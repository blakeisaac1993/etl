"""Ingest Nemet (2009) data on Photovoltaic costs using the Performance Curve Database."""

import pathlib

import click

from etl.snapshot import Snapshot

CURRENT_DIR = pathlib.Path(__file__).parent
SNAPSHOT_VERSION = CURRENT_DIR.name


@click.command()
@click.option(
    "--upload/--skip-upload",
    default=True,
    type=bool,
    help="Upload dataset to Snapshot",
)
def main(upload: bool) -> None:
    # Create a new snapshot.
    snap = Snapshot(f"papers/{SNAPSHOT_VERSION}/nemet_2009.csv")

    # Download data from source and upload to S3.
    snap.create_snapshot(upload=upload)


if __name__ == "__main__":
    main()
