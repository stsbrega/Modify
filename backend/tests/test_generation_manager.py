"""Tests for the in-memory GenerationManager.

Uses a fresh GenerationManager instance per test (not the singleton) to
avoid shared state between tests.
"""

import asyncio
import time

import pytest

from app.services.generation_manager import GenerationManager, GenerationState


@pytest.fixture
def manager():
    """Create a fresh manager for each test (bypass singleton)."""
    return GenerationManager()


# ---------------------------------------------------------------------------
# GenerationState dataclass defaults
# ---------------------------------------------------------------------------


class TestGenerationState:
    def test_defaults(self):
        state = GenerationState(generation_id="abc-123")
        assert state.generation_id == "abc-123"
        assert state.events == []
        assert state.subscribers == []
        assert state.status == "running"
        assert state.modlist_id is None
        assert state.paused_at_phase is None
        assert state.session_snapshot is None
        assert state.user_id is None


# ---------------------------------------------------------------------------
# create_generation
# ---------------------------------------------------------------------------


class TestCreateGeneration:
    def test_returns_string_id(self, manager):
        gid = manager.create_generation()
        assert isinstance(gid, str)
        assert len(gid) > 0

    def test_unique_ids(self, manager):
        ids = {manager.create_generation() for _ in range(20)}
        assert len(ids) == 20

    def test_state_is_running(self, manager):
        gid = manager.create_generation()
        state = manager.get_state(gid)
        assert state is not None
        assert state.status == "running"

    def test_stores_user_id(self, manager):
        gid = manager.create_generation(user_id="user-42")
        state = manager.get_state(gid)
        assert state.user_id == "user-42"


# ---------------------------------------------------------------------------
# emit
# ---------------------------------------------------------------------------


class TestEmit:
    def test_event_stored(self, manager):
        gid = manager.create_generation()
        manager.emit(gid, {"type": "thinking", "text": "..."})
        state = manager.get_state(gid)
        assert len(state.events) == 1
        assert state.events[0]["type"] == "thinking"

    def test_event_gets_timestamp(self, manager):
        gid = manager.create_generation()
        before = time.time()
        manager.emit(gid, {"type": "test"})
        after = time.time()
        ts = manager.get_state(gid).events[0]["timestamp"]
        assert before <= ts <= after

    def test_emit_to_unknown_generation_is_noop(self, manager):
        # Should not raise
        manager.emit("nonexistent-id", {"type": "test"})

    def test_multiple_events_ordered(self, manager):
        gid = manager.create_generation()
        for i in range(5):
            manager.emit(gid, {"type": "step", "index": i})
        events = manager.get_state(gid).events
        assert len(events) == 5
        assert [e["index"] for e in events] == [0, 1, 2, 3, 4]


# ---------------------------------------------------------------------------
# make_emitter
# ---------------------------------------------------------------------------


class TestMakeEmitter:
    def test_emitter_is_callable(self, manager):
        gid = manager.create_generation()
        emitter = manager.make_emitter(gid)
        assert callable(emitter)

    def test_emitter_stores_events(self, manager):
        gid = manager.create_generation()
        emitter = manager.make_emitter(gid)
        emitter({"type": "mod_added", "mod": "SkyUI"})
        state = manager.get_state(gid)
        assert len(state.events) == 1
        assert state.events[0]["mod"] == "SkyUI"


# ---------------------------------------------------------------------------
# subscribe / unsubscribe
# ---------------------------------------------------------------------------


class TestSubscribe:
    @pytest.mark.asyncio
    async def test_subscribe_returns_queue(self, manager):
        gid = manager.create_generation()
        queue = await manager.subscribe(gid)
        assert isinstance(queue, asyncio.Queue)

    @pytest.mark.asyncio
    async def test_subscribe_unknown_returns_none(self, manager):
        queue = await manager.subscribe("no-such-id")
        assert queue is None

    @pytest.mark.asyncio
    async def test_subscriber_receives_events(self, manager):
        gid = manager.create_generation()
        queue = await manager.subscribe(gid)
        manager.emit(gid, {"type": "searching", "query": "SKSE"})
        event = queue.get_nowait()
        assert event["type"] == "searching"
        assert event["query"] == "SKSE"

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, manager):
        gid = manager.create_generation()
        q1 = await manager.subscribe(gid)
        q2 = await manager.subscribe(gid)
        manager.emit(gid, {"type": "test"})
        assert q1.get_nowait()["type"] == "test"
        assert q2.get_nowait()["type"] == "test"

    @pytest.mark.asyncio
    async def test_unsubscribe(self, manager):
        gid = manager.create_generation()
        queue = await manager.subscribe(gid)
        manager.unsubscribe(gid, queue)
        state = manager.get_state(gid)
        assert queue not in state.subscribers

    @pytest.mark.asyncio
    async def test_unsubscribe_unknown_generation_is_noop(self, manager):
        queue = asyncio.Queue()
        # Should not raise
        manager.unsubscribe("no-such-id", queue)


# ---------------------------------------------------------------------------
# set_complete / set_error / set_paused / set_resumed
# ---------------------------------------------------------------------------


