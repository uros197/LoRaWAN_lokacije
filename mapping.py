import time
import pandas as pd
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

EXCEL_FILE = "Troškovi.xlsx"
SHEET_NAME = "Spisak lokacija"
OUTPUT_FILE = "mapa_lokacija.html"

# Names of columns in the Excel file
BUILDING_NUMBER_COLUMN = "R. Br."
BUILDING_NAME_COLUMN = "Zgrada"
ADDRESS_COLUMN = "Adresa"
LATITUDE_COLUMN = "Latitude"
LONGITUDE_COLUMN = "Longitude"

# If your columns D-F have specific names, put them here.
# Otherwise, set these to None.
MEASUREMENT_COLUMNS = [
    "Kalorimetar",
    "El. brojilo",
    "Vodomer"
]


# ---------------------------------------------------------
# Read Excel
# ---------------------------------------------------------

print(f"Reading {EXCEL_FILE}...")

df = pd.read_excel(
    EXCEL_FILE,
    sheet_name=SHEET_NAME
)

df.columns = (
    df.columns
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)
)

print(f"Found {len(df)} locations.")
print("\nColumns found in Excel:")
print(df.columns.tolist())

required_columns = [
    BUILDING_NUMBER_COLUMN,
    BUILDING_NAME_COLUMN,
    ADDRESS_COLUMN,
    LATITUDE_COLUMN,
    LONGITUDE_COLUMN,
]
missing_columns = [col for col in required_columns if col not in df.columns]
if missing_columns:
    raise ValueError(
        "Missing required columns in Excel: "
        f"{missing_columns}. "
        f"Available columns: {df.columns.tolist()}"
    )


# ---------------------------------------------------------
# Use existing coordinates from spreadsheet
# ---------------------------------------------------------

print("Using Latitude and Longitude values already present in the spreadsheet.")

# Keep the original data as-is; Folium uses the stored coordinates.
valid_coordinates = df.dropna(subset=[LATITUDE_COLUMN, LONGITUDE_COLUMN]).copy()

if valid_coordinates.empty:
    raise RuntimeError(
        "No valid Latitude/Longitude values found in the spreadsheet."
    )

# Optional: ensure numeric types for mapping
valid_coordinates[LATITUDE_COLUMN] = pd.to_numeric(
    valid_coordinates[LATITUDE_COLUMN], errors="coerce"
)
valid_coordinates[LONGITUDE_COLUMN] = pd.to_numeric(
    valid_coordinates[LONGITUDE_COLUMN], errors="coerce"
)
valid_coordinates = valid_coordinates.dropna(subset=[LATITUDE_COLUMN, LONGITUDE_COLUMN])

if valid_coordinates.empty:
    raise RuntimeError(
        "No valid Latitude/Longitude values found in the spreadsheet."
    )


# ---------------------------------------------------------
# Create map
# ---------------------------------------------------------

# Center approximately on the locations
center_lat = valid_coordinates[LATITUDE_COLUMN].mean()
center_lon = valid_coordinates[LONGITUDE_COLUMN].mean()


mapa = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=11,
    tiles="OpenStreetMap"
)


# ---------------------------------------------------------
# Add markers
# ---------------------------------------------------------

for _, row in valid_coordinates.iterrows():

    # -----------------------------------------------------
    # Basic information
    # -----------------------------------------------------

    building_number = row[BUILDING_NUMBER_COLUMN]
    building_name = row[BUILDING_NAME_COLUMN]
    address = row[ADDRESS_COLUMN]

    # -----------------------------------------------------
    # Popup
    # -----------------------------------------------------

    popup_html = f"""
    <div style="width:300px">

        <h4>{building_name}</h4>

        <b>Broj objekta:</b>
        {building_number}
        <br>

        <b>Adresa:</b>
        {address}
        <br><br>

    """

    # Add measurement information if columns exist
    for column in MEASUREMENT_COLUMNS:

        if column in df.columns:

            value = row[column]

            popup_html += f"""
            <b>{column}:</b> {value}
            <br>
            """

    popup_html += """
    </div>
    """

    # -----------------------------------------------------
    # Marker
    # -----------------------------------------------------

    folium.Marker(
        location=[
            row[LATITUDE_COLUMN],
            row[LONGITUDE_COLUMN]
        ],
        popup=folium.Popup(
            popup_html,
            max_width=350
        ),
        tooltip=building_name
    ).add_to(mapa)


# ---------------------------------------------------------
# Automatically fit map to all buildings
# ---------------------------------------------------------

bounds = [
    [
        valid_coordinates[LATITUDE_COLUMN].min(),
        valid_coordinates[LONGITUDE_COLUMN].min()
    ],
    [
        valid_coordinates[LATITUDE_COLUMN].max(),
        valid_coordinates[LONGITUDE_COLUMN].max()
    ]
]

mapa.fit_bounds(bounds)


# ---------------------------------------------------------
# Save map
# ---------------------------------------------------------

mapa.save(OUTPUT_FILE)

print("\n---------------------------------------")
print("Map successfully generated!")
print("---------------------------------------")

print(f"Output: {OUTPUT_FILE}")

print(
    f"Locations on map: "
    f"{len(valid_coordinates)}/{len(df)}"
)

print("---------------------------------------")