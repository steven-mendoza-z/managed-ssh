import click

from mssh.command_helpers import _validate_import_options
from mssh.destination.solve import (
    HOSTS_KEY,
    KEYS_KEY,
    TARGETS_KEY,
    aliases_file_path,
    export_aliases,
    load_aliases,
    load_aliases_from_file,
    replace_aliases,
)
from mssh.messages import info_message, success_message, warning_message
from mssh.verifiers import interruptIf_notConfirmed, interruptIf_valueError


@click.command("export")
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
    exported = interruptIf_valueError(export_aliases, file_path)

    info_message(f"Aliases source: {aliases_file_path()}")
    success_message(f"Aliases exported to: {exported}")


@click.command("import")
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

    imported = interruptIf_valueError(load_aliases_from_file, file_path)

    if replace:
        if not yes:
            interruptIf_notConfirmed(
                click.confirm(
                    "Replace all local aliases with imported aliases?",
                    default=False,
                )
            )
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
