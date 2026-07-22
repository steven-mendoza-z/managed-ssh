from mssh.commands.access_copy import access, copy, remote_run
from mssh.commands.alias_commands import (
    delete_alias_command,
    list_aliases,
    rename_alias_command,
    save,
    save_host_alias,
    save_target_alias,
    set_key_command,
    unset_key_command,
)
from mssh.commands.io_commands import export_aliases_command, import_aliases_command
from mssh.commands.key_commands import keygen_command


COMMANDS = [
    access,
    copy,
    remote_run,
    save_host_alias,
    save_target_alias,
    save,
    list_aliases,
    set_key_command,
    unset_key_command,
    delete_alias_command,
    rename_alias_command,
    export_aliases_command,
    import_aliases_command,
    keygen_command,
]
