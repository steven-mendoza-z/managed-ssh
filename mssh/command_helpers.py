import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

import click

from mssh.destination.interpreter import destination_interpreter
from mssh.destination.solve import (
    HOSTS_KEY,
    alias_kind,
    key_for_destination,
    save_host,
    save_target,
)
from mssh.messages import success_message, warning_message
from mssh.verifiers import (
    interruptIf_condition,
    interruptIf_invalidImportMergeOptions,
    interruptIf_notConfirmed,
)


def _run_command(command):
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def _is_windows_local_path(value: str) -> bool:
    return bool(re.match(r"^[a-zA-Z]:[\\/]", value))


def _is_remote_copy_spec(value: str) -> bool:
    if _is_windows_local_path(value):
        return False
    return ":" in value and value.split(":", 1)[0] != ""


def _normalize_cli_key(key_path: Optional[str]) -> Optional[str]:
    if key_path is None:
        return None
    return str(Path(key_path).expanduser().resolve())


def _build_identity_options(keys: List[str]) -> List[str]:
    options: List[str] = []
    seen = set()
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        options.extend(["-i", key])
    return options


def _resolve_copy_endpoint(value: str) -> Tuple[str, bool, Optional[str]]:
    if not _is_remote_copy_spec(value):
        return value, False, None

    origin, remote_path = value.split(":", 1)
    solved_origin = destination_interpreter(origin)
    auto_key = key_for_destination(origin)
    return f"{solved_origin}:{remote_path}", True, auto_key


def _save_alias(kind: str, alias: str, value: str, key_path: Optional[str] = None) -> None:
    found_kind = alias_kind(alias)
    existing_kind_name = found_kind[:-1] if found_kind else "unknown"
    interruptIf_condition(
        found_kind and found_kind != kind,
        f"Alias '{alias}' already exists as {existing_kind_name}. Use another alias name.",
    )

    if found_kind == kind:
        warning_message(f"Alias '{alias}' already exists as {kind[:-1]}.")
        interruptIf_notConfirmed(click.confirm("Do you want to overwrite it?", default=False))

    normalized_key = _normalize_cli_key(key_path)
    if kind == HOSTS_KEY:
        save_host(alias, value, normalized_key)
    else:
        save_target(alias, value, normalized_key)

    if normalized_key:
        success_message(f"Saved {kind[:-1]} alias '{alias}' -> '{value}' (key: {normalized_key})")
    else:
        success_message(f"Saved {kind[:-1]} alias '{alias}' -> '{value}'")


def _validate_import_options(replace: bool, overwrite: bool, skip_existing: bool) -> None:
    interruptIf_invalidImportMergeOptions(replace, overwrite, skip_existing)
