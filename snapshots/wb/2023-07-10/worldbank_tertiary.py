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
        'Gross enrolment ratio for tertiary education, female (%)'
        'Gross enrolment ratio for tertiary education, male (%)'
        'Gross enrolment ratio for tertiary education, both sexes (%)'
        'Gross enrolment ratio for tertiary education, adjusted gender parity index (GPIA)'
        'Outbound mobility ratio, all regions, both sexes (%)'
        'Gross graduation ratio from first degree programmes (ISCED 6 and 7) in tertiary education, male (%)'
        'Gross graduation ratio from first degree programmes (ISCED 6 and 7) in tertiary education, female (%)'
        'Gross graduation ratio from first degree programmes (ISCED 6 and 7) in tertiary education, both sexes (%)'
        'Gross graduation ratio from first degree programmes (ISCED 6 and 7) in tertiary education, gender parity index (GPI)'
    3. In the top right corner, click on the "Download" button.
    4. Choose the "CSV" format and initiate the download.

    Note: Ensure that the downloaded dataset contains the desired PISA scores and associated information.
    """
    # Create a new snapshot.
    snap = Snapshot(f"worldbank_education/{SNAPSHOT_VERSION}/worldbank_tertiary.csv")

    # Ensure destination folder exists.
    snap.path.parent.mkdir(exist_ok=True, parents=True)

    # Copy local data file to snapshots data folder.
    snap.path.write_bytes(Path(path_to_file).read_bytes())

    # Add file to DVC and upload to S3.
    snap.dvc_add(upload=upload)


if __name__ == "__main__":
    main()