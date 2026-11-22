"""Download the ERA5 hourly series used by wind.py from the Open-Meteo historical archive,
one file per 0.25-degree cell nearest each Wyoming wind farm (data/era5_<lat>_<lon>.json).
The extracts used for the published results are already in data/; this re-creates them."""
import json, os, time, urllib.request
from wind import plants, START, END

URL = ("https://archive-api.open-meteo.com/v1/archive?latitude={la}&longitude={lo}"
       "&start_date={s}&end_date={e}&hourly=wind_speed_10m,wind_speed_100m,temperature_2m,"
       "surface_pressure&wind_speed_unit=ms&timezone=GMT&models=era5")
os.makedirs("data", exist_ok=True)
for pid, r in plants().iterrows():
    la, lo = round(r.lat / 0.25) * 0.25, round(r.lon / 0.25) * 0.25
    path = f"data/era5_{la:.2f}_{lo:.2f}.json"
    if os.path.exists(path):
        continue
    for attempt in range(6):
        try:
            with urllib.request.urlopen(URL.format(la=la, lo=lo, s=START, e=END), timeout=120) as f:
                open(path, "w").write(f.read().decode())
            break
        except Exception as err:            # the API rate-limits bursts (HTTP 429)
            print("retry", pid, err); time.sleep(30 * (attempt + 1))
    time.sleep(5)
