"""Test to verify if DBOS runs independent steps in parallel.

Creates a simple DAG using native DBOS decorators:
- step_a (no deps) -> step_c
- step_b (no deps) -> step_c

Step A and B should run in parallel if we use asyncio.gather within the workflow.
"""

import asyncio
import logging
import time

import pytest
from dbos import DBOS

logger = logging.getLogger(__name__)

# Track execution times
execution_log: list[dict] = []


def reset_execution_log():
    """Reset the execution log."""
    global execution_log
    execution_log = []


def log_execution(step_name: str, action: str):
    """Log step execution with timestamp."""
    execution_log.append(
        {
            "step": step_name,
            "action": action,
            "time": time.time(),
        }
    )
    logger.info(f"[{time.time():.3f}] {step_name}: {action}")


# ============================================================================
# Native DBOS Steps
# ============================================================================


@DBOS.step()
def step_a_sync():
    """Step A - runs for 1 second (sync)."""
    log_execution("step_a", "start")
    time.sleep(1.0)
    log_execution("step_a", "end")
    return {"step": "a", "result": "done"}


@DBOS.step()
def step_b_sync():
    """Step B - runs for 1 second (sync)."""
    log_execution("step_b", "start")
    time.sleep(1.0)
    log_execution("step_b", "end")
    return {"step": "b", "result": "done"}


@DBOS.step()
def step_c_sync(a_result: dict, b_result: dict):
    """Step C - depends on A and B (sync)."""
    log_execution("step_c", "start")
    time.sleep(0.5)
    log_execution("step_c", "end")
    return {"step": "c", "a": a_result, "b": b_result}


@DBOS.step()
async def step_a_async():
    """Step A - runs for 1 second (async)."""
    log_execution("step_a_async", "start")
    await asyncio.sleep(1.0)
    log_execution("step_a_async", "end")
    return {"step": "a", "result": "done"}


@DBOS.step()
async def step_b_async():
    """Step B - runs for 1 second (async)."""
    log_execution("step_b_async", "start")
    await asyncio.sleep(1.0)
    log_execution("step_b_async", "end")
    return {"step": "b", "result": "done"}


@DBOS.step()
async def step_c_async(a_result: dict, b_result: dict):
    """Step C - depends on A and B (async)."""
    log_execution("step_c_async", "start")
    await asyncio.sleep(0.5)
    log_execution("step_c_async", "end")
    return {"step": "c", "a": a_result, "b": b_result}


# ============================================================================
# Workflows
# ============================================================================


@DBOS.workflow()
def workflow_sequential():
    """Run A, B, C sequentially."""
    a_result = step_a_sync()
    b_result = step_b_sync()
    c_result = step_c_sync(a_result, b_result)
    return c_result


@DBOS.workflow()
async def workflow_parallel_async():
    """Run A and B in parallel using asyncio.gather, then C."""
    # Run A and B in parallel
    a_result, b_result = await asyncio.gather(
        step_a_async(),
        step_b_async(),
    )
    # Then run C
    c_result = await step_c_async(a_result, b_result)
    return c_result


@DBOS.workflow()
async def workflow_sync_steps_via_gather():
    """Try to run sync steps A and B in parallel via asyncio.gather."""
    # This tests if sync DBOS steps can be parallelized when called from async context
    a_result, b_result = await asyncio.gather(
        asyncio.to_thread(step_a_sync),
        asyncio.to_thread(step_b_sync),
    )
    c_result = step_c_sync(a_result, b_result)
    return c_result


@DBOS.workflow()
async def workflow_mixed_sync_async():
    """Run sync step A and async step B in parallel."""

    async def run_sync_a():
        return await asyncio.to_thread(step_a_sync)

    a_result, b_result = await asyncio.gather(
        run_sync_a(),
        step_b_async(),
    )
    c_result = await step_c_async(a_result, b_result)
    return c_result


# ============================================================================
# Tests
# ============================================================================


@pytest.fixture
def dbos_local():
    """Initialize DBOS with local database for testing."""
    DBOS.destroy()  # Clean up any previous instance
    DBOS(config={"name": "parallel_test", "database": {"type": "local"}})
    DBOS.launch()
    yield
    DBOS.destroy()


