from typing import Optional

import click

from mssh.command_helpers import _normalize_cli_key, _save_alias
from mssh.destination.solve import (
    HOSTS_KEY,
    TARGETS_KEY,
    alias_kind,
    delete_alias,
    is_host,
    is_target,
    list_hosts,
    list_keys,
    list_targets,
    rename_alias,
    set_alias_key,
    unset_alias_key,
)
from mssh.messages import info_message, message, success_message, warning_message
from mssh.verifiers import (
    interruptIf_aliasMissing,
    interruptIf_none,
    interruptIf_notConfirmed,
    interruptIf_notHostOrTargetValue,
    interruptIf_notHostValue,
    interruptIf_notTargetValue,
    interruptIf_valueError,
)


@click.command("save-host")
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
    interruptIf_notHostValue(host)
    _save_alias(HOSTS_KEY, alias, host, key_path=key_path)


@click.command("save-target")
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
    interruptIf_notTargetValue(target)
    _save_alias(TARGETS_KEY, alias, target, key_path=key_path)


@click.command()
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
    interruptIf_notHostOrTargetValue(value)

    if is_target(value):
        _save_alias(TARGETS_KEY, alias, value, key_path=key_path)
        return

    if is_host(value):
        _save_alias(HOSTS_KEY, alias, value, key_path=key_path)
        return


@click.command("list")
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


@click.command("set-key")
@click.argument("alias")
@click.argument("key_path", type=click.Path(exists=True, dir_okay=False, readable=True, path_type=str))
def set_key_command(alias: str, key_path: str):
    """Set or replace SSH key for an existing alias."""
    normalized = interruptIf_valueError(set_alias_key, alias, _normalize_cli_key(key_path) or key_path)
    success_message(f"Updated key for alias '{alias}' -> '{normalized}'")


@click.command("unset-key")
@click.argument("alias")
def unset_key_command(alias: str):
    """Remove SSH key association from an alias."""
    kind = alias_kind(alias)
    interruptIf_aliasMissing(alias, kind)

    removed = unset_alias_key(alias)
    if removed:
        success_message(f"Removed key from alias '{alias}'")
    else:
        info_message(f"Alias '{alias}' has no key configured.")


@click.command("delete")
@click.argument("alias")
@click.option("-y", "--yes", is_flag=True, help="Delete without confirmation prompt.")
def delete_alias_command(alias: str, yes: bool):
    """Delete a host or target alias."""
    kind = alias_kind(alias)
    interruptIf_aliasMissing(alias, kind)

    kind_name = interruptIf_none(kind, f"Alias '{alias}' was not found.")[:-1]

    if not yes:
        interruptIf_notConfirmed(
            click.confirm(
                f"Delete {kind_name} alias '{alias}'?",
                default=False,
            )
        )

    deleted_kind = delete_alias(alias)
    deleted_kind = interruptIf_none(deleted_kind, f"Alias '{alias}' was not found.")
    success_message(f"Deleted {deleted_kind[:-1]} alias '{alias}'")


@click.command("rename")
@click.argument("old_alias")
@click.argument("new_alias")
@click.option("-y", "--yes", is_flag=True, help="Rename without confirmation prompt.")
def rename_alias_command(old_alias: str, new_alias: str, yes: bool):
    """Rename a host or target alias."""
    old_kind = alias_kind(old_alias)
    interruptIf_aliasMissing(old_alias, old_kind)

    if old_alias == new_alias:
        info_message("Old alias and new alias are the same. No changes applied.")
        return

    existing_new_kind = alias_kind(new_alias)
    if existing_new_kind:
        warning_message(
            f"Alias '{new_alias}' already exists as {existing_new_kind[:-1]} and will be replaced."
        )
        if not yes:
            interruptIf_notConfirmed(click.confirm("Do you want to continue?", default=False))
        delete_alias(new_alias)
    elif not yes:
        interruptIf_notConfirmed(
            click.confirm(
                f"Rename alias '{old_alias}' to '{new_alias}'?",
                default=False,
            )
        )

    renamed_kind = rename_alias(old_alias, new_alias)
    renamed_kind = interruptIf_none(renamed_kind, f"Alias '{old_alias}' was not found.")
    success_message(f"Renamed {renamed_kind[:-1]} alias '{old_alias}' -> '{new_alias}'")
