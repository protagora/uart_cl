"""Command‑line interface using *click* (acts like Program.cs Main)."""
from __future__ import annotations
import asyncio, sys, pathlib
import click
from .serial_io import UartSession, available_ports
from .error_db import ErrorDB
from .nor import patch_file, scan_info

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(package_name="uartcl")
def cli():
    """UART‑CL console – serial, NOR and error‑DB utilities."""

# -----------------------------------------------------------------------------
# UART commands
# -----------------------------------------------------------------------------
@cli.command()
@click.option("--port", "port_", help="Serial port path or COM name.")
@click.option("--baud", default=115200, show_default=True, help="Baud rate.")
def uart(port_: str | None, baud: int):
    """Open an interactive UART session (Ctrl‑C to quit)."""
    if port_ is None:
        ports = available_ports()
        if not ports:
            click.echo("No serial ports detected.", err=True)
            sys.exit(1)
        click.echo("Available ports:")
        for idx, (dev, desc) in enumerate(ports, 1):
            click.echo(f"  [{idx}] {dev} – {desc}")
        choice = click.prompt("Select", type=click.IntRange(1, len(ports)))
        port_ = ports[choice - 1][0]

    async def _run():
        click.secho(f"Opening {port_} @ {baud}…", fg="cyan")
        async with UartSession(port_, baud) as sess:
            reader = asyncio.create_task(_printer(sess))
            try:
                while True:
                    cmd = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                    if not cmd:
                        break
                    sess.write(cmd.rstrip("\n"))
            finally:
                reader.cancel()

    async def _printer(sess: UartSession):
        async for line in sess.read_lines():
            click.echo(line)

    asyncio.run(_run())

# -----------------------------------------------------------------------------
# NOR commands
# -----------------------------------------------------------------------------
@cli.group()
def nor():
    """PS5 NOR helpers."""


@nor.command("info")
@click.argument("dump", type=click.Path(exists=True))
def nor_info(dump: str):
    """Show edition / basic metadata of a NOR *DUMP*."""
    for k, v in scan_info(dump).items():
        click.echo(f"{k:<10}: {v}")


@nor.command("patch")
@click.argument("src", type=click.Path(exists=True))
@click.argument("dst", type=click.Path())
@click.option("--digital/--disc", default=True, help="Target console edition flag.")
def nor_patch(src: str, dst: str, digital: bool):
    """Patch *SRC* dump and write to *DST*."""
    patch_file(src, dst, digital=digital)
    click.secho("Patched dump written to " + dst, fg="green")

# -----------------------------------------------------------------------------
# Error‑DB commands
# -----------------------------------------------------------------------------
@cli.group()
def db():
    """Manage offline error‑code database."""


@db.command("download")
def db_download():
    """Fetch the latest JSON database to local cache."""
    asyncio.run(ErrorDB.ensure_latest())
    click.secho("Database updated", fg="green")
