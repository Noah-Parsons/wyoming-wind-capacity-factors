"""Wyoming wind farms: reported monthly capacity factors (EIA-923 via PUDL) against an
ERA5-based estimate at each plant (Open-Meteo's ERA5 archive, hourly, nearest grid cell).

Estimate per plant and hour:
  1. ERA5 wind speed at 100 m, shear exponent from the 10 m and 100 m speeds, extrapolated to
     the plant's hub height (EIA-860 wind table).
  2. Air density from ERA5 2 m temperature and surface pressure; speed scaled by
     (rho / 1.225)^(1/3), the IEC 61400-12 density normalisation. Wyoming plants sit at
     1,900 to 2,500 m, so this matters.
  3. A generic modern power curve (cut-in 3 m/s, rated 12 m/s, cut-out 25 m/s, cubic between).
No losses are applied: the gap between estimate and report is the quantity of interest.
"""
import json, os, sys, time, urllib.request
import numpy as np
import pandas as pd

D = "data"
START, END = "2019-01-01", "2025-12-31"


def plants():
    g = pd.read_parquet(f"{D}/out_eia__yearly_generators.parquet")
    g["report_date"] = pd.to_datetime(g.report_date)
    w = g[(g.state == "WY") & (g.energy_source_code_1 == "WND") & (g.operational_status == "existing")]
    hub = pd.read_parquet(f"{D}/core_eia860__scd_generators_wind.parquet")
    hub["report_date"] = pd.to_datetime(hub.report_date)
    hub = hub.sort_values("report_date").groupby("plant_id_eia").agg(
        hub_ft=("turbine_hub_height_feet", "last"), model=("predominant_turbine_model", "last"),
        maker=("predominant_turbine_manufacturer", "last"))
    p = w.sort_values("report_date").groupby("plant_id_eia").agg(
        name=("plant_name_eia", "last"), lat=("latitude", "last"), lon=("longitude", "last"),
        first_op=("generator_operating_date", "min")).join(hub)
    return p


def monthly_reported():
    """Monthly net generation and capacity in service, per plant."""
    g = pd.read_parquet(f"{D}/out_eia__yearly_generators.parquet")
    g["report_date"] = pd.to_datetime(g.report_date)
    g = g[(g.state == "WY") & (g.energy_source_code_1 == "WND")]
    g["op"] = pd.to_datetime(g.generator_operating_date)
    g["ret"] = pd.to_datetime(g.generator_retirement_date)
    gens = g.sort_values("report_date").groupby(["plant_id_eia", "generator_id"]).agg(
        cap=("capacity_mw", "last"), op=("op", "first"), ret=("ret", "last")).reset_index()
    gf = pd.read_parquet(f"{D}/out_eia923__monthly_generation_fuel_by_generator.parquet",
                         columns=["report_date", "plant_id_eia", "generator_id", "net_generation_mwh"])
    gf["report_date"] = pd.to_datetime(gf.report_date)
    gf = gf[gf.plant_id_eia.isin(gens.plant_id_eia) & (gf.report_date >= START) & (gf.report_date <= END)]
    rows = []
    months = pd.date_range(START, END, freq="MS")
    for pid, gg in gens.groupby("plant_id_eia"):
        for m in months:
            # count a generator only for whole months in service
            inserv = gg[(gg.op <= m) & (gg.ret.isna() | (gg.ret > m + pd.offsets.MonthEnd(0)))]
            cap = inserv.cap.sum()
            gen = gf[(gf.plant_id_eia == pid) & (gf.report_date == m) &
                     gf.generator_id.isin(inserv.generator_id)].net_generation_mwh.sum(min_count=1)
            hours = m.days_in_month * 24
            rows.append(dict(plant_id_eia=pid, month=m, cap_mw=cap, gen_mwh=gen,
                             cf_reported=gen / (cap * hours) if cap > 0 and pd.notna(gen) else np.nan))
    return pd.DataFrame(rows)


STAGED = "data"   # ERA5 extracts, one JSON file per grid cell


def era5(pid, lat, lon):
    """ERA5 hourly series for the 0.25-degree cell nearest the plant (fetched once per cell)."""
    la, lo = round(lat / 0.25) * 0.25, round(lon / 0.25) * 0.25
    path = f"{STAGED}/era5_{la:.2f}_{lo:.2f}.json"
    d = json.load(open(path))
    h = pd.DataFrame(d["hourly"])
    h["time"] = pd.to_datetime(h.time)
    h.attrs["elevation"] = d.get("elevation")
    return h


def power_curve(v):
    v = np.asarray(v, float)
    cf = np.clip((v ** 3 - 3.0 ** 3) / (12.0 ** 3 - 3.0 ** 3), 0, 1)
    cf[(v < 3.0) | (v >= 25.0)] = 0.0
    return cf


def modelled(h, hub_m):
    v10, v100 = h.wind_speed_10m.clip(lower=0.1), h.wind_speed_100m.clip(lower=0.1)
    alpha = np.clip(np.log(v100 / v10) / np.log(10.0), 0.0, 0.5)
    v_hub = v100 * (hub_m / 100.0) ** alpha
    rho = h.surface_pressure * 100.0 / (287.05 * (h.temperature_2m + 273.15))
    v_eq = v_hub * (rho / 1.225) ** (1 / 3)
    out = pd.DataFrame({"time": h.time, "cf": power_curve(v_eq), "v_hub": v_hub, "rho": rho})
    out["month"] = out.time.dt.to_period("M").dt.to_timestamp()
    return out.groupby("month").agg(cf_era5=("cf", "mean"), v_hub=("v_hub", "mean"), rho=("rho", "mean"))


if __name__ == "__main__":
    P = plants()
    rep = monthly_reported()
    res = []
    for pid, r in P.iterrows():
        h = era5(pid, r.lat, r.lon)
        hub_m = (r.hub_ft if pd.notna(r.hub_ft) else 262.0) * 0.3048
        m = modelled(h, hub_m).reset_index()
        m["plant_id_eia"] = pid
        m["elev_era5"] = h.attrs["elevation"]
        res.append(m)
        print(pid, r["name"], f"hub {hub_m:.0f} m", flush=True)
    M = pd.concat(res).merge(rep, on=["plant_id_eia", "month"], how="left")
    M = M.merge(P[["name", "model", "maker", "first_op"]], left_on="plant_id_eia", right_index=True)
    M.to_csv("monthly_comparison.csv", index=False)
    ok = M.dropna(subset=["cf_reported"])
    ok = ok[(ok.cf_reported > 0.02) & (ok.cap_mw > 0)]
    s = ok.groupby(["plant_id_eia", "name"]).agg(months=("month", "size"), cf_rep=("cf_reported", "mean"),
                                                 cf_era5=("cf_era5", "mean"), r=("cf_reported",
                                                 lambda x: np.corrcoef(x, ok.loc[x.index, "cf_era5"])[0, 1]))
    s["ratio"] = s.cf_rep / s.cf_era5
    print(s.sort_values("ratio").round(3).to_string())
    print("\nAll plants: mean reported CF %.3f, mean ERA5 estimate %.3f, ratio %.3f" %
          (ok.cf_reported.mean(), ok.cf_era5.mean(), ok.cf_reported.mean() / ok.cf_era5.mean()))
    ok["mon"] = ok.month.dt.month
    seas = ok.groupby("mon").agg(rep=("cf_reported", "mean"), era5=("cf_era5", "mean"))
    seas["ratio"] = seas.rep / seas.era5
    print(seas.round(3).to_string())
