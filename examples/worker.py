"""
Example: Fail-Closed Worker

Demonstrates where to place enforcement boundaries in a typical worker loop.

Boundaries:
1) Startup        -> enforce_startup()
2) Before job     -> enforce_boundary()
3) Before cost    -> enforce_boundary()
4) Before sidefx  -> enforce_boundary()
5) Before fan-out -> enforce_boundary()

Note:
- The guard is fail-closed. On denial or validation failure it hard-terminates the process.
"""

import sys
import time
from execution_gate.guard import enforce_startup, enforce_boundary


def _log(msg: str) -> None:
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def pull_job():
    # Mock queue intake
    return {"job_id": "job-001", "tasks": ["task-a", "task-b", "task-c"]}


def call_costly_tool(task_name: str):
    # Simulate cost (LLM, paid API, GPU job, etc.)
    time.sleep(0.2)


def perform_side_effect(task_name: str):
    # Simulate irreversible action (DB write, email, charge, etc.)
    time.sleep(0.1)


def main():
    # 1) STARTUP BOUNDARY
    device_id = enforce_startup()
    _log(f"authorized startup as device_id={device_id}")

    while True:
        # 2) BEFORE JOB / WORK UNIT
        enforce_boundary(device_id)

        job = pull_job()
        _log(f"pulled {job['job_id']}")

        # 5) BEFORE FAN-OUT (before batch loops / parallel dispatch)
        enforce_boundary(device_id)

        for task in job["tasks"]:
            # 3) BEFORE COST
            enforce_boundary(device_id)
            call_costly_tool(task)

            # 4) BEFORE SIDE EFFECT
            enforce_boundary(device_id)
            perform_side_effect(task)

            _log(f"completed {task}")

        time.sleep(2.0)


if __name__ == "__main__":
    main()
