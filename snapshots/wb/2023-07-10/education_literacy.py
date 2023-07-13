"""Script to create a snapshot of dataset 'World Bank Education Statistics: Learning Outcomes (2018)'."""

from pathlib import Path

import click

from etl.snapshot import Snapshot

# Version for current snapshot dataset.
SNAPSHOT_VERSION = Path(__file__).parent.name


@click.command()
@click.option(
    "--upload/--skip-upload",
    default=True,
    type=bool,
    help="Upload dataset to Snapshot",
)
@click.option("--path-to-file", prompt=True, type=str, help="Path to local data file.")
def main(path_to_file: str, upload: bool) -> None:
    """
    Instructions:
    1. Visit the following URL:  https://databank.worldbank.org/reports.aspx?source=Education%20Statistics#
    2. Select the following indicators:
        'Youth literacy rate, population 15-24 years, adjusted gender parity index (GPIA)'
        'Youth literacy rate, population 15-24 years, both sexes (%)'
        'Youth literacy rate, population 15-24 years, female (%)'
        'Youth literacy rate, population 15-24 years, male (%)'
        'Adult literacy rate, population 15+ years, male (%)'
        'Adult literacy rate, population 15+ years, female (%)'
        'Adult literacy rate, population 15+ years, both sexes (%)'
        'Adult literacy rate, population 15+ years, adjusted gender parity index (GPIA)'
        'Elderly literacy rate, population 65+ years, male (%)'
        'Elderly literacy rate, population 65+ years, female (%)'
        'Elderly literacy rate, population 65+ years, both sexes (%)'
        'Elderly literacy rate, population 65+ years, adjusted gender parity index (GPIA)'
        'Literacy rate, population 25-64 years, female (%)'
        'Literacy rate, population 25-64 years, male (%)'
        'Literacy rate, population 25-64 years, adjusted gender parity index (GPIA)'
        'Literacy rate, population 25-64 years, both sexes (%)']
    3. In the top right corner, click on the "Download" button.
    4. Choose the "CSV" format and initiate the download.

    Note: Ensure that the downloaded dataset contains the desired PISA scores and associated information.
    """
    # Create a new snapshot.
    snap = Snapshot(f"wb/{SNAPSHOT_VERSION}/education_literacy.csv")

    # Ensure destination folder exists.
    snap.path.parent.mkdir(exist_ok=True, parents=True)

    # Copy local data file to snapshots data folder.
    snap.path.write_bytes(Path(path_to_file).read_bytes())

    # Add file to DVC and upload to S3.
    snap.dvc_add(upload=upload)


if __name__ == "__main__":
    main()
