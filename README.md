# managed-ssh

`managed-ssh` is a command line SSH manager for saving destinations once and reusing them with short aliases.

Instead of typing the same hosts, `user@host` targets, and private key paths every time, you can save them in `mssh` and use the aliases with `ssh`, `scp`, and remote commands.

## What it helps with

- Save short names for hosts, such as `devbox -> 10.10.10.5`.
- Save full SSH targets, such as `app -> ubuntu@10.10.10.9`.
- Attach an SSH private key to an alias and let `mssh` use it automatically.
- Connect with `mssh access <alias>`.
- Run remote commands with `mssh remote-run <alias> <command>`.
- Copy files with `mssh copy`, including alias resolution on remote paths.
- Export and import aliases as JSON backups.

## Requirements

- Python 3.8 or newer.
- `ssh` and `scp` available in your system `PATH`.

## Installation

Install from PyPI:

```bash
pip install managed-ssh
```

After installing, the CLI command is:

```bash
mssh --help
```

## Quick Start

Create a host alias:

```bash
mssh save-host devbox 10.10.10.5
```

Connect to it:

```bash
mssh access devbox
```

Use a different login user without creating another alias:

```bash
mssh access ubuntu@devbox
```

Create a target alias when the user is always the same:

```bash
mssh save-target app ubuntu@10.10.10.9
mssh access app
```

Run a command remotely:

```bash
mssh remote-run app uname -a
```

Copy a local file to a saved target:

```bash
mssh copy ./local.txt app:/tmp/local.txt
```

## Alias Types

`mssh` supports two destination alias types:

| Type | Example | Use it when |
| --- | --- | --- |
| Host alias | `devbox -> 10.10.10.5` | You want to reuse the host with different users, such as `root@devbox` or `ubuntu@devbox`. |
| Target alias | `app -> ubuntu@10.10.10.9` | You usually connect with one fixed user and host. |

You can also let `mssh` detect the alias type:

```bash
mssh save devbox 10.10.10.5
mssh save app ubuntu@10.10.10.9
```

## SSH Keys

Generate a key in `~/.mssh/keys`:

```bash
mssh keygen server-a
```

Generate a key with a passphrase:

```bash
mssh keygen server-a "my-passphrase"
```

Save an alias with a specific key:

```bash
mssh save-host devbox 10.10.10.5 --key ~/.ssh/devbox.pem
mssh save-target app ubuntu@10.10.10.9 --key ~/.ssh/app.pem
```

Set, replace, or remove a key for an existing alias:

```bash
mssh set-key app ~/.ssh/app.pem
mssh unset-key app
```

Override the saved key for a single SSH connection:

```bash
mssh access app --key ~/.ssh/temporary.pem
```

Override the saved key for a single copy:

```bash
mssh copy ./local.txt app:/tmp/local.txt --key ~/.ssh/temporary.pem
```

## Copy Files

`mssh copy` wraps `scp` and resolves aliases on remote endpoints.

Copy from local to remote:

```bash
mssh copy ./local.txt app:/tmp/local.txt
```

Copy from remote to local:

```bash
mssh copy root@devbox:/tmp/file.txt ./file.txt
```

Copy between two remote destinations:

```bash
mssh copy app:/tmp/report.log root@devbox:/tmp/report.log
```

If both remote sides use aliases with keys, `mssh` passes the identity files to `scp` and uses `scp -3` so the copy is negotiated from your local machine.

## Run Remote Commands

Use `remote-run` to execute a command through SSH:

```bash
mssh remote-run devbox uname -a
mssh remote-run app ls -la /var/www
```

The destination can be an alias, `user@alias`, or `user@host`.

## Manage Aliases

List saved aliases:

```bash
mssh list
```

Rename an alias:

```bash
mssh rename old-name new-name
```

Delete an alias:

```bash
mssh delete app
```

Use `-y` to skip confirmation prompts:

```bash
mssh rename old-name new-name -y
mssh delete app -y
```

## Export and Import

Export your aliases to a JSON file:

```bash
mssh export --file backup-mssh.json
```

Import and merge while keeping existing aliases:

```bash
mssh import --file backup-mssh.json --skip-existing -y
```

Import and merge while overwriting conflicts:

```bash
mssh import --file backup-mssh.json --overwrite -y
```

Replace all local aliases with the imported file:

```bash
mssh import --file backup-mssh.json --replace -y
```

## Command Reference

| Command | Description |
| --- | --- |
| `mssh access <destination>` | Open an SSH session to an alias, `user@alias`, or `user@host`. |
| `mssh remote-run <destination> <cmd1> <cmd2> ...` | Run a remote command through SSH. |
| `mssh copy <source> <target>` | Copy files with `scp` and resolve aliases on remote paths. |
| `mssh keygen <key_name> [passphrase]` | Generate an SSH key under `~/.mssh/keys`. |
| `mssh save-host <alias> <host> [--key <path>]` | Save a host alias. |
| `mssh save-target <alias> <user@host> [--key <path>]` | Save a target alias. |
| `mssh save <alias> <value> [--key <path>]` | Save an alias and detect whether the value is a host or target. |
| `mssh list` | Show saved hosts, targets, and associated keys. |
| `mssh rename <old_alias> <new_alias> [-y]` | Rename an alias. |
| `mssh delete <alias> [-y]` | Delete an alias. |
| `mssh set-key <alias> <path>` | Set or replace the SSH key for an alias. |
| `mssh unset-key <alias>` | Remove the SSH key associated with an alias. |
| `mssh export [--file <path>]` | Export aliases to JSON. |
| `mssh import --file <path> [--replace | --overwrite | --skip-existing] [-y]` | Import aliases from JSON. |

## Where Data Is Stored

Aliases are stored locally in:

```text
~/.mssh/aliases.json
```

Generated keys are stored under:

```text
~/.mssh/keys
```

The aliases file uses this structure:

```json
{
  "hosts": {
    "devbox": "10.10.10.5"
  },
  "targets": {
    "app": "ubuntu@10.10.10.9"
  },
  "keys": {
    "app": "/home/user/.ssh/app.pem"
  }
}
```

## Notes

- A name cannot exist as both a host alias and a target alias.
- If an alias already exists, `save` asks for confirmation before overwriting it.
- Keys are used automatically when the destination or copy endpoint uses an alias.
- `--key` overrides saved alias keys for a single command.
- `managed-ssh` does not replace OpenSSH configuration; it is a small alias manager that calls your system `ssh` and `scp` commands.

## License

MIT
