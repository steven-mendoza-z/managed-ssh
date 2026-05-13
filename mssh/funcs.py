from typing import List, Protocol
import subprocess

from mssh.messages import info_message, warning_message


class ServerLike(Protocol):
    ssh_key: str
    user: str
    host_address: str


def remote_access_cmd(server: ServerLike) -> List[str]:
    return ["ssh", "-i", server.ssh_key, f"{server.user}@{server.host_address}"]


def run_serverside(server: ServerLike, commands: List[str]) -> None:
    command_str = " && ".join(commands)
    ssh_cmd = remote_access_cmd(server) + [command_str]
    result = subprocess.run(ssh_cmd, capture_output=True, text=True, check=False)

    if result.stdout:
        info_message(result.stdout.strip(), left="Remote")
    if result.stderr:
        warning_message(result.stderr.strip())


def run_local(commands: List[str]) -> None:
    command_str = " && ".join(commands)
    result = subprocess.run(command_str, check=True, capture_output=True, text=True, shell=True)

    if result.stdout:
        info_message(result.stdout.strip(), left="Local")
    if result.stderr:
        warning_message(result.stderr.strip())
