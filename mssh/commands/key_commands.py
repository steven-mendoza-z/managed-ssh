import click

from mssh.keys import set_keys
from mssh.messages import success_message


@click.command("keygen")
@click.argument("key_name")
@click.argument("passphrase", required=False, default="")
def keygen_command(key_name: str, passphrase: str):
    """Generate an SSH key under ~/.mssh/keys/<key_name>."""
    key_path = set_keys(key_name, passphrase=passphrase)
    success_message(f"Key ready: {key_path}")
