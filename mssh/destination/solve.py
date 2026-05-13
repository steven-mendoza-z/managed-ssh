import json
from pathlib import Path
from typing import Dict, Optional


ALIASES_DIR = Path.home() / ".mssh"
ALIASES_FILE = ALIASES_DIR / "aliases.json"
HOSTS_KEY = "hosts"
TARGETS_KEY = "targets"
KEYS_KEY = "keys"


def _default_aliases() -> Dict[str, Dict[str, str]]:
    return {
        HOSTS_KEY: {},
        TARGETS_KEY: {},
        KEYS_KEY: {},
    }


def _normalize_key_path(key_path: str) -> str:
    path = Path(key_path).expanduser()
    if not path.exists() or not path.is_file():
        raise ValueError(f"SSH key file does not exist: {path}")
    return str(path.resolve())


def _normalize_aliases(raw: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    if not isinstance(raw, dict):
        raise ValueError("Invalid aliases structure: expected JSON object.")

    hosts = raw.get(HOSTS_KEY, {})
    targets = raw.get(TARGETS_KEY, {})
    keys = raw.get(KEYS_KEY, {})
    if not isinstance(hosts, dict) or not isinstance(targets, dict) or not isinstance(keys, dict):
        raise ValueError(
            "Invalid aliases structure: 'hosts', 'targets', and 'keys' must be objects."
        )

    normalized = {
        HOSTS_KEY: {str(k): str(v) for k, v in hosts.items()},
        TARGETS_KEY: {str(k): str(v) for k, v in targets.items()},
        KEYS_KEY: {str(k): str(v) for k, v in keys.items()},
    }

    duplicated_aliases = set(normalized[HOSTS_KEY]).intersection(normalized[TARGETS_KEY])
    if duplicated_aliases:
        duplicates = ", ".join(sorted(duplicated_aliases))
        raise ValueError(
            "Invalid aliases structure: alias names are duplicated across "
            f"'hosts' and 'targets': {duplicates}"
        )

    existing_aliases = set(normalized[HOSTS_KEY]).union(normalized[TARGETS_KEY])
    orphan_keys = set(normalized[KEYS_KEY]).difference(existing_aliases)
    if orphan_keys:
        aliases = ", ".join(sorted(orphan_keys))
        raise ValueError(
            "Invalid aliases structure: keys reference unknown aliases: "
            f"{aliases}"
        )

    return normalized


def _ensure_storage() -> None:
    ALIASES_DIR.mkdir(parents=True, exist_ok=True)
    if not ALIASES_FILE.exists():
        ALIASES_FILE.write_text(json.dumps(_default_aliases(), indent=2), encoding="utf-8")


def load_aliases() -> Dict[str, Dict[str, str]]:
    _ensure_storage()
    try:
        raw = json.loads(ALIASES_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid aliases file: {ALIASES_FILE}") from exc

    return _normalize_aliases(raw)


def _write_aliases(data: Dict[str, Dict[str, str]]) -> None:
    _ensure_storage()
    normalized = _normalize_aliases(data)
    ALIASES_FILE.write_text(json.dumps(normalized, indent=2, sort_keys=True), encoding="utf-8")


def aliases_file_path() -> str:
    return str(ALIASES_FILE)


def load_aliases_from_file(file_path: str) -> Dict[str, Dict[str, str]]:
    path = Path(file_path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid aliases file: {path}") from exc
    return _normalize_aliases(raw)


def export_aliases(file_path: str) -> str:
    aliases = load_aliases()
    path = Path(file_path)
    if path.parent and str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(aliases, indent=2, sort_keys=True), encoding="utf-8")
    return str(path)


def replace_aliases(aliases: Dict[str, Dict[str, str]]) -> None:
    _write_aliases(aliases)


def is_target(value: str) -> bool:
    if "@" not in value:
        return False
    user, host = value.split("@", 1)
    return bool(user and host)


def is_host(value: str) -> bool:
    return bool(value and "@" not in value)


def alias_kind(alias: str) -> Optional[str]:
    aliases = load_aliases()
    if alias in aliases[TARGETS_KEY]:
        return TARGETS_KEY
    if alias in aliases[HOSTS_KEY]:
        return HOSTS_KEY
    return None


def save_host(alias: str, host: str, key_path: Optional[str] = None) -> None:
    aliases = load_aliases()
    aliases[HOSTS_KEY][alias] = host
    if key_path is not None:
        aliases[KEYS_KEY][alias] = _normalize_key_path(key_path)
    _write_aliases(aliases)


def save_target(alias: str, target: str, key_path: Optional[str] = None) -> None:
    aliases = load_aliases()
    aliases[TARGETS_KEY][alias] = target
    if key_path is not None:
        aliases[KEYS_KEY][alias] = _normalize_key_path(key_path)
    _write_aliases(aliases)


def set_alias_key(alias: str, key_path: str) -> str:
    aliases = load_aliases()
    if alias not in aliases[HOSTS_KEY] and alias not in aliases[TARGETS_KEY]:
        raise ValueError(f"Alias '{alias}' was not found.")
    normalized = _normalize_key_path(key_path)
    aliases[KEYS_KEY][alias] = normalized
    _write_aliases(aliases)
    return normalized


def unset_alias_key(alias: str) -> bool:
    aliases = load_aliases()
    if alias in aliases[KEYS_KEY]:
        del aliases[KEYS_KEY][alias]
        _write_aliases(aliases)
        return True
    return False


def get_alias_key(alias: str) -> Optional[str]:
    aliases = load_aliases()
    return aliases[KEYS_KEY].get(alias)


def _alias_from_destination_token(destination: str) -> Optional[str]:
    aliases = load_aliases()
    if "@" in destination:
        _, host_or_alias = destination.split("@", 1)
        if host_or_alias in aliases[HOSTS_KEY]:
            return host_or_alias
        return None

    if destination in aliases[TARGETS_KEY]:
        return destination

    if destination in aliases[HOSTS_KEY]:
        return destination

    return None


def key_for_destination(destination: str) -> Optional[str]:
    alias = _alias_from_destination_token(destination)
    if not alias:
        return None
    return get_alias_key(alias)


def delete_alias(alias: str) -> Optional[str]:
    aliases = load_aliases()

    if alias in aliases[HOSTS_KEY]:
        del aliases[HOSTS_KEY][alias]
        aliases[KEYS_KEY].pop(alias, None)
        _write_aliases(aliases)
        return HOSTS_KEY

    if alias in aliases[TARGETS_KEY]:
        del aliases[TARGETS_KEY][alias]
        aliases[KEYS_KEY].pop(alias, None)
        _write_aliases(aliases)
        return TARGETS_KEY

    return None


def rename_alias(old_alias: str, new_alias: str) -> Optional[str]:
    aliases = load_aliases()

    if old_alias in aliases[HOSTS_KEY]:
        aliases[HOSTS_KEY][new_alias] = aliases[HOSTS_KEY].pop(old_alias)
        if old_alias in aliases[KEYS_KEY]:
            aliases[KEYS_KEY][new_alias] = aliases[KEYS_KEY].pop(old_alias)
        _write_aliases(aliases)
        return HOSTS_KEY

    if old_alias in aliases[TARGETS_KEY]:
        aliases[TARGETS_KEY][new_alias] = aliases[TARGETS_KEY].pop(old_alias)
        if old_alias in aliases[KEYS_KEY]:
            aliases[KEYS_KEY][new_alias] = aliases[KEYS_KEY].pop(old_alias)
        _write_aliases(aliases)
        return TARGETS_KEY

    return None


def solve_host(host: str) -> str:
    aliases = load_aliases()
    return aliases[HOSTS_KEY].get(host, host)


def solve_target(target: str) -> str:
    aliases = load_aliases()
    return aliases[TARGETS_KEY].get(target, target)


def list_hosts() -> Dict[str, str]:
    aliases = load_aliases()
    return dict(sorted(aliases[HOSTS_KEY].items(), key=lambda item: item[0]))


def list_targets() -> Dict[str, str]:
    aliases = load_aliases()
    return dict(sorted(aliases[TARGETS_KEY].items(), key=lambda item: item[0]))


def list_keys() -> Dict[str, str]:
    aliases = load_aliases()
    return dict(sorted(aliases[KEYS_KEY].items(), key=lambda item: item[0]))
