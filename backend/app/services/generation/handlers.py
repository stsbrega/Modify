"""Tool handler builders for the generation pipeline.

Builds closures that the LLM tool-calling loop invokes when the model
calls search_nexus, add_to_modlist, etc.
"""

import asyncio
import json
import logging
from typing import Callable

from app.services.nexus_client import NexusAPIError

from .exceptions import NexusExhaustedError
from .session import GenerationSession, strip_html

logger = logging.getLogger(__name__)


def emit(callback: Callable[[dict], None] | None, event_type: str, data: dict, debug_data: dict | None = None) -> None:
    """Emit an event if a callback is provided.

    If debug_data is given it is attached as ``_debug`` so that
    GenerationManager.emit() can split it into the debug log while
    keeping the SSE stream lean.
    """
    if callback:
        event = {"type": event_type, **data}
        if debug_data:
            event["_debug"] = debug_data
        callback(event)


async def retry_nexus(
    coro_fn: Callable,
    max_retries: int = 3,
    event_callback: Callable[[dict], None] | None = None,
) -> object:
    """Retry a Nexus API call with exponential backoff.

    Handles rate limits (429) and server errors (5xx) by retrying.
    NexusAPIError (GraphQL errors) are NOT retried — they indicate
    query/auth problems, not transient failures.
    If all retries fail, raises NexusExhaustedError so the LLM can
    try a different search or skip the mod.
    """
    import httpx

    for attempt in range(max_retries):
        try:
            return await coro_fn()
        except NexusAPIError:
            raise
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 429:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt * 5  # 5s, 10s, 20s
                    emit(event_callback, "retrying", {
                        "reason": "nexus_rate_limit",
                        "wait_seconds": wait,
                        "attempt": attempt + 1,
                        "max_attempts": max_retries,
                    })
                    await asyncio.sleep(wait)
                    continue
            elif status >= 500:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt * 3  # 3s, 6s, 12s
                    emit(event_callback, "retrying", {
                        "reason": "nexus_server_error",
                        "wait_seconds": wait,
                        "attempt": attempt + 1,
                        "max_attempts": max_retries,
                    })
                    await asyncio.sleep(wait)
                    continue
            raise
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt * 3
                emit(event_callback, "retrying", {
                    "reason": "nexus_timeout" if isinstance(e, httpx.TimeoutException) else "nexus_connection",
                    "wait_seconds": wait,
                    "attempt": attempt + 1,
                    "max_attempts": max_retries,
                })
                await asyncio.sleep(wait)
                continue
            raise

    raise NexusExhaustedError("All Nexus retries failed")


def build_phase1_handlers(
    session: GenerationSession,
    event_callback: Callable[[dict], None] | None = None,
) -> dict:
    """Build tool handler functions for discovery phases (search + add mods)."""

    async def search_nexus(query: str, sort_by: str = "endorsements") -> str:
        emit(event_callback, "searching", {"query": query})
        try:
            results = await retry_nexus(
                lambda: session.nexus.search_mods(session.game_domain, query, sort_by=sort_by),
                event_callback=event_callback,
            )
        except Exception as e:
            logger.warning(f"Nexus search failed after retries: {e}")
            return json.dumps({"error": "Search temporarily unavailable. Try a different query."})

        mods = []
        for m in results[:15]:
            author = m.get("author", "Unknown")
            mod_id = m["modId"]
            session.author_cache[mod_id] = author
            mods.append({
                "mod_id": mod_id,
                "name": m["name"],
                "author": author,
                "summary": (m.get("summary") or "")[:200],
                "endorsements": m.get("endorsements", 0),
                "category": m.get("modCategory", {}).get("name", ""),
                "updated": m.get("updatedAt", ""),
            })
        all_names = [m["name"] for m in mods]
        logger.debug("Search '%s' returned %d results: %s", query, len(mods), all_names)
        emit(event_callback, "search_results", {
            "count": len(mods),
            "sample_names": all_names[:5],
        }, debug_data={"all_names": all_names})
        return json.dumps({"results": mods, "count": len(mods)})

    async def get_mod_details(mod_id: int) -> str:
        emit(event_callback, "reading_mod", {"mod_id": mod_id})
        try:
            details = await retry_nexus(
                lambda: session.nexus.get_mod_details(session.game_domain, mod_id),
                event_callback=event_callback,
            )
        except Exception as e:
            logger.warning(f"Nexus get_mod_details failed after retries: {e}")
            return json.dumps({"error": f"Could not fetch mod {mod_id}. Try another mod."})

        if not details:
            return json.dumps({"error": f"Mod {mod_id} not found"})
        desc_html = details.get("description") or ""
        desc_text = strip_html(desc_html)
        session.description_cache[mod_id] = desc_text
        author = details.get("author", "Unknown")
        session.author_cache[mod_id] = author
        return json.dumps({
            "mod_id": details["modId"],
            "name": details["name"],
            "author": author,
            "summary": details.get("summary", ""),
            "description": desc_text,
            "endorsements": details.get("endorsements", 0),
            "category": details.get("modCategory", {}).get("name", ""),
        })

    async def add_to_modlist(
        mod_id: int, name: str, reason: str, load_order: int,
        author: str = "", summary: str = "", estimated_size_mb: int = 0,
    ) -> str:
        resolved_author = author or session.author_cache.get(mod_id, "")
        entry = {
            "nexus_mod_id": mod_id,
            "name": name,
            "author": resolved_author,
            "summary": summary,
            "reason": reason,
            "load_order": load_order,
            "estimated_size_mb": estimated_size_mb,
            "is_patch": False,
        }
        session.modlist.append(entry)
        logger.debug("Mod added: %s (id=%d, order=%d, size=%dMB) — %s",
                      name, mod_id, load_order, estimated_size_mb, reason)
        emit(event_callback, "mod_added", {
            "mod_id": mod_id,
            "name": name,
            "reason": reason,
            "load_order": load_order,
        })
        return json.dumps({
            "status": "added",
            "name": name,
            "current_count": len(session.modlist),
        })

    async def finalize() -> str:
        session.finalized = True
        return json.dumps({
            "status": "finalized",
            "total_mods": len(session.modlist),
        })

    return {
        "search_nexus": search_nexus,
        "get_mod_details": get_mod_details,
        "add_to_modlist": add_to_modlist,
        "finalize": finalize,
    }


