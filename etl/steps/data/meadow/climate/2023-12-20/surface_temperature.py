"""Load a snapshot and create a meadow dataset."""
import datetime
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import rioxarray
import xarray as xr
from owid.catalog import Table
from shapely.geometry import mapping
from structlog import get_logger

from etl.helpers import PathFinder, create_dataset

# Get paths and naming conventions for current step.
paths = PathFinder(__file__)
# Initialize logger.
log = get_logger()


def run(dest_dir: str) -> None:
    #
    # Load inputs.
    #
    # Retrieve snapshot.
    snap = paths.load_snapshot("surface_temperature.nc")

    # Load data from snapshot.
    ds = xr.open_dataset(snap.path)
    #
    # Process data.
    #
    # The latest 3 months in this dataset are made available through ERA5T, which is slightly different to ERA5. In the downloaded file, an extra dimenions ‘expver’ indicates which data is ERA5 (expver = 1) and which is ERA5T (expver = 5).
    # If a value is missing in the first dataset, it is filled with the value from the second dataset.
    ERA5_combine = ds.sel(expver=1).combine_first(ds.sel(expver=5))

    # Select the 't2m' variable from the combined dataset and assign it to 'da'.
    da = ERA5_combine["t2m"]

    # Convert the temperature values from Kelvin to Celsius by subtracting 273.15.
    da_degc = da - 273.15

    # Read the shapefile to extract country informaiton

    snap_geo = paths.load_snapshot("world_bank.zip")
    shapefile_name = "WB_countries_Admin0_10m/WB_countries_Admin0_10m.shp"

    # Check if the shapefile exists in the ZIP archive
    with zipfile.ZipFile(snap_geo.path, "r") as z:
        if shapefile_name in z.namelist():
            # Construct the correct path for Geopandas
            file_path = f"zip://{snap_geo.path}!/{shapefile_name}"

            # Read the shapefile directly from the ZIP archive
            shapefile = gpd.read_file(file_path)
            shapefile = shapefile[["geometry", "WB_NAME"]]
            # Continue processing the data as needed
        else:
            log.info(
                f"Shapefile using World Bank coordinates with '{shapefile_name}' name not found in the ZIP archive."
            )

    temp_country = {}
    small_countries = []
    for i in range(shapefile.shape[0]):
        data = shapefile[shapefile.index == i]
        da_degc.rio.write_crs("epsg:4326", inplace=True)
        try:
            clip = da_degc.rio.clip(data.geometry.apply(mapping), data.crs)
            weights = np.cos(np.deg2rad(clip.latitude))
            weights.name = "weights"
            clim_month_weighted = clip.weighted(weights)
            country_weighted_mean = clim_month_weighted.mean(dim=["longitude", "latitude"]).values
            temp_country[shapefile.iloc[i]["WB_NAME"]] = country_weighted_mean
        except:
            small_countries.append(shapefile.iloc[i]["WB_NAME"])

    log.info(f"It wasn't possible to extract data for {len(small_countries)} small countries")
    start_time = datetime.datetime(1950, 1, 1, 0, 0, 0)
    end_time = datetime.datetime(2023, 12, 1, 0, 0, 0)
    idx = pd.date_range(start_time, end_time, freq="1M")

    # df of temperatures for each country
    df_temp = pd.DataFrame(temp_country)
    df_temp["time"] = idx

    # # df of temperatures for each country
    df_temp = pd.DataFrame(temp_country)
    melted_df = df_temp.melt(id_vars=["time"], var_name="country", value_name="2m_temperature")

    # Create a new table and ensure all columns are snake-case and add relevant metadata.
    tb = Table(melted_df, short_name=paths.short_name, underscore=True)
    tb["2m_temperature"].metadata.origins = [snap.metadata.origin]
    #
    # Save outputs.
    #
    # Create a new meadow dataset with the same metadata as the snapshot.
    ds_meadow = create_dataset(dest_dir, tables=[tb], check_variables_metadata=True, default_metadata=snap.metadata)

    # Save changes in the new garden dataset.
    ds_meadow.save()
