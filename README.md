# Wyoming wind capacity factors

Noah Parsons. Results as of 21 November 2026.

## Question

How well does a standard reanalysis-based estimate (ERA5) reproduce the output that Wyoming's wind farms actually report, and where and when does it fail?

Reanalysis estimates of wind output are widely used for planning studies and grid models in places with few measurements. Wyoming has high, ridge-top sites in complex terrain and a strong seasonal cycle, which are exactly the conditions under which a 0.25-degree reanalysis is least reliable.

## Data

- **Reported output:** monthly net generation per generator from EIA-923, and capacity, operating and retirement dates from EIA-860, both through the PUDL data release (Catalyst Cooperative, CC-BY-4.0). A generator counts towards a month's capacity only if it was in service for the whole month.
- **Hub heights and turbine models:** the EIA-860 wind table (PUDL `core_eia860__scd_generators_wind`).
- **Weather:** ERA5 hourly wind speed at 10 m and 100 m, 2 m temperature and surface pressure, from the Open-Meteo ERA5 archive, for the 0.25-degree cell nearest each plant. The data run from January 2019 to December 2025.

## Method (`wind.py`)

1. Extrapolate the 100 m wind speed to each plant's hub height, using the shear exponent from the 10 m and 100 m speeds (clipped to 0 to 0.5).
2. Correct for air density, using the IEC 61400-12 normalisation, (ρ/1.225)^(1/3). The plants sit at 1,900 to 2,500 m, where the air is about 20% thinner than at sea level.
3. Pass the result through a generic power curve: cut-in 3 m/s, rated 12 m/s, cut-out 25 m/s, cubic in between.
4. Apply no losses. The gap between the estimate and the reported output is the quantity being measured.

Plant-months with a reported capacity factor below 2% are left out, since they mostly reflect commissioning or outages. That leaves 34 plants and 1,945 plant-months.

## Results

| | Reported | ERA5 estimate | Ratio |
|---|---|---|---|
| All plant-months | 0.321 | 0.235 | 1.37 |
| Median plant ratio | | | 1.23 |

- **ERA5 underestimates Wyoming's wind output, and by far the most in summer.** In December the estimate is within 5% of reported output. In July it is less than half: a ratio of 2.31, falling from 1.05 in December (`seasonal_summary.csv`, `fig_seasonal.png`).
- **The shortfall is largest at the ridge-top sites.** The worst ratios are at Foote Creek Rim (3.0), Corriedale (2.5), Foote Creek I (2.5), and Roundhouse and Roundhouse II (2.4) (`plant_summary.csv`, `fig_plant_ratio.png`). Foote Creek and Roundhouse sit on the high ridges west of Laramie and Cheyenne, terrain the 0.25-degree grid smooths away.
- **ERA5 gets the timing right even where it gets the level wrong.** The median correlation between reported and estimated monthly capacity factor is 0.82. A plant-by-plant, month-by-month scaling factor would therefore recover most of the gap, and this table supplies one.
- **A few plants sit well below the estimate, which points to their reported data, not to ERA5.** Casper Wind Farm reports a mean capacity factor of 9.3% (ratio 0.41), and Foote Creek III and Rock Creek have only 13 and 4 usable months. These are worth checking against EIA's raw filings before anything is concluded.

## Limits

- **The power curve is generic and no losses are applied,** so the absolute ratio is not an accuracy figure for ERA5 itself. The seasonal and site-to-site pattern, however, does not depend on that choice.
- **The nearest grid cell is used, without interpolation or elevation correction.**
- **This is a known effect.** Reanalysis wind is known to be biased low in complex terrain, and services such as Renewables.ninja apply correction factors for it. What this adds is a Wyoming, plant-by-plant and month-by-month quantification against reported output.

## Reproducing

1. Put these PUDL tables (Catalyst Cooperative data release, CC-BY-4.0) in `data/`: `out_eia__yearly_generators.parquet`, `out_eia923__monthly_generation_fuel_by_generator.parquet` and `core_eia860__scd_generators_wind.parquet`. They are not included because of their size.
2. The ERA5 extracts used for the results are in `data/`. `python fetch_era5.py` downloads them again.
3. Run:

```
python wind.py        # monthly_comparison.csv
python summarise.py   # plant and seasonal summaries, figures
```

Python packages: numpy, pandas, pyarrow, matplotlib.

## Sources and licences

- **EIA-860 and EIA-923,** via the PUDL data release, Catalyst Cooperative (CC-BY-4.0).
- **ERA5 hourly reanalysis** (Hersbach et al., Copernicus Climate Change Service), through the Open-Meteo historical archive (CC-BY-4.0). The extracts in `data/` contain modified Copernicus Climate Change Service information.

## Files

| File | Contents |
|---|---|
| `fetch_era5.py` | Downloads the ERA5 extracts |
| `wind.py` | Builds the monthly comparison |
| `summarise.py` | Tables and figures |
| `monthly_comparison.csv` | Every plant-month: reported and estimated capacity factor, hub-height speed, air density |
| `plant_summary.csv`, `seasonal_summary.csv` | The summaries above |
| `fig_seasonal.png`, `fig_plant_ratio.png` | Figures |

