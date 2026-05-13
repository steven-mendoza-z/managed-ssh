# managed-ssh

`managed-ssh` (`mssh`) is a CLI to manage SSH aliases per user and use them with `ssh` and `scp`.

It stores aliases in:

- `~/.mssh/aliases.json`

Alias types:

- `hosts`: `alias -> host`
- `targets`: `alias -> user@host`
- `keys`: `alias -> /path/to/private_key` (optional)

## Install

From this repository:

```bash
pip install -e .
```

After install, the command is:

```bash
mssh --help
```

## Quick Start

Generate a key in `~/.mssh/keys`:

```bash
mssh keygen server-a
```

Generate a key with passphrase (as argument):

```bash
mssh keygen server-a "my-passphrase"
```

Save aliases:

```bash
mssh save-host devbox 10.10.10.5
mssh save-target app ubuntu@10.10.10.9
```

Or autodetect:

```bash
mssh save devbox 10.10.10.5
mssh save app ubuntu@10.10.10.9
```

Save with a specific key:

```bash
mssh save-host devbox 10.10.10.5 --key ~/.ssh/devbox.pem
mssh save-target app ubuntu@10.10.10.9 --key ~/.ssh/app.pem
```

List aliases:

```bash
mssh list
```

Access via SSH:

```bash
mssh access devbox
mssh access root@devbox
mssh access ubuntu@10.10.10.9
```

Override key for a single access:

```bash
mssh access devbox --key ~/.ssh/temporary.pem
```

Copy with SCP (alias resolution on both remote sides):

```bash
mssh copy ./local.txt app:/tmp/local.txt
mssh copy root@devbox:/tmp/file.txt ./file.txt
```

Override key for a single copy:

```bash
mssh copy ./local.txt app:/tmp/local.txt --key ~/.ssh/temporary.pem
```

## Commands

- `mssh access <destination>`
- `mssh keygen <key_name> [passphrase]`
- `mssh copy <source> <target>`
- `mssh save-host <alias> <host> [--key <path>]`
- `mssh save-target <alias> <user@host> [--key <path>]`
- `mssh save <alias> <value> [--key <path>]`
- `mssh list`
- `mssh delete <alias> [-y]`
- `mssh rename <old_alias> <new_alias> [-y]`
- `mssh set-key <alias> <path>`
- `mssh unset-key <alias>`
- `mssh export [--file <path>]`
- `mssh import --file <path> [--replace | --overwrite | --skip-existing] [-y]`

## Export / Import

Export current aliases:

```bash
mssh export --file backup-mssh.json
```

Import and merge, skipping existing:

```bash
mssh import --file backup-mssh.json --skip-existing -y
```

Import and merge, overwriting existing:

```bash
mssh import --file backup-mssh.json --overwrite -y
```

Import replacing everything:

```bash
mssh import --file backup-mssh.json --replace -y
```

## Notes

- If an alias already exists, `save` asks for confirmation before overwrite.
- A name cannot exist at the same time as both `host` and `target` alias.
- Keys are used automatically when destination/source uses an alias.
- In `copy`, if both sides are remote aliases, `mssh` can pass both identity files.
- `mssh` requires `ssh` and `scp` binaries available in your system `PATH`.
