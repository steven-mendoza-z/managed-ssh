import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

import click

from mssh import __version__
from mssh.destination.interpreter import destination_interpreter
from mssh.destination.solve import (
    HOSTS_KEY,
    KEYS_KEY,
    TARGETS_KEY,
    alias_kind,
    aliases_file_path,
    delete_alias,
    export_aliases,
    key_for_destination,
    is_host,
    is_target,
    load_aliases,
    load_aliases_from_file,
    list_hosts,
    list_keys,
    list_targets,
    rename_alias,
    replace_aliases,
    set_alias_key,
    save_host,
    save_target,
    unset_alias_key,
)
from mssh.keys import set_keys
from mssh.messages import error_message, info_message, message, success_message, warning_message


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
    if found_kind and found_kind != kind:
        error_message(
            f"Alias '{alias}' already exists as {found_kind[:-1]}. "
            f"Use another alias name."
        )

    if found_kind == kind:
        warning_message(f"Alias '{alias}' already exists as {kind[:-1]}.")
        if not click.confirm("Do you want to overwrite it?", default=False):
            info_message("Operation cancelled.")
            return

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
    if replace and (overwrite or skip_existing):
        error_message("Use either --replace OR merge options (--overwrite/--skip-existing).")
    if overwrite and skip_existing:
        error_message("Use only one merge strategy: --overwrite or --skip-existing.")


@click.group()
@click.version_option(__version__, prog_name="mssh")
def cli():
    """Managed-SSH CLI."""


@cli.command()
@click.argument("destination")
@click.option(
    "--key",
    "key_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=str),
    help="SSH private key path (overrides alias key).",
)
def access(destination: str, key_path: Optional[str]):
    """SSH into destination (alias, user@alias, user@host)."""
    solved_destination = destination_interpreter(destination)
    effective_key = _normalize_cli_key(key_path) or key_for_destination(destination)

    command = ["ssh"]
    if effective_key:
        command.extend(["-i", effective_key])
    command.append(solved_destination)
    _run_command(command)


@cli.command()
@click.argument("source")
@click.argument("target")
@click.option(
    "--key",
    "key_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=str),
    help="SSH private key path (overrides alias keys).",
)
def copy(source: str, target: str, key_path: Optional[str]):
    """SCP copy with alias resolution on both remote sides."""
    solved_source, source_is_remote, source_auto_key = _resolve_copy_endpoint(source)
    solved_target, target_is_remote, target_auto_key = _resolve_copy_endpoint(target)

    command = ["scp"]
    if source_is_remote and target_is_remote:
        # Ensure both remote sides are negotiated from local host.
        command.append("-3")

    normalized_key = _normalize_cli_key(key_path)
    if normalized_key:
        command.extend(["-i", normalized_key])
    else:
        auto_keys = [k for k in (source_auto_key, target_auto_key) if k]
        command.extend(_build_identity_options(auto_keys))

    command.extend([solved_source, solved_target])
    _run_command(command)


@cli.command("save-host")
@click.argument("alias")
@click.argument("host")
@click.option(
    "--key",
    "key_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=str),
    help="SSH private key to associate with alias.",
)
def save_host_alias(alias: str, host: str, key_path: Optional[str]):
    """Save a host alias (alias -> host)."""
    if not is_host(host):
        error_message("Host value must not contain '@'.")
    _save_alias(HOSTS_KEY, alias, host, key_path=key_path)


@cli.command("save-target")
@click.argument("alias")
@click.argument("target")
@click.option(
    "--key",
    "key_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=str),
    help="SSH private key to associate with alias.",
)
def save_target_alias(alias: str, target: str, key_path: Optional[str]):
    """Save a target alias (alias -> user@host)."""
    if not is_target(target):
        error_message("Target value must be in format user@host.")
    _save_alias(TARGETS_KEY, alias, target, key_path=key_path)


@cli.command()
@click.argument("alias")
@click.argument("value")
@click.option(
    "--key",
    "key_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=str),
    help="SSH private key to associate with alias.",
)
def save(alias: str, value: str, key_path: Optional[str]):
    """Save alias automatically as host or target."""
    if is_target(value):
        _save_alias(TARGETS_KEY, alias, value, key_path=key_path)
        return

    if is_host(value):
        _save_alias(HOSTS_KEY, alias, value, key_path=key_path)
        return

    error_message("Value must be either host or user@host.")


