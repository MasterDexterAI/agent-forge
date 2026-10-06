# prove the patch works or it does not

from agentforge.agents.common import meta, plan_text, usage_delta
from agentforge.config import settings
from agentforge.core.guards import (
    compress_error,
    error_signature,
    hash_files,
    validate_test_files,
)
from agentforge.core.llm import structured_call
from agentforge.core.sandbox import run_in_sandbox
from agentforge.core.schemas import TestSuiteSpec
from agentforge.prompts.tester_prompt import TEST_WRITER_SYSTEM

TEST_COMMAND = "python -m pytest -q -p no:cacheprovider tests"


async def write_tests_node(state: dict) -> dict:
    suite, usage = await structured_call(
        settings.tester_model,
        TEST_WRITER_SYSTEM,
        f"PLAN:\n{plan_text(state)}",
        TestSuiteSpec,
        meta(state, "test_writer"),
    )
    files = validate_test_files(suite.files)
    return {
        "test_files": files,
        "tests_hash": hash_files(files),
        "status": "tests_written",
        **usage_delta(usage),
    }


async def run_tests_node(state: dict) -> dict:
    iteration = state["iteration_count"] + 1
    if state.get("guard_violation"):
        message = f"PATCH REJECTED BEFORE RUNNING: {state['guard_violation']}"
        return {
            "test_passed": False,
            "execution_exit_code": 1,
            "execution_stdout": "",
            "execution_stderr": message,
            "error_signatures": [error_signature(message)],
            "iteration_count": iteration,
            "status": "tested",
        }

    files = {**state["code_files"], **state["test_files"]}
    result = await run_in_sandbox(state["run_id"], iteration, files, TEST_COMMAND)
    passed = result.exit_code == 0
    delta = {
        "test_passed": passed,
        "execution_exit_code": result.exit_code,
        "execution_stdout": result.stdout,
        "execution_stderr": result.stderr,
        "iteration_count": iteration,
        "status": "tested",
    }
    if not passed:
        delta["error_signatures"] = [error_signature(compress_error(result.stdout, result.stderr))]
    return delta
