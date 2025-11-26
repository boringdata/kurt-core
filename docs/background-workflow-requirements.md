# Background Workflow Execution Requirements

## Overview
This document outlines the requirements and implementation details for Kurt's background workflow execution system using DBOS.

## Core Requirements

### 1. Process Independence
- **Requirement**: Background workflows must run in a completely independent process
- **Rationale**: Allows CLI to exit immediately after starting a workflow
- **Implementation**: Use `subprocess.Popen` with `start_new_session=True` to create detached process

### 2. Workflow Durability
- **Requirement**: Workflows must be durable and resumable
- **Rationale**: Long-running operations (fetching, indexing) must survive process crashes
- **Implementation**: DBOS provides automatic checkpointing and recovery

### 3. Logging and Observability
- **Requirement**: All workflow output must be captured to log files
- **Rationale**: Users need to monitor progress after CLI exits
- **Implementation**:
  - Redirect stdout/stderr to log files using `os.dup2()`
  - Configure Python logging with FileHandler
  - Log files stored in `.kurt/logs/workflow-{id}.log`

### 4. Signal Handling
- **Requirement**: Background process must survive parent termination
- **Rationale**: Process should continue even when terminal/SSH session closes
- **Implementation**:
  - Ignore SIGHUP (terminal hangup) with `signal.SIG_IGN`
  - Ignore SIGTERM from parent process
  - Still respond to direct SIGINT/SIGKILL for debugging

### 5. DBOS Thread Pool Initialization
- **Requirement**: DBOS executor threads must be properly initialized in subprocess
- **Rationale**: DBOS ThreadPoolExecutor may not auto-start in subprocess environment
- **Implementation**:
  - Prime thread pool with dummy workflow on startup
  - Force multiple status checks to trigger thread creation
  - Wait for queue processing to start before continuing

## Implementation Pattern

### Worker Process Structure
```python
def run_workflow_worker(workflow_name, workflow_args_json, priority):
    """Execute workflow in background worker process."""

    # 1. Signal handling setup
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)

    # 2. Initialize DBOS
    init_dbos()
    dbos_instance = get_dbos()

    # 3. Prime thread pool (CRITICAL for subprocess)
    dummy_workflow = lambda: {"status": "primed"}
    dummy_handle = DBOS.start_workflow(dummy_workflow, workflow_id=unique_id)
    # Wait for completion to prove threads are working

    # 4. Setup logging before workflow starts
    setup_workflow_logging(temp_log_file)
    os.dup2(log_fd, sys.stdout.fileno())
    os.dup2(log_fd, sys.stderr.fileno())

    # 5. Start actual workflow
    handle = DBOS.start_workflow(workflow_func, **workflow_args)

    # 6. Rename log file with workflow ID
    temp_log_file.rename(f"workflow-{handle.workflow_id}.log")

    # 7. Wait and monitor
    while not workflow_complete:
        status = handle.get_status()
        # Periodic logging and flushing

    # 8. Clean shutdown
    DBOS.destroy(workflow_completion_timeout_sec=5)
```

### CLI Integration Pattern
```python
def run_with_background_support(workflow_func, args, background=False):
    if background:
        # Serialize arguments
        workflow_args_json = json.dumps(args)

        # Create ID communication file
        id_file = tempfile.NamedTemporaryFile(delete=False)

        # Spawn detached worker
        subprocess.Popen(
            [sys.executable, "-m", "kurt.workflows._worker",
             workflow_name, workflow_args_json, priority],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env={"KURT_WORKFLOW_ID_FILE": id_file}
        )

        # Wait for workflow ID
        workflow_id = read_id_file(id_file)

        # Report to user
        print(f"Workflow started: {workflow_id}")
        print(f"Logs: .kurt/logs/workflow-{workflow_id}.log")
```

## Timing Requirements (CI Environment)

### Initialization Timeouts
- **Thread pool priming**: 3 seconds max
- **Queue dequeue wait**: 5 seconds (CI needs more time)
- **Status check attempts**: 20 attempts with 1s delay
- **Total workflow timeout**: 600 seconds (10 minutes)

### Log Flushing
- **Frequency**: Every 5 seconds during execution
- **Method**: Flush both Python handlers and OS file descriptors
- **Critical points**: Before exit, after errors

## File Management

### Log File Lifecycle
1. Create temporary log file: `workflow-temp-{pid}.log`
2. Configure logging and redirect stdout/stderr
3. Start workflow and get ID
4. Rename to final: `workflow-{id}.log`
5. Keep same file descriptor (no handler recreation)

### File Descriptor Management
- Use `os.dup2()` for atomic redirection
- Close original fd after duplication
- Flush with `os.fsync()` for OS-level persistence

## Error Handling

### Graceful Degradation
- Continue if thread pool priming fails
- Log warnings but don't abort on non-critical errors
- Always attempt DBOS shutdown even on error

### Cleanup Guarantees
- Register `atexit` handler for log flushing
- Use try/finally for DBOS shutdown
- Flush logs even on exception

## Testing Requirements

### Integration Tests Must Verify
1. Log file creation within 10 seconds
2. Workflow ID extraction from output or log filename
3. Status transitions from PENDING to RUNNING
4. Actual workflow logs appear (not just monitoring)
5. Process survives parent termination

### CI-Specific Considerations
- Longer timeouts for slower environments
- More status check attempts
- Accept both message formats for compatibility
- Unique test IDs to prevent deduplication

## Dependencies

### Required Python Packages
```python
# Core workflow engine
dbos >= 0.1.0

# Logging and process management (stdlib)
import logging
import subprocess
import signal
import os
import sys
import atexit
import time
import json
import tempfile
```

### System Requirements
- Python 3.10+
- POSIX-compliant OS (Linux, macOS)
- SQLite for DBOS persistence
- Write access to `.kurt/logs/` directory

## Security Considerations

1. **Input Validation**: JSON arguments must be validated
2. **File Permissions**: Log files created with 0o644
3. **Signal Safety**: Only ignore specific signals, not all
4. **Process Isolation**: Each workflow in separate process
5. **Resource Limits**: 10-minute timeout prevents runaway processes

## Performance Considerations

1. **Startup Overhead**: ~5-8 seconds in CI for full initialization
2. **Memory Usage**: Each worker process ~50-100MB
3. **Disk I/O**: Log flushing every 5 seconds
4. **Database Connections**: One SQLite connection per worker

## Monitoring and Debugging

### User Commands
```bash
# Check workflow status
kurt workflows status {id}

# List all workflows
kurt workflows list

# Follow logs
kurt workflows follow {id} --wait

# View logs directly
cat .kurt/logs/workflow-{id}.log
```

### Debug Techniques
1. Check process still running: `ps aux | grep _worker`
2. Monitor log file growth: `tail -f .kurt/logs/workflow-*.log`
3. Database state: `sqlite3 .kurt/kurt.sqlite "SELECT * FROM dbos_workflow_status"`
4. Signal testing: `kill -HUP {pid}` should not terminate

## Future Enhancements

1. **Resource Limits**: CPU/memory limits per workflow
2. **Priority Queues**: Better queue management in DBOS
3. **Distributed Execution**: Multi-machine workflow distribution
4. **Live Streaming**: WebSocket-based log streaming
5. **Retry Policies**: Configurable retry strategies
6. **Workflow Composition**: Chain workflows together
7. **Scheduled Execution**: Cron-like workflow scheduling
8. **Notification System**: Email/Slack on completion