class TestStatusTransitions:
    def test_set_complete(self, manager):
        gid = manager.create_generation()
        manager.set_complete(gid, modlist_id="ml-42")
        state = manager.get_state(gid)
        assert state.status == "complete"
        assert state.modlist_id == "ml-42"

    def test_set_complete_emits_event(self, manager):
        gid = manager.create_generation()
        manager.set_complete(gid, modlist_id="ml-42")
        events = manager.get_state(gid).events
        assert any(e["type"] == "complete" and e["modlist_id"] == "ml-42" for e in events)

    def test_set_error(self, manager):
        gid = manager.create_generation()
        manager.set_error(gid, "Provider rate limited")
        state = manager.get_state(gid)
        assert state.status == "error"

    def test_set_error_emits_event(self, manager):
        gid = manager.create_generation()
        manager.set_error(gid, "boom")
        events = manager.get_state(gid).events
        assert any(e["type"] == "error" and e["message"] == "boom" for e in events)

    def test_set_paused(self, manager):
        gid = manager.create_generation()
        manager.set_paused(
            gid,
            phase_number=3,
            phase_name="Textures",
            reason="All providers failed",
            session_snapshot={"mods": ["SkyUI"]},
            request_snapshot={"game": "skyrim"},
            mods_so_far=5,
        )
        state = manager.get_state(gid)
        assert state.status == "paused"
        assert state.paused_at_phase == 3
        assert state.session_snapshot == {"mods": ["SkyUI"]}
        assert state.request_snapshot == {"game": "skyrim"}
        assert state.pause_reason == "All providers failed"

    def test_set_paused_emits_event(self, manager):
        gid = manager.create_generation()
        manager.set_paused(gid, 2, "Combat", "timeout", {}, {}, 3)
        events = manager.get_state(gid).events
        paused = [e for e in events if e["type"] == "paused"]
        assert len(paused) == 1
        assert paused[0]["can_resume"] is True
        assert paused[0]["mods_so_far"] == 3

    def test_set_resumed(self, manager):
        gid = manager.create_generation()
        manager.set_paused(gid, 3, "Textures", "error", {}, {}, 5)
        manager.set_resumed(gid, phase_name="Textures", phase_number=3)
        state = manager.get_state(gid)
        assert state.status == "running"
        assert state.paused_at_phase is None

    def test_set_resumed_emits_event(self, manager):
        gid = manager.create_generation()
        manager.set_paused(gid, 1, "Essentials", "error", {}, {}, 0)
        manager.set_resumed(gid, "Essentials", 1)
        events = manager.get_state(gid).events
        assert any(e["type"] == "resumed" for e in events)

    def test_set_complete_unknown_id_is_noop(self, manager):
        # Should not raise
        manager.set_complete("ghost", "ml-0")

    def test_set_error_unknown_id_is_noop(self, manager):
        manager.set_error("ghost", "msg")


# ---------------------------------------------------------------------------
# cleanup_old
# ---------------------------------------------------------------------------


class TestCleanup:
    def test_removes_old_complete(self, manager):
        gid = manager.create_generation()
        manager.set_complete(gid, "ml-1")
        # Backdate creation
        manager.get_state(gid).created_at = time.time() - 7200
        removed = manager.cleanup_old(max_age=3600)
        assert removed == 1
        assert manager.get_state(gid) is None

    def test_removes_old_errored(self, manager):
        gid = manager.create_generation()
        manager.set_error(gid, "fail")
        manager.get_state(gid).created_at = time.time() - 7200
        removed = manager.cleanup_old(max_age=3600)
        assert removed == 1

    def test_does_not_remove_running(self, manager):
        gid = manager.create_generation()
        manager.get_state(gid).created_at = time.time() - 7200
        removed = manager.cleanup_old(max_age=3600)
        assert removed == 0
        assert manager.get_state(gid) is not None

    def test_does_not_remove_paused(self, manager):
        gid = manager.create_generation()
        manager.set_paused(gid, 1, "Phase", "reason", {}, {}, 0)
        manager.get_state(gid).created_at = time.time() - 7200
        removed = manager.cleanup_old(max_age=3600)
        assert removed == 0

    def test_does_not_remove_recent_complete(self, manager):
        gid = manager.create_generation()
        manager.set_complete(gid, "ml-1")
        removed = manager.cleanup_old(max_age=3600)
        assert removed == 0

    def test_mixed_cleanup(self, manager):
        # Old + complete → removed
        g1 = manager.create_generation()
        manager.set_complete(g1, "ml-1")
        manager.get_state(g1).created_at = time.time() - 7200

        # Old + running → kept
        g2 = manager.create_generation()
        manager.get_state(g2).created_at = time.time() - 7200

        # Recent + complete → kept
        g3 = manager.create_generation()
        manager.set_complete(g3, "ml-3")

        removed = manager.cleanup_old(max_age=3600)
        assert removed == 1
        assert manager.get_state(g1) is None
        assert manager.get_state(g2) is not None
        assert manager.get_state(g3) is not None


# ---------------------------------------------------------------------------
# get_state
# ---------------------------------------------------------------------------


class TestGetState:
    def test_existing(self, manager):
        gid = manager.create_generation()
        assert manager.get_state(gid) is not None

    def test_nonexistent(self, manager):
        assert manager.get_state("no-such-id") is None
