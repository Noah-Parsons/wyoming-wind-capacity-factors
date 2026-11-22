"""Tables and figures from monthly_comparison.csv (written by wind.py)."""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
M = pd.read_csv("monthly_comparison.csv", parse_dates=["month"])
ok = M.dropna(subset=["cf_reported"]); ok = ok[(ok.cf_reported > 0.02) & (ok.cap_mw > 0)]
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
ax.plot(seas.index, seas.cf_reported, color=A, lw=2, marker="o", ms=5, label="Reported (EIA-923)")
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
