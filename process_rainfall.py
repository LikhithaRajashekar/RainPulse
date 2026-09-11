import h5py
import numpy as np
import pandas as pd
import re
from pathlib import Path

# ============================================================
# INPUT FOLDER
# Your original .h5 files stay here.
# This script ONLY READS them.
# ============================================================

folder = Path("data/01_ISRO_GSMaP")

# ============================================================
# OUTPUT FILE
# This will be created in the main RainPulse_prototype folder.
# ============================================================

output = Path("odisha_rainfall_20260728.csv")

# ============================================================
# ODISHA APPROXIMATE BOUNDING BOX
# ============================================================

LAT_MIN = 17.5
LAT_MAX = 22.8

LON_MIN = 80.0
LON_MAX = 87.5

all_data = []

# Find HDF5 files
files = sorted(folder.glob("GPMMRG_MAP_*.h5"))

print("HDF5 files found:", len(files))

if not files:
    print("ERROR: No HDF5 files found.")
    raise SystemExit


# ============================================================
# PROCESS EACH FILE
# ============================================================

for file_path in files:

    print("\nProcessing:", file_path.name)

    # Example filename:
    # GPMMRG_MAP_260728000_H_L3S_MCH_03F.h5

    match = re.search(r"GPMMRG_MAP_(\d{9})", file_path.name)

    if not match:
        print("Skipping - timestamp not found")
        continue

    time_code = match.group(1)

    # 260728000 = 2026-07-28 00:00
    timestamp = pd.to_datetime(
        time_code,
        format="%y%m%d%H%M"
    )

    # ========================================================
    # OPEN HDF5 FILE
    # ========================================================

    with h5py.File(file_path, "r") as f:

        g = f["Grid"]

        lat = np.asarray(g["Latitude"][:])
        lon = np.asarray(g["Longitude"][:])
        rain = np.asarray(g["hourlyPrecipRate"][:])

        print("Latitude shape :", lat.shape)
        print("Longitude shape:", lon.shape)
        print("Rain shape     :", rain.shape)

        # ====================================================
        # CASE 1:
        # Latitude and longitude are already point-by-point
        # ====================================================

        if lat.shape == lon.shape == rain.shape:

            mask = (
                (lat >= LAT_MIN) &
                (lat <= LAT_MAX) &
                (lon >= LON_MIN) &
                (lon <= LON_MAX) &
                np.isfinite(rain) &
                (rain != -9999.9)
            )

            df = pd.DataFrame({
                "timestamp": timestamp,
                "latitude": lat[mask],
                "longitude": lon[mask],
                "rainfall_mm_hr": rain[mask]
            })

        # ====================================================
        # CASE 2:
        # Latitude and longitude are 1-D axes
        # and rainfall is a 2-D grid
        # ====================================================

        elif lat.ndim == 1 and lon.ndim == 1 and rain.ndim == 2:

            lat_mask = (
                (lat >= LAT_MIN) &
                (lat <= LAT_MAX)
            )

            lon_mask = (
                (lon >= LON_MIN) &
                (lon <= LON_MAX)
            )

            selected_lat = lat[lat_mask]
            selected_lon = lon[lon_mask]

            selected_rain = rain[
                np.ix_(lat_mask, lon_mask)
            ]

            valid = (
                np.isfinite(selected_rain) &
                (selected_rain != -9999.9)
            )

            lat_indices, lon_indices = np.where(valid)

            df = pd.DataFrame({
                "timestamp": timestamp,
                "latitude": selected_lat[lat_indices],
                "longitude": selected_lon[lon_indices],
                "rainfall_mm_hr": selected_rain[valid]
            })

        else:

            print("WARNING: Unexpected data shapes.")
            print("No extraction performed for this file.")
            continue

        print("Odisha points extracted:", len(df))

        all_data.append(df)


# ============================================================
# COMBINE RESULTS
# ============================================================

if not all_data:

    print("\nERROR: No Odisha rainfall data was extracted.")
    raise SystemExit


result = pd.concat(
    all_data,
    ignore_index=True
)

# ============================================================
# SAVE
# ============================================================

result.to_csv(
    output,
    index=False
)

print("\n========================================")
print("SUCCESS!")
print("========================================")
print("Rows created:", len(result))
print("Output file :", output)
print("\nFirst 5 rows:")
print(result.head())