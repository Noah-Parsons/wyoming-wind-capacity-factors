"""Record how each Wyoming wind plant reported to EIA-923 in each year (data/eia923_respondent_frequency.csv).

EIA-923's "Respondent Frequency" column is M for plants that report monthly and A for plants
that report once a year. For A plants, EIA estimates the monthly values itself by spreading the
annual total over a common monthly profile, so their monthly generation is not a measurement.
(AM plants report annually but supply monthly values.) summarise.py leaves the A plant-years out.

Downloads the EIA-923 archive files for 2019 to 2025 (about 22 MB each) into a temporary folder.
"""
import csv, io, tempfile, urllib.request, zipfile, pathlib
import openpyxl

URL = "https://www.eia.gov/electricity/data/eia923/archive/xls/f923_{y}.zip"
rows = []
with tempfile.TemporaryDirectory() as tmp:
    for y in range(2019, 2026):
        path = pathlib.Path(tmp) / f"f923_{y}.zip"
        urllib.request.urlretrieve(URL.format(y=y), path)
        z = zipfile.ZipFile(path)
        name = next(n for n in z.namelist() if "Schedules_2_3_4_5" in n)
        wb = openpyxl.load_workbook(io.BytesIO(z.read(name)), read_only=True)
        ws = wb[next(s for s in wb.sheetnames if "Page 1 Generation and Fuel" in s)]
        hdr = None
        for r in ws.iter_rows(values_only=True):
            if hdr is None:
                if r and any(isinstance(c, str) and "Plant Id" in c for c in r if c):
                    hdr = {str(c).replace("\n", " "): i for i, c in enumerate(r) if c}
                    state = next(h for h in hdr if "State" in h)
                continue
            if r[hdr[state]] == "WY" and r[hdr["Reported Prime Mover"]] == "WT":
                rows.append((r[hdr["Plant Id"]], y, r[hdr["Respondent Frequency"]] or ""))
        print(y, name)
rows = sorted(set(rows))
with open("data/eia923_respondent_frequency.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["plant_id_eia", "year", "respondent_frequency"]); w.writerows(rows)
print(len(rows), "plant-years written")
