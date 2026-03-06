"""In-memory manager for tracking active and recently completed generations.

Stores events for SSE replay and manages subscriber queues for live streaming.
Generations are cleaned up after 1 hour to bound memory usage.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class GenerationState:
    """State for a single modlist generation."""

    generation_id: str
    events: list[dict] = field(default_factory=list)
    debug_log: list[dict] = field(default_factory=list)
    subscribers: list[asyncio.Queue] = field(default_factory=list)
    status: str = "running"  # running | complete | error | paused
    modlist_id: str | None = None
    created_at: float = field(default_factory=time.time)

    # Pause/resume fields
    paused_at_phase: int | None = None
    session_snapshot: dict | None = None
    request_snapshot: dict | None = None
    pause_reason: str | None = None
    user_id: str | None = None


class GenerationManager:
    """Singleton manager for in-memory generation tracking.

    Responsibilities:
    - Store events for each generation (for SSE replay on reconnect)
    - Push live events to subscriber queues (for active SSE connections)
    - Track generation status (running/complete/error/paused)
    - Clean up old generations to bound memory
    """

    _instance: "GenerationManager | None" = None

    def __init__(self):
        self._generations: dict[str, GenerationState] = {}
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> "GenerationManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_generation(self, user_id: str | None = None) -> str:
        """Create a new generation and return its ID."""
        generation_id = str(uuid.uuid4())
        state = GenerationState(
            generation_id=generation_id,
            user_id=user_id,
        )
        self._generations[generation_id] = state
        logger.info(f"Created generation {generation_id}")
        return generation_id

    def emit(self, generation_id: str, event: dict) -> None:
        """Store an event and push it to all active subscribers.

        If the event carries a ``_debug`` key (injected by the pipeline's
        ``emit()`` helper), it is stripped from the SSE event and merged
        into a separate ``debug_log`` entry with full untruncated data.
        """
        state = self._generations.get(generation_id)
        if not state:
            logger.warning(f"emit() called for unknown generation {generation_id}")
            return

        event["timestamp"] = time.time()

        # Separate debug data from SSE event
        debug_data = event.pop("_debug", None)

        state.events.append(event)

        # Push to all subscriber queues (non-blocking)
        for queue in state.subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(f"Subscriber queue full for generation {generation_id}")

        # Store full-detail copy in debug log
        debug_entry = dict(event)
        if debug_data:
            debug_entry.update(debug_data)
        state.debug_log.append(debug_entry)

    def make_emitter(self, generation_id: str) -> Callable[[dict], None]:
        """Return a callback function bound to a specific generation ID.

        This is passed as `event_callback` to the generation pipeline.
        """
        def _emit(event: dict) -> None:
            self.emit(generation_id, event)
        return _emit

    async def subscribe(self, generation_id: str) -> asyncio.Queue | None:
        """Subscribe to live events for a generation.

        Returns a Queue that receives new events. Past events should be
        replayed from state.events before consuming the queue.
        Returns None if generation doesn't exist.
        """
        state = self._generations.get(generation_id)
        if not state:
            return None

        queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        state.subscribers.append(queue)
        logger.info(
            f"New subscriber for generation {generation_id} "
            f"(total: {len(state.subscribers)})"
        )
        return queue

    def unsubscribe(self, generation_id: str, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        state = self._generations.get(generation_id)
        if state and queue in state.subscribers:
            state.subscribers.remove(queue)
            logger.info(
                f"Unsubscribed from generation {generation_id} "
                f"(remaining: {len(state.subscribers)})"
            )

    def get_state(self, generation_id: str) -> GenerationState | None:
        return self._generations.get(generation_id)

    def set_complete(self, generation_id: str, modlist_id: str) -> None:
        """Mark generation as complete with the saved modlist ID."""
        state = self._generations.get(generation_id)
        if state:
            state.status = "complete"
            state.modlist_id = modlist_id
            self.emit(generation_id, {
                "type": "complete",
                "modlist_id": modlist_id,
            })

    def set_error(self, generation_id: str, message: str) -> None:
        """Mark generation as failed."""
        state = self._generations.get(generation_id)
        if state:
            state.status = "error"
            self.emit(generation_id, {
                "type": "error",
                "message": message,
            })

    def set_paused(
        self,
        generation_id: str,
        phase_number: int,
        phase_name: str,
        reason: str,
        session_snapshot: dict,
        request_snapshot: dict,
        mods_so_far: int,
    ) -> None:
        """Mark generation as paused with recovery state."""
        state = self._generations.get(generation_id)
        if state:
            state.status = "paused"
            state.paused_at_phase = phase_number
            state.session_snapshot = session_snapshot
            state.request_snapshot = request_snapshot
            state.pause_reason = reason
            self.emit(generation_id, {
                "type": "paused",
                "reason": reason,
                "phase_name": phase_name,
                "phase_number": phase_number,
                "mods_so_far": mods_so_far,
                "can_resume": True,
            })

    def set_resumed(self, generation_id: str, phase_name: str, phase_number: int) -> None:
        """Mark generation as running again after resume."""
        state = self._generations.get(generation_id)
        if state:
            state.status = "running"
            state.paused_at_phase = None
            self.emit(generation_id, {
                "type": "resumed",
                "phase_name": phase_name,
                "phase_number": phase_number,
            })

    def cleanup_old(self, max_age: float = 3600) -> int:
        """Remove completed/errored generations older than max_age seconds.

        Returns the number of cleaned-up generations.
        """
        now = time.time()
        to_remove = []
        for gid, state in self._generations.items():
            if state.status in ("complete", "error") and now - state.created_at > max_age:
                to_remove.append(gid)
        for gid in to_remove:
            del self._generations[gid]
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old generations")
        return len(to_remove)
