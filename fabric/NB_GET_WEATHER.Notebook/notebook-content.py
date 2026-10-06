# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "376d57d5-b180-447c-a563-86f060fc63e1",
# META       "default_lakehouse_name": "LH_DEV",
# META       "default_lakehouse_workspace_id": "125b2b62-ab60-4936-954d-2570ff4a99a5",
# META       "known_lakehouses": [
# META         {
# META           "id": "376d57d5-b180-447c-a563-86f060fc63e1"
# META         }
# META       ]
# META     }
# META   }
# META }

# MARKDOWN ********************

# ## This is dev environment

# CELL ********************

import requests
from datetime import datetime, timezone

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# ============================================================
# Environment configuration
# These values are replaced by fabric-cicd during deployment
# ============================================================

ENVIRONMENT = "dev"
LOCATION = "Brussels"
LATITUDE = 50.8503
LONGITUDE = 4.3517
API_URL = "https://api.open-meteo.com/v1/forecast"

TARGET_TABLE = "weather_data"

print("============================================================")
print(f"Environment : {ENVIRONMENT}")
print(f"Location    : {LOCATION}")
print(f"Latitude    : {LATITUDE}")
print(f"Longitude   : {LONGITUDE}")
print(f"Target table: {TARGET_TABLE}")
print("============================================================")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# ============================================================
# Call Open-Meteo API
# ============================================================

params = {
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
    "hourly": [
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m"
    ],
    "forecast_days": 1,
    "timezone": "auto"
}

print("Calling API...")

response = requests.get(
    API_URL,
    params=params,
    timeout=30
)

response.raise_for_status()

data = response.json()

print("API call successful")


# ============================================================
# Extract API data
# ============================================================

hourly = data["hourly"]

ingestion_timestamp = datetime.now(timezone.utc).isoformat()

rows = []

for i, timestamp in enumerate(hourly["time"]):

    rows.append({
        "environment": ENVIRONMENT,
        "location": LOCATION,
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timestamp": timestamp,
        "temperature_c": hourly["temperature_2m"][i],
        "relative_humidity_pct": hourly["relative_humidity_2m"][i],
        "wind_speed_kmh": hourly["wind_speed_10m"][i],
        "ingestion_timestamp": ingestion_timestamp
    })


# ============================================================
# Create Spark DataFrame
# ============================================================

df = spark.createDataFrame(rows)

print(f"Rows retrieved: {df.count()}")

display(df)


# ============================================================
# Write to Lakehouse Delta table
# ============================================================

(
    df.write
      .format("delta")
      .mode("overwrite")
      .saveAsTable(TARGET_TABLE)
)

print(f"Successfully written {len(rows)} rows to '{TARGET_TABLE}'")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# ============================================================
# Visualize temperature
# ============================================================

import matplotlib.pyplot as plt

plot_df = (
    df.select(
        "timestamp",
        "temperature_c"
    )
    .orderBy("timestamp")
    .toPandas()
)

plt.figure(figsize=(10, 5))

plt.plot(
    plot_df["timestamp"],
    plot_df["temperature_c"],
    marker="o"
)

# Fixed Y-axis
plt.ylim(-10, 40)

# Fixed X-axis: first to last forecast hour
plt.xlim(
    plot_df["timestamp"].min(),
    plot_df["timestamp"].max()
)

plt.xlabel("Time")
plt.ylabel("Temperature (°C)")
plt.title(f"Temperature forecast - {LOCATION} ({ENVIRONMENT})")

plt.grid(True)
plt.xticks(rotation=45)

plt.tight_layout()
plt.show()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
