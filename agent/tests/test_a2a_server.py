import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import a2a_server

# ─── Mock subprocess class ───────────────────────────────────────────────────

class MockProcess:
    def __init__(self, stdout=b"mock success", stderr=b"", returncode=0, delay=0.0):
        self.stdout_bytes = stdout
        self.stderr_bytes = stderr
        self._returncode = returncode
        self.delay = delay
        self.terminate_called = False
        self.kill_called = False
        self.wait_called = False

    @property
    def returncode(self):
        return self._returncode

    async def communicate(self):
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        return self.stdout_bytes, self.stderr_bytes

    def terminate(self):
        self.terminate_called = True
        self._returncode = -15

    def kill(self):
        self.kill_called = True
        self._returncode = -9

    async def wait(self):
        self.wait_called = True
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        return self._returncode

# ─── Mock TaskUpdater ──────────────────────────────────────────────────────────

class MockTaskUpdater:
    def __init__(self, event_queue, task_id, context_id):
        self.event_queue = event_queue
        self.task_id = task_id
        self.context_id = context_id
        self.status_updates = []
        self.artifacts = []
        self.cancelled = False

    async def update_status(self, state, message=None):
        self.status_updates.append((state, message))

    async def add_artifact(self, parts):
        self.artifacts.append(parts)

    async def cancel(self, message=None):
        self.cancelled = True
        self.status_updates.append(("CANCELED", message))

# ─── Helper to build Mock Context ─────────────────────────────────────────────

def make_mock_context(task_id="task_123", context_id="ctx_456", text="hello"):
    context = MagicMock()
    context.task_id = task_id
    context.context_id = context_id
    context.message = MagicMock()
    
    task = MagicMock()
    task.id = task_id
    task.context_id = context_id
    context.current_task = task
    
    return context

# ─── Tests ───────────────────────────────────────────────────────────────────

