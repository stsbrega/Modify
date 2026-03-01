"""Agentic modlist generation pipeline.

Public API re-exports for backward compatibility.
"""

from .exceptions import (
    NexusExhaustedError,
    NexusRateLimitError,
    NexusServerError,
    PauseGeneration,
)
from .pipeline import build_rag_context, generate_modlist
from .session import GenerationResult, GenerationSession
from .version import TIER_MIN_VRAM, is_version_compatible

__all__ = [
    "generate_modlist",
    "build_rag_context",
    "GenerationResult",
    "GenerationSession",
    "PauseGeneration",
    "NexusRateLimitError",
    "NexusServerError",
    "NexusExhaustedError",
    "is_version_compatible",
    "TIER_MIN_VRAM",
]
