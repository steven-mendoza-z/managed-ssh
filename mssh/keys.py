from pathlib import Path
import subprocess
from typing import Any, List

from mssh.messages import info_message, success_message


def ssh_key_path(key_name: str) -> str:
    ssh_path = Path.home() / ".mssh" / "keys" / key_name
    return str(ssh_path)


def set_keys(name: str, passphrase: str = "") -> str:
    ssh_path = Path(ssh_key_path(name))
    ssh_path.parent.mkdir(parents=True, exist_ok=True)

    if ssh_path.exists():
        info_message(f"SSH key already exists: {ssh_path}")
    else:
        info_message(f"Generating SSH key: {ssh_path}")
        subprocess.run(
            ["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", str(ssh_path), "-N", passphrase],
            check=True,
        )
        success_message("SSH key generated.")

    return str(ssh_path)


def remote_access_cmd(server: Any) -> List[str]:
    return ["ssh", "-i", server.ssh_key, f"{server.user}@{server.host_address}"]