@cli.command("list")
def list_aliases():
    """List saved host and target aliases."""
    hosts = list_hosts()
    targets = list_targets()
    keys = list_keys()

    message("Hosts:")
    if hosts:
        for alias, host in hosts.items():
            key_note = f" [key: {keys[alias]}]" if alias in keys else ""
            message(f"  {alias} -> {host}{key_note}")
    else:
        message("  (none)")

    message("")
    message("Targets:")
    if targets:
        for alias, target in targets.items():
            key_note = f" [key: {keys[alias]}]" if alias in keys else ""
            message(f"  {alias} -> {target}{key_note}")
    else:
        message("  (none)")


@cli.command("set-key")
@click.argument("alias")
@click.argument("key_path", type=click.Path(exists=True, dir_okay=False, readable=True, path_type=str))
def set_key_command(alias: str, key_path: str):
    """Set or replace SSH key for an existing alias."""
    try:
        normalized = set_alias_key(alias, _normalize_cli_key(key_path) or key_path)
    except ValueError as exc:
        error_message(str(exc))
        return
    success_message(f"Updated key for alias '{alias}' -> '{normalized}'")


@cli.command("unset-key")
@click.argument("alias")
def unset_key_command(alias: str):
    """Remove SSH key association from an alias."""
    kind = alias_kind(alias)
    if not kind:
        error_message(f"Alias '{alias}' was not found.")
        return

    removed = unset_alias_key(alias)
    if removed:
        success_message(f"Removed key from alias '{alias}'")
    else:
        info_message(f"Alias '{alias}' has no key configured.")


@cli.command("delete")
@click.argument("alias")
@click.option("-y", "--yes", is_flag=True, help="Delete without confirmation prompt.")
def delete_alias_command(alias: str, yes: bool):
    """Delete a host or target alias."""
    kind = alias_kind(alias)
    if not kind:
        error_message(f"Alias '{alias}' was not found.")
        return

    kind_name = kind[:-1]

    if not yes:
        if not click.confirm(
            f"Delete {kind_name} alias '{alias}'?",
            default=False,
        ):
            info_message("Operation cancelled.")
            return

    deleted_kind = delete_alias(alias)
    if not deleted_kind:
        error_message(f"Alias '{alias}' was not found.")
    success_message(f"Deleted {deleted_kind[:-1]} alias '{alias}'")


@cli.command("rename")
@click.argument("old_alias")
@click.argument("new_alias")
@click.option("-y", "--yes", is_flag=True, help="Rename without confirmation prompt.")
def rename_alias_command(old_alias: str, new_alias: str, yes: bool):
    """Rename a host or target alias."""
    old_kind = alias_kind(old_alias)
    if not old_kind:
        error_message(f"Alias '{old_alias}' was not found.")
        return

    if old_alias == new_alias:
        info_message("Old alias and new alias are the same. No changes applied.")
        return

    existing_new_kind = alias_kind(new_alias)
    if existing_new_kind:
        warning_message(
            f"Alias '{new_alias}' already exists as {existing_new_kind[:-1]} and will be replaced."
        )
        if not yes and not click.confirm("Do you want to continue?", default=False):
            info_message("Operation cancelled.")
            return
        delete_alias(new_alias)
    elif not yes and not click.confirm(
        f"Rename alias '{old_alias}' to '{new_alias}'?",
        default=False,
    ):
        info_message("Operation cancelled.")
        return

    renamed_kind = rename_alias(old_alias, new_alias)
    if not renamed_kind:
        error_message(f"Alias '{old_alias}' was not found.")
        return
    success_message(f"Renamed {renamed_kind[:-1]} alias '{old_alias}' -> '{new_alias}'")


@cli.command("export")
@click.option(
    "--file",
    "file_path",
    default="mssh-aliases.json",
    show_default=True,
    type=click.Path(dir_okay=False, writable=True, path_type=str),
    help="Destination JSON file for aliases backup.",
)
def export_aliases_command(file_path: str):
    """Export aliases to a JSON file."""
    try:
        exported = export_aliases(file_path)
    except ValueError as exc:
        error_message(str(exc))
        return

    info_message(f"Aliases source: {aliases_file_path()}")
    success_message(f"Aliases exported to: {exported}")


