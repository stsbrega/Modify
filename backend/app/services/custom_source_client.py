"""Generic client for custom mod source APIs.

This client accepts a user-provided API endpoint and key,
and normalizes responses from various mod hosting APIs
into a common format used by ModdersOmni.
"""
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class CustomSourceClient:
    """Generic client for custom mod source APIs."""

    def __init__(self, api_url: str | None = None, api_key: str | None = None):
        settings = get_settings()
        self.api_url = (api_url or settings.custom_source_api_url).rstrip("/")
        self.api_key = api_key or settings.custom_source_api_key

    def is_configured(self) -> bool:
        return bool(self.api_url)

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def search_mods(self, search_term: str) -> list[dict]:
        """Search for mods on the custom source."""
        if not self.is_configured():
            return []

        try:
            async with httpx.AsyncClient() as client:
                # Try common API patterns
                for endpoint in [
                    f"{self.api_url}/mods/search",
                    f"{self.api_url}/api/mods/search",
                    f"{self.api_url}/search",
                ]:
                    try:
                        response = await client.get(
                            endpoint,
                            params={"q": search_term},
                            headers=self._headers(),
                            timeout=15.0,
                        )
                        if response.status_code == 200:
                            data = response.json()
                            return self._normalize_search_results(data)
                    except httpx.HTTPError:
                        continue

        except Exception as e:
            logger.warning(f"Custom source search failed: {e}")

        return []

    async def get_mod_details(self, mod_id: str | int) -> dict | None:
        """Get details for a specific mod."""
        if not self.is_configured():
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/mods/{mod_id}",
                    headers=self._headers(),
                    timeout=15.0,
                )
                if response.status_code == 200:
                    return self._normalize_mod(response.json())
        except Exception as e:
            logger.warning(f"Custom source mod details failed: {e}")

        return None

    async def get_download_url(self, mod_id: str | int, file_id: str | int | None = None) -> str | None:
        """Get download URL for a mod file."""
        if not self.is_configured():
            return None

        try:
            async with httpx.AsyncClient() as client:
                endpoint = f"{self.api_url}/mods/{mod_id}/download"
                if file_id:
                    endpoint = f"{self.api_url}/mods/{mod_id}/files/{file_id}/download"

                response = await client.get(
                    endpoint,
                    headers=self._headers(),
                    timeout=15.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("url") or data.get("download_url") or data.get("URI")
        except Exception as e:
            logger.warning(f"Custom source download URL failed: {e}")

        return None

    def _normalize_search_results(self, data: dict | list) -> list[dict]:
        """Normalize various API response formats into a standard list."""
        results = []

        # Handle list or dict-with-results
        items = data if isinstance(data, list) else data.get("results", data.get("data", data.get("mods", [])))

        for item in items:
            results.append(self._normalize_mod(item))

        return results

    def _normalize_mod(self, data: dict) -> dict:
        """Normalize a single mod response into standard format."""
        return {
            "id": data.get("id") or data.get("mod_id"),
            "name": data.get("name") or data.get("title", "Unknown"),
            "summary": data.get("summary") or data.get("description", ""),
            "author": data.get("author") or data.get("uploaded_by", "Unknown"),
            "version": data.get("version", ""),
            "download_count": data.get("download_count") or data.get("downloads", 0),
            "source": "custom",
        }
