from typing import Optional, Tuple

import click

from mssh.command_helpers import (
    _build_identity_options,
    _normalize_cli_key,
    _resolve_copy_endpoint,
    _run_command,
)
from mssh.destination.interpreter import destination_interpreter
from mssh.destination.solve import key_for_destination


@click.command()
@click.argument("destination")
@click.option(
    "--key",
    "key_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=str),
    help="SSH private key path (overrides alias key).",
)
def access(destination: str, key_path: Optional[str]):
    """SSH into destination (alias, user@alias, user@host)."""
    ssh(destination, key_path)


def ssh(destination: str, key_path: Optional[str] = None):
    solved_destination = destination_interpreter(destination)
    effective_key = _normalize_cli_key(key_path) or key_for_destination(destination)

    command = ["ssh"]
    if effective_key:
        command.extend(["-i", effective_key])
    command.append(solved_destination)
    _run_command(command)


@click.command()
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
    scp(source, target, key_path)


def scp(source: str, target: str, key_path: Optional[str] = None):
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


@click.command(
    "remote-run",
    context_settings={
        "ignore_unknown_options": True,
        "allow_extra_args": True,
    },
)
@click.argument("destination")
@click.argument("remote_args", nargs=-1, required=True, type=click.UNPROCESSED)
@click.option(
    "--key",
    "key_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=str),
    help="SSH private key path (overrides alias key).",
)
def remote_run(destination: str, remote_args: Tuple[str, ...], key_path: Optional[str]):
    """Run remote command through SSH (alias, user@alias, user@host)."""
    remote_execute(destination, remote_args, key_path)


def remote_execute(
    destination: str,
    remote_args: Tuple[str, ...],
    key_path: Optional[str] = None,
):
    solved_destination = destination_interpreter(destination)
    effective_key = _normalize_cli_key(key_path) or key_for_destination(destination)

    command = ["ssh"]
    if effective_key:
        command.extend(["-i", effective_key])

    command.append(solved_destination)
    command.extend(remote_args)
    _run_command(command)
