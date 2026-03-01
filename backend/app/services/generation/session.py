"""Session state and result types for the generation pipeline."""

import re
from dataclasses import dataclass, field

from app.services.nexus_client import NexusModsClient


@dataclass
class GenerationSession:
    """Mutable state shared across tool handler calls within one generation."""
    game_domain: str
    nexus: NexusModsClient
    modlist: list[dict] = field(default_factory=list)
    patches: list[dict] = field(default_factory=list)
    knowledge_flags: list[dict] = field(default_factory=list)
    description_cache: dict[int, str] = field(default_factory=dict)
    finalized: bool = False
    completed_phases: list[int] = field(default_factory=list)

    def to_snapshot(self) -> dict:
        """Serialize session state for pause/resume."""
        return {
            "game_domain": self.game_domain,
            "modlist": list(self.modlist),
            "patches": list(self.patches),
            "knowledge_flags": list(self.knowledge_flags),
            "description_cache": {str(k): v for k, v in self.description_cache.items()},
            "completed_phases": list(self.completed_phases),
        }

    @classmethod
    def from_snapshot(cls, snapshot: dict, nexus: NexusModsClient) -> "GenerationSession":
        """Reconstruct a session from a saved snapshot."""
        return cls(
            game_domain=snapshot["game_domain"],
            nexus=nexus,
            modlist=snapshot.get("modlist", []),
            patches=snapshot.get("patches", []),
            knowledge_flags=snapshot.get("knowledge_flags", []),
            description_cache={int(k): v for k, v in snapshot.get("description_cache", {}).items()},
            completed_phases=snapshot.get("completed_phases", []),
        )


@dataclass
class GenerationResult:
    """Complete output of the agentic modlist generation."""
    entries: list[dict]
    knowledge_flags: list[dict]
    llm_provider: str


def strip_html(html: str) -> str:
    """Strip HTML tags, keeping text content."""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 3000:
        text = text[:3000] + "... [truncated]"
    return text
