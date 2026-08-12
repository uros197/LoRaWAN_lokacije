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
]
missing_columns = [col for col in required_columns if col not in df.columns]
if missing_columns:
    raise ValueError(
        "Missing required columns in Excel: "
        f"{missing_columns}. "
        f"Available columns: {df.columns.tolist()}"
    )


# ---------------------------------------------------------
# Geocoder
# ---------------------------------------------------------

geolocator = Nominatim(
    user_agent="belgrade_building_map_generator"
)


def geocode_address(address):
    """
    Convert an address into latitude and longitude
    using OpenStreetMap Nominatim.
    """

    # Add Belgrade and Serbia to improve geocoding
    query = f"{address}, Beograd, Srbija"

    for attempt in range(3):

        try:
            location = geolocator.geocode(query)

            if location is not None:
                return location.latitude, location.longitude

            print(f"  Address not found: {query}")
            if attempt < 2:
                print("  Retrying...")
                time.sleep(2)
                continue

        except (GeocoderTimedOut, GeocoderServiceError) as e:

            print(f"  Geocoding error: {e}")
            print("  Retrying...")

            time.sleep(2)

    return None, None


# ---------------------------------------------------------
# Geocode all locations
# ---------------------------------------------------------

coordinates = []

for index, row in df.iterrows():

    address = str(row[ADDRESS_COLUMN]).strip()

    print(
        f"\n[{index + 1}/{len(df)}] "
        f"{row[BUILDING_NAME_COLUMN]}"
    )

    print(f"  Address: {address}")

    latitude, longitude = geocode_address(address)

    coordinates.append((latitude, longitude))

    if latitude is not None:
        print(
            f"  Coordinates: "
            f"{latitude:.6f}, {longitude:.6f}"
        )

    # Nominatim asks users to avoid sending requests too quickly
    time.sleep(1)


# Add coordinates to dataframe

df["Latitude"] = [c[0] for c in coordinates]
df["Longitude"] = [c[1] for c in coordinates]

# Save the updated coordinates back to the same spreadsheet
with pd.ExcelWriter(
    EXCEL_FILE,
    engine="openpyxl",
    mode="a",
    if_sheet_exists="replace",
) as writer:
    df.to_excel(writer, sheet_name=SHEET_NAME, index=False)

print(f"Saved coordinates to {EXCEL_FILE} -> sheet '{SHEET_NAME}'")


# ---------------------------------------------------------
# Create map
# ---------------------------------------------------------

valid_coordinates = df.dropna(
    subset=["Latitude", "Longitude"]
)

if valid_coordinates.empty:
    raise RuntimeError(
        "No locations could be geocoded."
    )


# Center approximately on the locations
center_lat = valid_coordinates["Latitude"].mean()
center_lon = valid_coordinates["Longitude"].mean()


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
            row["Latitude"],
            row["Longitude"]
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
        valid_coordinates["Latitude"].min(),
        valid_coordinates["Longitude"].min()
    ],
    [
        valid_coordinates["Latitude"].max(),
        valid_coordinates["Longitude"].max()
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