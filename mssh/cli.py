import click

from mssh import __version__
from mssh.commands import COMMANDS


@click.group()
@click.version_option(__version__, prog_name="mssh")
def cli():
    """Managed-SSH CLI."""


for command in COMMANDS:
    cli.add_command(command)


def main():
    cli.main(standalone_mode=True, color=True)


if __name__ == "__main__":
    main()
