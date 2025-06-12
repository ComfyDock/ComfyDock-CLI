import sys
import click

from .core.updates import get_package_version
from .commands.server import up, down
from .commands.config import config
from .commands.dev import dev
from .commands.update import update

@click.group()
@click.version_option(get_package_version(), prog_name="ComfyDock CLI")
def cli():
    """ComfyDock CLI - Manage ComfyUI Docker environments.
    
    A tool for running and managing ComfyUI installations with Docker.
    """
    pass

# Add all commands to the main CLI group
cli.add_command(up)
cli.add_command(down)
cli.add_command(config)
cli.add_command(dev)
cli.add_command(update)

def main(argv=None):
    """The main entry point for the CLI."""
    if argv is None:
        # No arguments passed in, default to sys.argv[1:]
        argv = sys.argv[1:]
    elif isinstance(argv, str):
        # If someone called main("up"), split it into ["up"]
        argv = argv.split()

    # Invoke Click, passing in our arguments list
    cli.main(args=argv, prog_name="comfydock")

if __name__ == "__main__":
    main()