@pytest.mark.anyio
@patch("a2a_server.TaskUpdater", MockTaskUpdater)
@patch("a2a_server.new_text_message", lambda x: f"msg:{x}")
@patch("a2a_server.new_text_part", lambda text, media_type: f"part:{text}")
@patch("a2a_server.get_message_text", lambda x: "mock user prompt")
async def test_vt_executor_success():
    executor = a2a_server.VTAgentExecutor()
    context = make_mock_context()
    event_queue = MagicMock()

    mock_proc = MockProcess(stdout=b"ChinaAEngine Backtest Results", returncode=0)
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        await executor.execute(context, event_queue)
        
        # Verify subprocess.exec was called correctly
        mock_exec.assert_called_once_with(
            a2a_server.VT_BIN, "-p", "mock user prompt", "--no-rich",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Verify executor status updates
        # VTAgentExecutor has a TaskUpdater instance created
        # Let's verify process dict is clean
        assert len(executor._running_processes) == 0

@pytest.mark.anyio
@patch("a2a_server.TaskUpdater", MockTaskUpdater)
@patch("a2a_server.new_text_message", lambda x: f"msg:{x}")
@patch("a2a_server.new_text_part", lambda text, media_type: f"part:{text}")
@patch("a2a_server.get_message_text", lambda x: "mock user prompt")
async def test_vt_executor_timeout():
    executor = a2a_server.VTAgentExecutor()
    context = make_mock_context()
    event_queue = MagicMock()

    # Mock wait_for to raise TimeoutError
    async def mock_wait_for(fut, timeout=None):
        if timeout == 180.0:
            # Wrap in task, cancel and await to avoid unawaited coroutine warning
            t = asyncio.create_task(fut)
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
            raise asyncio.TimeoutError()
        return await fut

    mock_proc = MockProcess(stdout=b"", returncode=None, delay=1.0)

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
         patch("asyncio.wait_for", mock_wait_for):
        
        await executor.execute(context, event_queue)
        
        # Verify the process was terminated/killed and reaped
        assert mock_proc.terminate_called is True
        assert len(executor._running_processes) == 0

@pytest.mark.anyio
@patch("a2a_server.TaskUpdater", MockTaskUpdater)
@patch("a2a_server.new_text_message", lambda x: f"msg:{x}")
@patch("a2a_server.new_text_part", lambda text, media_type: f"part:{text}")
@patch("a2a_server.get_message_text", lambda x: "mock user prompt")
async def test_vt_executor_concurrency():
    executor = a2a_server.VTAgentExecutor()
    context_1 = make_mock_context(task_id="task_1")
    context_2 = make_mock_context(task_id="task_2")
    event_queue = MagicMock()

    proc_1 = MockProcess(stdout=b"Output 1", returncode=0, delay=0.1)
    proc_2 = MockProcess(stdout=b"Output 2", returncode=0, delay=0.1)

    async def mock_exec(*args, **kwargs):
        # Return different mock process depending on prompt or call count
        if "task_1" in executor._running_processes or len(executor._running_processes) == 0:
            return proc_1
        return proc_2

    with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
        # Start both concurrently
        task_1 = asyncio.create_task(executor.execute(context_1, event_queue))
        task_2 = asyncio.create_task(executor.execute(context_2, event_queue))
        
        # Let them run a bit
        await asyncio.sleep(0.02)
        
        # Verify both processes are tracked concurrently
        assert "task_1" in executor._running_processes
        assert "task_2" in executor._running_processes
        assert len(executor._running_processes) == 2
        
        await asyncio.gather(task_1, task_2)
        
        # Verify clean up
        assert len(executor._running_processes) == 0

@pytest.mark.anyio
@patch("a2a_server.TaskUpdater", MockTaskUpdater)
@patch("a2a_server.new_text_message", lambda x: f"msg:{x}")
@patch("a2a_server.new_text_part", lambda text, media_type: f"part:{text}")
@patch("a2a_server.get_message_text", lambda x: "mock user prompt")
async def test_vt_executor_cancellation_via_finally():
    executor = a2a_server.VTAgentExecutor()
    context = make_mock_context(task_id="cancel_task")
    event_queue = MagicMock()

    mock_proc = MockProcess(stdout=b"", returncode=None, delay=5.0)

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        # Run execution inside a Task
        run_task = asyncio.create_task(executor.execute(context, event_queue))
        
        # Wait until process is registered
        await asyncio.sleep(0.02)
        assert "cancel_task" in executor._running_processes
        
        # Cancel the task
        run_task.cancel()
        
        try:
            await run_task
        except asyncio.CancelledError:
            pass
            
        # Verify subprocess was reaped and terminated in finally
        assert mock_proc.terminate_called is True
        assert len(executor._running_processes) == 0

@pytest.mark.anyio
@patch("a2a_server.TaskUpdater", MockTaskUpdater)
@patch("a2a_server.new_text_message", lambda x: f"msg:{x}")
@patch("a2a_server.new_text_part", lambda text, media_type: f"part:{text}")
@patch("a2a_server.get_message_text", lambda x: "mock user prompt")
async def test_vt_executor_cancel_method():
    executor = a2a_server.VTAgentExecutor()
    context = make_mock_context(task_id="task_to_cancel")
    event_queue = MagicMock()

    mock_proc = MockProcess(stdout=b"", returncode=None, delay=5.0)

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        # Run execution inside a Task
        run_task = asyncio.create_task(executor.execute(context, event_queue))
        
        # Wait until process is registered
        await asyncio.sleep(0.02)
        assert "task_to_cancel" in executor._running_processes
        
        # Call executor.cancel() explicitly
        cancel_ctx = make_mock_context(task_id="task_to_cancel")
        await executor.cancel(cancel_ctx, event_queue)
        
        # Verify cancel sent SIGTERM to the process
        assert mock_proc.terminate_called is True
        
        # Wait for execution task to wind down (it will exit because communication finished or process was terminated)
        # Note: In real life, cancel() terminates process, causing process.communicate() in execute() to return
        await run_task
        
        # Verify dictionary cleaned up
        assert len(executor._running_processes) == 0
