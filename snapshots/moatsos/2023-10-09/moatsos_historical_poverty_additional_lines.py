"""Script to create a snapshot of dataset."""

from pathlib import Path

import click

from etl.snapshot import Snapshot

# Version for current snapshot dataset.
SNAPSHOT_VERSION = Path(__file__).parent.name


@click.command()
@click.option("--upload/--skip-upload", default=True, type=bool, help="Upload dataset to Snapshot")
def main(upload: bool) -> None:
    # Define list of poverty lines that define the files to use
    poverty_lines = ["5", "10", "30", "oecd_countries_share", "oecd_regions_number"]
    # Create a new snapshot.
    for povline in poverty_lines:
        snap = Snapshot(f"moatsos/{SNAPSHOT_VERSION}/moatsos_historical_poverty_{povline}.csv")

        # Download data from source, add file to DVC and upload to S3.
        snap.create_snapshot(upload=upload)


if __name__ == "__main__":
    main()