def build_phase2_handlers(
    session: GenerationSession,
    event_callback: Callable[[dict], None] | None = None,
) -> dict:
    """Build tool handler functions for the compatibility patches phase."""

    async def get_mod_description(mod_id: int) -> str:
        emit(event_callback, "reading_mod", {"mod_id": mod_id})
        if mod_id in session.description_cache:
            return json.dumps({"mod_id": mod_id, "description": session.description_cache[mod_id]})
        try:
            details = await retry_nexus(
                lambda: session.nexus.get_mod_details(session.game_domain, mod_id),
                event_callback=event_callback,
            )
        except Exception as e:
            logger.warning(f"Nexus get_mod_details failed after retries: {e}")
            return json.dumps({"error": f"Could not fetch mod {mod_id}"})

        if not details:
            return json.dumps({"error": f"Mod {mod_id} not found"})
        desc_text = strip_html(details.get("description") or "")
        session.description_cache[mod_id] = desc_text
        return json.dumps({"mod_id": mod_id, "description": desc_text})

    async def search_patches(query: str) -> str:
        emit(event_callback, "searching", {"query": query})
        try:
            results = await retry_nexus(
                lambda: session.nexus.search_mods(session.game_domain, query, sort_by="endorsements"),
                event_callback=event_callback,
            )
        except Exception as e:
            logger.warning(f"Nexus search_patches failed after retries: {e}")
            return json.dumps({"error": "Patch search temporarily unavailable."})

        patches = []
        for m in results[:10]:
            author = m.get("author", "Unknown")
            mod_id = m["modId"]
            session.author_cache[mod_id] = author
            patches.append({
                "mod_id": mod_id,
                "name": m["name"],
                "author": author,
                "summary": (m.get("summary") or "")[:200],
                "endorsements": m.get("endorsements", 0),
            })
        all_patch_names = [p["name"] for p in patches]
        logger.debug("Patch search '%s' returned %d results: %s", query, len(patches), all_patch_names)
        emit(event_callback, "search_results", {
            "count": len(patches),
            "sample_names": all_patch_names[:5],
        }, debug_data={"all_names": all_patch_names})
        return json.dumps({"results": patches, "count": len(patches)})

    async def add_patch(
        mod_id: int, name: str, patches_mods: list[str], reason: str,
        load_order: int, author: str = "",
    ) -> str:
        resolved_author = author or session.author_cache.get(mod_id, "")
        entry = {
            "nexus_mod_id": mod_id,
            "name": name,
            "author": resolved_author,
            "reason": reason,
            "load_order": load_order,
            "is_patch": True,
            "patches_mods": patches_mods,
        }
        session.patches.append(entry)
        logger.debug("Patch added: %s (id=%d, order=%d) patches %s — %s",
                      name, mod_id, load_order, patches_mods, reason)
        emit(event_callback, "patch_added", {
            "mod_id": mod_id,
            "name": name,
            "patches_mods": patches_mods,
        })
        return json.dumps({"status": "patch_added", "name": name})

    async def flag_user_knowledge(
        mod_a: str, mod_b: str, issue: str, severity: str = "warning",
    ) -> str:
        flag = {
            "mod_a": mod_a,
            "mod_b": mod_b,
            "issue": issue,
            "severity": severity,
        }
        session.knowledge_flags.append(flag)
        emit(event_callback, "knowledge_flag", {
            "mod_a": mod_a,
            "mod_b": mod_b,
            "issue": issue,
            "severity": severity,
        })
        return json.dumps({"status": "flagged", "mod_a": mod_a, "mod_b": mod_b})

    async def finalize_review() -> str:
        session.finalized = True
        return json.dumps({
            "status": "review_complete",
            "patches_added": len(session.patches),
            "flags_raised": len(session.knowledge_flags),
        })

    return {
        "get_mod_description": get_mod_description,
        "search_patches": search_patches,
        "add_patch": add_patch,
        "flag_user_knowledge": flag_user_knowledge,
        "finalize_review": finalize_review,
    }
