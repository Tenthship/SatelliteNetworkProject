import requests
from skyfield.api import EarthSatellite, load, Topos
from datetime import datetime, timedelta, timezone
import pandas as pd
import random
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.patches as patches
import math
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

response = requests.get("https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle")
NUM_SATELLITES = 20
lat, lon, elev_m = 32.85548069219173, -117.20414146258183, 111
observer = Topos(latitude_degrees=lat, longitude_degrees=lon, elevation_m=elev_m)
CSV_FILE_NAME = "satellite_network_dataset.csv"
ani = None

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

    plt.scatter(x, y)

    plt.xlabel("Altitude (°)")
    plt.ylabel("Latency (ms)")
    plt.title("Altitude vs Latency")


def throughput_vs_elevation(df):
    csv_file = pd.read_csv(df)
    csv_file = csv_file[csv_file["altitude"] >= 0]
    # remove NaN rows
    csv_file = csv_file[csv_file["throughput_mbps"].notna()]

    x = csv_file["altitude"]
    y = csv_file["throughput_mbps"]

    plt.scatter(x, y)

    plt.xlabel("Altitude (°)")
    plt.ylabel("Throughput (mbps)")
    plt.title("Altitude vs Throughput")

def show_all_plots(csv_file):
    fig = plt.figure(figsize=(10,8))

    plt.subplot(2,1,1)
    latency_vs_elevation(csv_file)

    plt.subplot(2,1,2)
    throughput_vs_elevation(csv_file)

    plt.tight_layout()
    return fig



def create_figure(satellites):
    global ani
    fig, ax = plt.subplots()
    ts = load.timescale()
    north = 1
    east = 1
    south = -1
    west = -1

    center = (0, 0)
    outer_horizon_radius = 1
    inner_altitude_ring1_radius = 0.667
    inner_altitude_ring2_radius = 0.333

    outer_horizon = patches.Circle(center, outer_horizon_radius, facecolor="none", edgecolor='white')
    inner_altitude_ring1 = patches.Circle(center, inner_altitude_ring1_radius, facecolor="none", edgecolor='white')
    inner_altitude_ring2 = patches.Circle(center, inner_altitude_ring2_radius, facecolor="none", edgecolor='white')

    ax.add_patch(outer_horizon)
    ax.add_patch(inner_altitude_ring1)
    ax.add_patch(inner_altitude_ring2)

    ax.set_xlim(west -.2, east +.2)
    ax.set_ylim(south -.2, north +.2)
    ax.plot([x for x in range(west, east + 1)], [y*0 for y in range(south, north + 1)], color="green")
    ax.plot([x*0 for x in range(west, east + 1)], [y for y in range(south, north + 1)], color="green")
    ax.text(0, north + 0.05, "N", color="white")
    ax.text(east + 0.05, 0, "E", color="white")
    ax.text(0, south - 0.1, "S", color="white")
    ax.text(west -0.1, 0, "W", color="white")

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_facecolor("black")
    ax.set_aspect('equal')
    ax.set_title('Matplotlib Circle Patch', color="white")


    # One scatter artist for all satellites
    dots = ax.scatter([0]*len(satellites), [0]*len(satellites), s=18)

    # Status HUD (so you can tell it's updating even if nothing is visible)
    status = ax.text(0, 0, "", color="white", ha="center", va="center")

    def update(frame):
        offsets = []
        colors = []
        visible = 0

        t_now = ts.now()

        for sat in satellites:
            topocentric = (sat - observer).at(t_now)
            alt, az, distance = topocentric.altaz()

            r = (90 - alt.degrees) / 90
            r = clamp(r, 0, 1)

            theta = math.radians(az.degrees)
            x = r * math.sin(theta)
            y = r * math.cos(theta)

            offsets.append([x, y])

            if alt.degrees >= 0:
                colors.append("yellow")
                visible += 1
            else:
                colors.append("gray")

        dots.set_offsets(offsets)
        dots.set_color(colors)
        status.set_text(f"UTC {t_now.utc_datetime().strftime('%H:%M:%S')} | visible: {visible}")

        return dots, status

    ani = FuncAnimation(fig, update, interval=200, blit=False)
    return fig


def show_dashboard(csv_file, satellites):
    root = tk.Tk()

    left = ttk.Frame(root)
    left.pack(side="left", fill="both", expand=True)

    right = ttk.Frame(root)
    right.pack(side="right", fill="both", expand=True)

    fig1 = show_all_plots(csv_file)
    fig2 = create_figure(satellites)

    canvas1 = FigureCanvasTkAgg(fig1, master=left)
    canvas1.draw()
    canvas1.get_tk_widget().pack(fill="both", expand=True)

    canvas2 = FigureCanvasTkAgg(fig2, master=right)
    canvas2.draw()
    canvas2.get_tk_widget().pack(fill="both", expand=True)

    root.ani = ani

    root.mainloop()


def main():
    write_to_file()
    satellites = parse_tle_file()
    ts = load.timescale()
    skyfield_satellites = convert_to_skyfield(satellites, ts)
    times = populate_times()
    satellite_positions = compute_satellite_positions(skyfield_satellites, times)
    df = pd.DataFrame(satellite_positions)
    df.to_csv(CSV_FILE_NAME, index=False)
    show_dashboard(CSV_FILE_NAME, skyfield_satellites)

main()
