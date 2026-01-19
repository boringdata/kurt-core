"""
Unit tests for Stream Bridge.

Tests the StreamSession class and build_stream_args function.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kurt.web.api.stream_bridge import (
    StreamSession,
    build_stream_args,
)

# ============================================================================
# build_stream_args Tests
# ============================================================================


class TestBuildStreamArgs:
    """Test build_stream_args function."""

    def test_no_print_flag(self):
        """Should not add --print flag (VSCode extension doesn't use it)."""
        args = build_stream_args([], None, False)
        assert "--print" not in args

    def test_adds_output_format_stream_json(self):
        """Should add --output-format stream-json."""
        args = build_stream_args([], None, False)
        assert "--output-format" in args
        idx = args.index("--output-format")
        assert args[idx + 1] == "stream-json"

    def test_adds_input_format_stream_json(self):
        """Should add --input-format stream-json."""
        args = build_stream_args([], None, False)
        assert "--input-format" in args
        idx = args.index("--input-format")
        assert args[idx + 1] == "stream-json"

    def test_adds_verbose_flag(self):
        """Should add --verbose flag."""
        args = build_stream_args([], None, False)
        assert "--verbose" in args

    def test_adds_session_id_for_new_session(self):
        """Should add --session-id for new sessions."""
        args = build_stream_args([], "test-session-123", resume=False)
        assert "--session-id" in args
        idx = args.index("--session-id")
        assert args[idx + 1] == "test-session-123"

    def test_adds_resume_flag_for_resumed_session(self):
        """Should add --resume for resumed sessions."""
        args = build_stream_args([], "test-session-123", resume=True)
        assert "--resume" in args
        idx = args.index("--resume")
        assert args[idx + 1] == "test-session-123"

    def test_no_session_args_without_session_id(self):
        """Should not add session args when no session_id provided."""
        args = build_stream_args([], None, False)
        assert "--session-id" not in args
        assert "--resume" not in args

    def test_preserves_base_args(self):
        """Should preserve existing base args."""
        base = ["--model", "sonnet"]
        args = build_stream_args(base, None, False)
        assert "--model" in args
        assert "sonnet" in args

    def test_adds_setting_sources(self):
        """Should add --setting-sources to load user/project/local settings."""
        args = build_stream_args([], None, False)
        assert "--setting-sources" in args
        idx = args.index("--setting-sources")
        assert args[idx + 1] == "user,project,local"

    def test_no_duplicate_setting_sources(self):
        """Should not duplicate --setting-sources if already present."""
        args = build_stream_args(["--setting-sources", "user"], None, False)
        assert args.count("--setting-sources") == 1


# ============================================================================
# StreamSession Tests
# ============================================================================


class TestStreamSession:
    """Test StreamSession class."""

    def test_init(self):
        """Should initialize with correct attributes."""
        session = StreamSession(
            cmd="claude",
            args=["--print"],
            cwd="/tmp",
            extra_env={"FOO": "bar"},
        )
        assert session.cmd == "claude"
        assert session.args == ["--print"]
        assert session.cwd == "/tmp"
        assert session.extra_env == {"FOO": "bar"}
        assert session.proc is None
        assert not session._started
        assert not session._terminated

    def test_is_alive_false_when_no_proc(self):
        """Should return False when process not started."""
        session = StreamSession("claude", [], "/tmp")
        assert not session.is_alive()

    @pytest.mark.asyncio
    async def test_is_alive_false_after_terminate(self):
        """Should return False after termination."""
        session = StreamSession("claude", [], "/tmp")
        session._started = True
        session._terminated = True
        assert not session.is_alive()

    @pytest.mark.asyncio
    async def test_write_message_formats_json_correctly(self):
        """Should format message as correct JSON for Claude stream-json input."""
        session = StreamSession("claude", [], "/tmp")

        # Mock the process and stdin
        mock_stdin = AsyncMock()
        mock_stdin.write = MagicMock()
        mock_stdin.drain = AsyncMock()

        mock_proc = MagicMock()
        mock_proc.stdin = mock_stdin

        session.proc = mock_proc

        await session.write_message("Hello world")

        # Verify the JSON format
        mock_stdin.write.assert_called_once()
        written_bytes = mock_stdin.write.call_args[0][0]
        written_str = written_bytes.decode("utf-8")
        written_json = json.loads(written_str.strip())

        assert written_json == {
            "type": "user",
            "session_id": "",  # Required by stream-json protocol
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "Hello world"}],
            },
        }

    @pytest.mark.asyncio
    async def test_write_message_noop_without_proc(self):
        """Should do nothing if process not started."""
        session = StreamSession("claude", [], "/tmp")
        # Should not raise
        await session.write_message("test")

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_clients(self):
        """Should broadcast message to all connected clients."""
        session = StreamSession("claude", [], "/tmp")

        client1 = AsyncMock()
        client2 = AsyncMock()
        session.clients = {client1, client2}

        payload = {"type": "test", "data": "hello"}
        await session.broadcast(payload)

        client1.send_json.assert_called_once_with(payload)
        client2.send_json.assert_called_once_with(payload)

    @pytest.mark.asyncio
    async def test_broadcast_does_not_store_history(self):
        """Should not store history (CLI handles it via --resume)."""
        session = StreamSession("claude", [], "/tmp")

        payload = {"type": "test", "data": "hello"}
        await session.broadcast(payload)

        # History storage removed - CLI handles conversation history
        assert len(session.history) == 0

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_clients(self):
        """Should remove clients that fail to receive."""
        session = StreamSession("claude", [], "/tmp")

        good_client = AsyncMock()
        bad_client = AsyncMock()
        bad_client.send_json.side_effect = Exception("Connection lost")

        session.clients = {good_client, bad_client}

        await session.broadcast({"type": "test"})

        assert good_client in session.clients
        assert bad_client not in session.clients

    @pytest.mark.asyncio
    async def test_send_history_to_new_client(self):
        """Should send accumulated history to new client."""
        session = StreamSession("claude", [], "/tmp")
        session.history.append({"type": "msg1"})
        session.history.append({"type": "msg2"})

        client = AsyncMock()
        await session.send_history(client)

        assert client.send_json.call_count == 2
        client.send_json.assert_any_call({"type": "msg1"})
        client.send_json.assert_any_call({"type": "msg2"})

    @pytest.mark.asyncio
    async def test_add_client_cancels_idle_task(self):
        """Should cancel idle cleanup when client connects."""
        session = StreamSession("claude", [], "/tmp")

        # Create a mock idle task
        mock_task = MagicMock()
        session.idle_task = mock_task

        client = AsyncMock()
        await session.add_client(client)

        mock_task.cancel.assert_called_once()
        assert session.idle_task is None
        assert client in session.clients

    @pytest.mark.asyncio
    async def test_remove_client_schedules_cleanup(self):
        """Should schedule cleanup when last client disconnects."""
        session = StreamSession("claude", [], "/tmp")
        session.session_id = "test-session"

        client = AsyncMock()
        session.clients = {client}

        with patch.object(session, "schedule_idle_cleanup", new_callable=AsyncMock) as mock_cleanup:
            await session.remove_client(client)
            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_terminate_kills_process(self):
        """Should terminate the subprocess."""
        session = StreamSession("claude", [], "/tmp")
        session.session_id = "test-session"
        session._started = True

        # Mock process
        mock_proc = MagicMock()
        mock_proc.returncode = None
        mock_proc.terminate = MagicMock()
        mock_proc.wait = AsyncMock()
        session.proc = mock_proc

        await session.terminate()

        mock_proc.terminate.assert_called_once()
        assert session._terminated
        assert session.proc is None


