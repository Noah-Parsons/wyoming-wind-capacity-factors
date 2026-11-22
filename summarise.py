"""Tables and figures from monthly_comparison.csv (written by wind.py)."""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
M = pd.read_csv("monthly_comparison.csv", parse_dates=["month"])
M["year"] = M.month.dt.year
# EIA-923 respondent frequency (fetch_frequency.py). For annual respondents (A), EIA estimates the
# monthly values by spreading the annual total over a common profile, so those plant-years are left out.
F = pd.read_csv("data/eia923_respondent_frequency.csv")
M = M.merge(F, on=["plant_id_eia", "year"], how="left")
base = M.dropna(subset=["cf_reported"]); base = base[(base.cf_reported > 0.02) & (base.cap_mw > 0)]
est = base[base.respondent_frequency == "A"]
# Check: within each year, the estimated plants share one monthly profile exactly.
spread = []
for y, g in est.groupby("year"):
    piv = g.pivot_table(index="plant_id_eia", columns=g.month.dt.month, values="gen_mwh").dropna()
    if len(piv) > 1 and piv.shape[1] == 12:
        sh = piv.div(piv.sum(axis=1), axis=0); spread.append((y, len(piv), float((sh.max() - sh.min()).max())))
print("EIA-estimated plant-years, largest spread of monthly shares within a year:", spread)
def headline(d):
    s = d.groupby("plant_id_eia").agg(r=("cf_reported", "mean"), e=("cf_era5", "mean"))
    c = d.groupby("plant_id_eia").apply(lambda g: np.corrcoef(g.cf_reported, g.cf_era5)[0, 1] if len(g) > 2 else np.nan)
    m = d.groupby(d.month.dt.month).agg(r=("cf_reported", "mean"), e=("cf_era5", "mean")); m = m.r / m.e
    return dict(plants=d.plant_id_eia.nunique(), plant_months=len(d), cf_reported=round(d.cf_reported.mean(), 3),
                cf_era5=round(d.cf_era5.mean(), 3), ratio=round(d.cf_reported.mean() / d.cf_era5.mean(), 2),
                median_plant_ratio=round((s.r / s.e).median(), 2), median_corr=round(c.median(), 2),
                ratio_dec=round(m[12], 2), ratio_jul=round(m[7], 2))
ok = base[base.respondent_frequency != "A"].copy()
pd.DataFrame([dict(months="all, including EIA estimates", **headline(base)),
              dict(months="reported monthly values only (used)", **headline(ok))]).to_csv("headline.csv", index=False)
print(pd.read_csv("headline.csv").to_string())
s = ok.groupby(["plant_id_eia", "name"]).agg(months=("month", "size"), cap_mw=("cap_mw", "max"),
        cf_reported=("cf_reported", "mean"), cf_era5=("cf_era5", "mean"), mean_v_hub=("v_hub", "mean"),
        mean_rho=("rho", "mean"))
s["corr"] = ok.groupby(["plant_id_eia", "name"]).apply(lambda g: np.corrcoef(g.cf_reported, g.cf_era5)[0, 1])
s["ratio"] = s.cf_reported / s.cf_era5
s = s.sort_values("ratio").round(3); s.to_csv("plant_summary.csv")
ok["mon"] = ok.month.dt.month
seas = ok.groupby("mon").agg(cf_reported=("cf_reported", "mean"), cf_era5=("cf_era5", "mean"))
seas["ratio"] = seas.cf_reported / seas.cf_era5; seas.round(3).to_csv("seasonal_summary.csv")
INK, MUTED, A, B = "#222222", "#888888", "#1d70b8", "#d4691a"
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.plot(seas.index, seas.cf_reported, color=A, lw=2, marker="o", ms=5, label="Reported (EIA-923, monthly values only)")
ax.plot(seas.index, seas.cf_era5, color=B, lw=2, marker="o", ms=5, label="ERA5 estimate")
ax.set_xticks(range(1, 13)); ax.set_xticklabels(list("JFMAMJJASOND"))
ax.set_ylabel("Mean capacity factor"); ax.set_ylim(0, 0.5)
ax.grid(axis="y", color="#e5e5e5"); [ax.spines[k].set_visible(False) for k in ("top", "right")]
ax.legend(frameon=False, loc="upper center")
ax.set_title("Wyoming wind farms, 2019-2025: reported against ERA5-based capacity factor", fontsize=11, color=INK, loc="left")
fig.tight_layout(); fig.savefig("fig_seasonal.png", dpi=200)
fig, ax = plt.subplots(figsize=(8, 7))
y = np.arange(len(s)); ax.barh(y, s.ratio, color=A, height=0.7)
ax.axvline(1, color=MUTED, lw=1); ax.set_yticks(y); ax.set_yticklabels(s.index.get_level_values("name"), fontsize=7.5)
ax.set_xlabel("Reported / ERA5-estimated capacity factor"); [ax.spines[k].set_visible(False) for k in ("top", "right")]
ax.set_title("Ratio by plant (1 = ERA5 estimate matches reported output)", fontsize=11, color=INK, loc="left")
fig.tight_layout(); fig.savefig("fig_plant_ratio.png", dpi=200)
print(s[["months", "cap_mw", "cf_reported", "cf_era5", "corr", "ratio"]].to_string())
print("plants", len(s), "plant-months", len(ok), "median ratio", s.ratio.median(), "corr median", s["corr"].median())