class TestDBOSParallelExecution:
    """Test DBOS parallel execution patterns."""

    @pytest.fixture(autouse=True)
    def setup(self, dbos_local):
        """Reset execution log and initialize DBOS before each test."""
        reset_execution_log()

    def test_sequential_workflow_timing(self):
        """Test that sequential workflow takes ~2.5 seconds."""
        reset_execution_log()

        start_time = time.time()
        result = workflow_sequential()
        elapsed = time.time() - start_time

        logger.info(f"\nSequential workflow completed in {elapsed:.2f}s")
        logger.info(f"Result: {result}")

        # Sequential should take ~2.5 seconds (1 + 1 + 0.5)
        assert elapsed >= 2.0, f"Expected >= 2.0s, got {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_parallel_workflow_timing(self):
        """Test that parallel workflow takes ~1.5 seconds."""
        reset_execution_log()

        start_time = time.time()
        result = await workflow_parallel_async()
        elapsed = time.time() - start_time

        logger.info(f"\nParallel workflow completed in {elapsed:.2f}s")
        logger.info(f"Result: {result}")

        # Analyze execution log
        a_start = next(
            (e["time"] for e in execution_log if "step_a" in e["step"] and e["action"] == "start"),
            None,
        )
        b_start = next(
            (e["time"] for e in execution_log if "step_b" in e["step"] and e["action"] == "start"),
            None,
        )

        if a_start and b_start:
            start_diff = abs(b_start - a_start)
            logger.info(f"Time between A and B start: {start_diff:.3f}s")

            # If parallel, A and B should start within 0.1s of each other
            if start_diff < 0.1:
                logger.info("Steps A and B ran in PARALLEL")
                # Parallel should take ~1.5 seconds (max(1,1) + 0.5)
                assert elapsed < 2.0, f"Expected < 2.0s for parallel, got {elapsed:.2f}s"
            else:
                logger.info("Steps A and B ran SEQUENTIALLY")


def analyze_parallelism(test_name: str):
    """Analyze execution log for parallelism."""
    a_start = next(
        (e["time"] for e in execution_log if "step_a" in e["step"] and e["action"] == "start"), None
    )
    b_start = next(
        (e["time"] for e in execution_log if "step_b" in e["step"] and e["action"] == "start"), None
    )
    a_end = next(
        (e["time"] for e in execution_log if "step_a" in e["step"] and e["action"] == "end"), None
    )

    if a_start and b_start:
        start_diff = abs(b_start - a_start)
        # Check if B started before A ended (overlap = parallel)
        overlap = b_start < a_end if a_end else False
        parallel = start_diff < 0.1 or overlap

        print(f"   A start: {a_start:.3f}")
        print(f"   B start: {b_start:.3f}")
        print(f"   Start diff: {start_diff:.3f}s")
        print(f"   B started before A ended: {overlap}")
        print(f"   → PARALLEL: {parallel}")
        return parallel
    return False


async def run_all_async_tests():
    """Run all async tests in single event loop."""
    results = {}

    # Test 1: Async workflow with async steps + gather
    print("\n1. ASYNC workflow + async steps + gather (expected ~1.5s, parallel):")
    reset_execution_log()
    start = time.time()
    try:
        await workflow_parallel_async()
        elapsed = time.time() - start
        print(f"   Elapsed: {elapsed:.2f}s")
        results["async_gather"] = {
            "elapsed": elapsed,
            "parallel": analyze_parallelism("async_gather"),
        }
    except Exception as e:
        print(f"   Error: {e}")
        results["async_gather"] = {"error": str(e)}

    # Test 2: Async workflow with sync steps via to_thread
    print("\n2. ASYNC workflow + sync steps via to_thread (expected ~1.5s if parallel):")
    reset_execution_log()
    start = time.time()
    try:
        await workflow_sync_steps_via_gather()
        elapsed = time.time() - start
        print(f"   Elapsed: {elapsed:.2f}s")
        results["sync_via_thread"] = {
            "elapsed": elapsed,
            "parallel": analyze_parallelism("sync_via_thread"),
        }
    except Exception as e:
        print(f"   Error: {e}")
        results["sync_via_thread"] = {"error": str(e)}

    # Test 3: Mixed sync and async
    print("\n3. ASYNC workflow + mixed sync/async steps (expected ~1.5s if parallel):")
    reset_execution_log()
    start = time.time()
    try:
        await workflow_mixed_sync_async()
        elapsed = time.time() - start
        print(f"   Elapsed: {elapsed:.2f}s")
        results["mixed"] = {"elapsed": elapsed, "parallel": analyze_parallelism("mixed")}
    except Exception as e:
        print(f"   Error: {e}")
        results["mixed"] = {"error": str(e)}

    return results


def run_timing_test():
    """Run timing test without pytest (for manual testing)."""

    # Initialize and launch DBOS
    DBOS.destroy()  # Clean up any previous instance
    DBOS(config={"name": "parallel_test", "database": {"type": "local"}})
    DBOS.launch()

    print("=" * 60)
    print("Testing DBOS Parallel Execution Patterns")
    print("=" * 60)

    results = {}

    # Test sync workflow first (doesn't need async)
    print("\n0. SYNC Sequential workflow (expected ~2.5s, sequential):")
    reset_execution_log()
    start = time.time()
    try:
        workflow_sequential()
        elapsed = time.time() - start
        print(f"   Elapsed: {elapsed:.2f}s")
        results["sync_sequential"] = {
            "elapsed": elapsed,
            "parallel": analyze_parallelism("sync_sequential"),
        }
    except Exception as e:
        print(f"   Error: {e}")
        results["sync_sequential"] = {"error": str(e)}

    # Run all async tests in single event loop
    async_results = asyncio.run(run_all_async_tests())
    results.update(async_results)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, data in results.items():
        if "error" in data:
            print(f"  {name}: ERROR - {data['error']}")
        else:
            status = "✓ PARALLEL" if data.get("parallel") else "✗ SEQUENTIAL"
            print(f"  {name}: {data['elapsed']:.2f}s {status}")
    print("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_timing_test()
