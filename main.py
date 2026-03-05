import requests
from skyfield.api import EarthSatellite, load, Topos
from datetime import datetime, timedelta, timezone
import pandas as pd
import random
import numpy as np
import matplotlib.pyplot as plt

response = requests.get("https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle")
NUM_SATELLITES = 20
lat, lon, elev_m = 32.85548069219173, -117.20414146258183, 111
observer = Topos(latitude_degrees=lat, longitude_degrees=lon, elevation_m=elev_m)
CSV_FILE_NAME = "satellite_network_dataset.csv"

# Function to write TLE data to file
def write_to_file():
    if response.status_code == 200:
        lines = response.text.splitlines()

        with open("TLE.txt", "w") as f:
            for line in lines:
                if line.strip():
                    f.write(line + "\n")
    else:
        print(f"Error: {response.status_code}")

# Function to parse tle_file to create satellite objects in array
def parse_tle_file():
    satellites = []
    with open("TLE.txt", "r") as f:
        lines = f.readlines()
        for i in range(0, NUM_SATELLITES*3, 3):
            satellite = {
                "name": lines[i].strip(),
                "tle_1": lines[i + 1].strip(),
                "tle_2": lines[i + 2].strip(),
            }
            satellites.append(satellite)
        
    return satellites

# Function to convert satellite objects to skyfield satllite objects
def convert_to_skyfield(satellites, ts):
    skyfield_satellites = []
    for s in satellites:
        earth_satellite = EarthSatellite(s["tle_1"], s["tle_2"], s["name"], ts)
        skyfield_satellites.append(earth_satellite)
    return skyfield_satellites

# Function to populate time array
def populate_times():
    ts = load.timescale()
    start_time_utc = datetime.now(timezone.utc)
    minutes_in_day = 1440
    return ts.from_datetimes([start_time_utc + timedelta(minutes=i) for i in range(minutes_in_day)])

# Function to clamp a value
def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))

def compute_satellite_positions(skyfield_satellites, times):
    satellite_positions = []
    for t in times:
        dt = t.utc_datetime()
        for s in skyfield_satellites:
            topocentric = (s - observer).at(t)
            alt, az, distance = topocentric.altaz()
            latency = None
            throughput_mbps = 0
            packet_loss_percent = 100
            latency_noise = random.randint(-5, 5)
            throughput_mbps_noise = random.randint(-20, 20)
            packet_loss_percent_noise = random.randint(-1, 1)
            if alt.degrees >= 0:
                latency =  25 + (90 - alt.degrees) * 0.5 + latency_noise
                throughput_mbps = 200 - (90 - alt.degrees) * 1.5 + throughput_mbps_noise
                throughput_mbps = clamp(throughput_mbps, 0, 1000)
                packet_loss_percent = max(0, (20 - alt.degrees) * 0.3 + packet_loss_percent_noise)
                
            satellite_position = {
                "time": dt,
                "name": s.name,
                "altitude": alt.degrees,
                "azimuth": az.degrees,
                "latency": latency,
                "throughput_mbps": throughput_mbps,
                "packet_loss_percent": packet_loss_percent
            }
            satellite_positions.append(satellite_position)

    return satellite_positions

def latency_vs_elevation(df):
    csv_file = pd.read_csv(df)
    x = csv_file["altitude"]
    y = csv_file["latency"]
    
    plt_x = np.array(x)
    plt_y = np.array(y)
    plt.scatter(plt_x, plt_y)
    
    plt.xlabel("Altitude (°)")
    plt.ylabel("Latency (ms)")
    plt.title("Altitude vs Latency")
    
    plt.show()

def throughput_vs_elevation(df):
    csv_file = pd.read_csv(df)
    x = csv_file["altitude"]
    y = csv_file["throughput_mbps"]
    
    plt_x = np.array(x)
    plt_y = np.array(y)
    plt.scatter(plt_x, plt_y)
    
    plt.xlabel("Altitude (°)")
    plt.ylabel("Throughput (mbps)")
    plt.title("Altitude vs Throughput")
    
    plt.show()


def main():
    write_to_file()
    satellites = parse_tle_file()
    ts = load.timescale()
    skyfield_satellites = convert_to_skyfield(satellites, ts)
    times = populate_times()
    satellite_positions = compute_satellite_positions(skyfield_satellites, times)
    df = pd.DataFrame(satellite_positions)
    df.to_csv(CSV_FILE_NAME, index=False)
    latency_vs_elevation(CSV_FILE_NAME)
    throughput_vs_elevation(CSV_FILE_NAME)

main()