# ============================================================================
# Integration Tests (require real claude CLI)
# ============================================================================


class TestSessionResuming:
    """Test session resuming functionality."""

    def test_resume_uses_resume_flag_not_session_id(self):
        """When resuming, should use --resume not --session-id."""
        args = build_stream_args([], "test-session-123", resume=True)
        assert "--resume" in args
        assert "--session-id" not in args
        idx = args.index("--resume")
        assert args[idx + 1] == "test-session-123"

    def test_new_session_uses_session_id_not_resume(self):
        """When not resuming, should use --session-id not --resume."""
        args = build_stream_args([], "test-session-123", resume=False)
        assert "--session-id" in args
        assert "--resume" not in args
        idx = args.index("--session-id")
        assert args[idx + 1] == "test-session-123"


@pytest.mark.integration
class TestStreamSessionIntegration:
    """Integration tests that require real Claude CLI.

    Run with: pytest -m integration
    """

    @pytest.mark.asyncio
    async def test_spawn_and_communicate(self):
        """Test spawning Claude and sending a message."""
        import shutil

        if not shutil.which("claude"):
            pytest.skip("Claude CLI not installed")

        args = build_stream_args([], None, False)
        session = StreamSession(
            cmd="claude",
            args=args,
            cwd="/tmp",
        )

        try:
            await session.spawn()
            assert session.is_alive()

            # Send a test message
            await session.write_message("say hello in one word")

            # Give it time to process
            await asyncio.sleep(5)

        finally:
            await session.terminate()