@cli.command("import")
@click.option(
    "--file",
    "file_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=str),
    help="Source JSON file with aliases.",
)
@click.option(
    "--replace",
    is_flag=True,
    help="Replace all local aliases with imported file.",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="On merge, overwrite existing aliases with imported values.",
)
@click.option(
    "--skip-existing",
    is_flag=True,
    help="On merge, keep existing aliases and skip conflicts.",
)
@click.option("-y", "--yes", is_flag=True, help="Run without confirmation prompts.")
def import_aliases_command(
    file_path: str,
    replace: bool,
    overwrite: bool,
    skip_existing: bool,
    yes: bool,
):
    """Import aliases from a JSON file."""
    _validate_import_options(replace, overwrite, skip_existing)

    try:
        imported = load_aliases_from_file(file_path)
    except ValueError as exc:
        error_message(str(exc))
        return

    if replace:
        if not yes and not click.confirm(
            "Replace all local aliases with imported aliases?",
            default=False,
        ):
            info_message("Operation cancelled.")
            return
        replace_aliases(imported)
        success_message(
            "Import complete (replace): "
            f"{len(imported[HOSTS_KEY])} hosts, {len(imported[TARGETS_KEY])} targets."
        )
        return

    current = load_aliases()
    merged = {
        HOSTS_KEY: dict(current[HOSTS_KEY]),
        TARGETS_KEY: dict(current[TARGETS_KEY]),
        KEYS_KEY: dict(current[KEYS_KEY]),
    }

    added = 0
    overwritten_count = 0
    skipped = 0
    unchanged = 0
    key_added = 0
    key_overwritten = 0
    key_skipped = 0
    key_unchanged = 0

    for kind in (HOSTS_KEY, TARGETS_KEY):
        opposite = TARGETS_KEY if kind == HOSTS_KEY else HOSTS_KEY
        kind_name = kind[:-1]
        opposite_name = opposite[:-1]

        for alias, imported_value in imported[kind].items():
            if alias in merged[opposite]:
                warning_message(
                    f"Skipped {kind_name} '{alias}' because local alias exists as {opposite_name}."
                )
                skipped += 1
                continue

            current_value = merged[kind].get(alias)
            if current_value is None:
                merged[kind][alias] = imported_value
                added += 1
                continue

            if current_value == imported_value:
                unchanged += 1
                continue

            if overwrite:
                merged[kind][alias] = imported_value
                overwritten_count += 1
                continue

            if skip_existing:
                skipped += 1
                continue

            warning_message(
                f"Conflict for {kind_name} '{alias}': "
                f"local='{current_value}' imported='{imported_value}'"
            )
            if yes or click.confirm("Overwrite this alias?", default=False):
                merged[kind][alias] = imported_value
                overwritten_count += 1
            else:
                skipped += 1

    for alias, imported_key in imported[KEYS_KEY].items():
        if alias not in merged[HOSTS_KEY] and alias not in merged[TARGETS_KEY]:
            warning_message(f"Skipped key for unknown alias '{alias}'.")
            key_skipped += 1
            continue

        current_key = merged[KEYS_KEY].get(alias)
        if current_key is None:
            merged[KEYS_KEY][alias] = imported_key
            key_added += 1
            continue

        if current_key == imported_key:
            key_unchanged += 1
            continue

        if overwrite:
            merged[KEYS_KEY][alias] = imported_key
            key_overwritten += 1
            continue

        if skip_existing:
            key_skipped += 1
            continue

        warning_message(
            f"Key conflict for alias '{alias}': "
            f"local='{current_key}' imported='{imported_key}'"
        )
        if yes or click.confirm("Overwrite this key?", default=False):
            merged[KEYS_KEY][alias] = imported_key
            key_overwritten += 1
        else:
            key_skipped += 1

    replace_aliases(merged)
    success_message(
        "Import complete (merge): "
        f"added={added}, overwritten={overwritten_count}, skipped={skipped}, unchanged={unchanged}; "
        f"keys_added={key_added}, keys_overwritten={key_overwritten}, "
        f"keys_skipped={key_skipped}, keys_unchanged={key_unchanged}."
    )
    info_message(f"Aliases file: {aliases_file_path()}")


@cli.command("keygen")
@click.argument("key_name")
@click.argument("passphrase", required=False, default="")
def keygen_command(key_name: str, passphrase: str):
    """Generate an SSH key under ~/.mssh/keys/<key_name>."""
    key_path = set_keys(key_name, passphrase=passphrase)
    success_message(f"Key ready: {key_path}")


def main():
    cli.main(standalone_mode=True, color=True)


if __name__ == "__main__":
    main()
