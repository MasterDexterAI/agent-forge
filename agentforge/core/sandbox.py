import asyncio
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from docker.errors import DockerException, NotFound

import docker
from agentforge.config import settings
from agentforge.core.guards import safe_path
from agentforge.metrics import SANDBOX_ACTIVE, SANDBOX_SECONDS, SANDBOX_TIMEOUTS

MAX_OUTPUT_CHARS = 12_000
_slots = asyncio.Semaphore(settings.max_concurrent_sandboxes)


@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    duration_s: float


def _clip(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    half = MAX_OUTPUT_CHARS // 2
    return f"{text[:half]}\n...[output truncated]...\n{text[-half:]}"


def _write_files(workdir: Path, files: dict[str, str]) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    os.chmod(workdir, 0o777)
    for raw, content in files.items():
        target = workdir / safe_path(raw)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(target.parent, 0o777)
        target.write_text(content)
        os.chmod(target, 0o666)


def _execute(workdir: str, command: str) -> SandboxResult:
    client = docker.from_env()
    container = None
    started = time.monotonic()
    runtime = settings.sandbox_runtime if settings.sandbox_runtime not in ("", "runc") else None
    try:
        container = client.containers.run(
            image=settings.sandbox_image,
            command=["sleep", str(settings.sandbox_timeout_s + 30)],
            detach=True,
            runtime=runtime,
            mem_limit=settings.sandbox_mem,
            memswap_limit=settings.sandbox_mem,
            nano_cpus=500_000_000,
            pids_limit=64,
            read_only=True,
            network_mode="none",
            volumes={workdir: {"bind": "/workspace", "mode": "rw"}},
            tmpfs={"/tmp": "size=64m,mode=1777"},
            working_dir="/workspace",
            user="1000:1000",
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            environment={"PYTHONDONTWRITEBYTECODE": "1", "HOME": "/tmp"},
            labels={"agentforge": "sandbox"},
        )
        exit_code, output = container.exec_run(
            ["timeout", "--kill-after=5", str(settings.sandbox_timeout_s), "sh", "-c", command],
            demux=True,
            workdir="/workspace",
            user="1000:1000",
        )
        out, err = output if output else (b"", b"")
        timed_out = exit_code in (124, 137)
        if timed_out:
            SANDBOX_TIMEOUTS.inc()
        return SandboxResult(
            exit_code=exit_code,
            stdout=_clip((out or b"").decode(errors="replace")),
            stderr=_clip((err or b"").decode(errors="replace"))
            + ("\nTIMEOUT: tests exceeded the time limit" if timed_out else ""),
            timed_out=timed_out,
            duration_s=time.monotonic() - started,
        )
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except (NotFound, DockerException):
                pass


async def run_in_sandbox(run_id: str, iteration: int, files: dict[str, str], command: str) -> SandboxResult:
    workdir = Path(settings.workspace_root) / run_id / f"iter-{iteration}-{int(time.time() * 1000)}"
    _write_files(workdir, files)
    try:
        async with _slots:
            SANDBOX_ACTIVE.inc()
            try:
                result = await asyncio.to_thread(_execute, str(workdir), command)
            finally:
                SANDBOX_ACTIVE.dec()
        SANDBOX_SECONDS.observe(result.duration_s)
        return result
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# # docker container runner, which will executes code safely

# import docker

# def create_hardened_sandbox(host_workspace_dir: str):
#     client = docker.from_env()
#     return client.containers.run(
#         image="agentforge-sandbox:latest",
#         command="sleep 3600",
#         detach=True,
#         mem_limit="1024m",
#         pids_limit=100,
#         read_only=True,
#         volumes={host_workspace_dir: {"bind": "/workspace", "mode": "rw"}},
#         tmpfs={"/tmp": "size=128m,mode=1777"},
#         working_dir="/workspace",
#         user="sandboxuser",
#         security_opt=["no-new-privileges:true"],
#         cap_drop=["ALL"],
#         network_mode="none",
#     )
