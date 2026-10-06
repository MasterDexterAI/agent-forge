import hashlib
import re
from pathlib import PurePosixPath

from agentforge.core.schemas import FileWrite

ALLOWED_SUFFIXES = {".py", ".txt", ".md", ".toml", ".json", ".cfg", ".ini", ".yaml", ".yml"}
PROTECTED_PREFIXES = ("tests", "hidden_tests", ".git", ".github")
MAX_FILE_BYTES = 100_000

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
]


class GuardError(Exception):
    pass


def safe_path(raw: str) -> str:
    cleaned = raw.strip()
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    path = PurePosixPath(cleaned)
    if not path.parts or path.is_absolute() or ".." in path.parts:
        raise GuardError(f"illegal path: {raw}")
    if len(path.parts) > 6:
        raise GuardError(f"path too deep: {raw}")
    if path.suffix not in ALLOWED_SUFFIXES:
        raise GuardError(f"file type not allowed: {raw}")
    return str(path)


def _check_size(item: FileWrite) -> None:
    if len(item.content.encode()) > MAX_FILE_BYTES:
        raise GuardError(f"file too large: {item.path}")


def validate_code_files(files: list[FileWrite]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in files:
        path = safe_path(item.path)
        name = PurePosixPath(path).name
        top = PurePosixPath(path).parts[0]
        if top in PROTECTED_PREFIXES or name == "conftest.py" or name.startswith("test_"):
            raise GuardError(f"coder may not write test files: {path}")
        _check_size(item)
        out[path] = item.content
    return out


def validate_test_files(files: list[FileWrite]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in files:
        path = safe_path(item.path)
        if not path.startswith("tests/"):
            path = f"tests/{PurePosixPath(path).name}"
        _check_size(item)
        out[path] = item.content
    return out


def hash_files(files: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.encode())
        digest.update(b"\0")
        digest.update(files[path].encode())
    return digest.hexdigest()


def scan_secrets(files: dict[str, str]) -> list[str]:
    hits = []
    for path, content in files.items():
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                hits.append(f"{path}: matches {pattern.pattern[:20]}")
    return hits


def compress_error(stdout: str, stderr: str, limit: int = 3000) -> str:
    lines = (stdout + "\n" + stderr).splitlines()
    keep = [
        line
        for line in lines
        if line.startswith(("E ", "E\t", "FAILED", "ERROR", ">", "Traceback"))
        or "Error" in line
        or line.strip().startswith("File ")
    ]
    text = "\n".join(keep) if keep else "\n".join(lines[-60:])
    return text[:limit]


def error_signature(text: str) -> str:
    normalized = re.sub(r"0x[0-9a-f]+|\d+", "N", text)
    first = next((l for l in normalized.splitlines() if l.startswith(("E ", "FAILED"))), normalized[:200])
    return hashlib.sha1(first.encode()).hexdigest()[:12]
