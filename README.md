# WURKIO Stock Scanner

A small, dependency-free Python scanner engine. It reads a market snapshot from
CSV, applies configurable filters, scores the matches, and
ranks the strongest stocks.

## Included filters

- Price range
- Relative volume (RVOL)
- Current volume
- 20-day average volume
- ATR as a percentage of price (ATR%)
- 5-day average volume
- Latest percent change
- Volume percent change versus 20-day average
- Float range

Every threshold is configurable. Set a value to `null` in JSON to disable that
filter. Minimum and maximum values can be used for price, ATR%, and float.

## Run it

Python 3.10+ is recommended.

Launch the desktop GUI:

```powershell
python main.py
```

The v0.3 GUI supports editable filter controls, enabled/disabled filters,
preset loading and saving, CSV selection, scanning, CSV/JSON export, ranked
results, pass-reason details, remembered user settings, and theme switching.
Dark 2026 and Light 2026 are the primary modern themes. The
Default, Windows 98, True 98, and Windows 2000s definitions are registered; the
dedicated classic workstation layout is planned for a later milestone.

Scanner usability features include sortable result headings, ticker search,
configurable visible columns, positive/negative result coloring, quick presets,
scan timing/count diagnostics, empty states, required-filter evaluations,
non-blocking score targets, and a six-category WURKIO Score breakdown.

The v0.4 market-intelligence foundation adds VWAP and SMA position, gap and
premarket activity, market cap, short float, 52-week/day-range position, dollar
volume, float rotation, and distance from the intraday high/low. These context
metrics are informational and optionally filterable; they do not change the
100-point score. Optional scan snapshots are stored locally in SQLite at
`data/wurkio_history.db` for later score validation and performance research.

The v0.5 outcome-tracking foundation defines a vendor-neutral market-data
provider interface and restart-safe SQLite jobs for 5-minute, 15-minute,
30-minute, 1-hour, and market-close observations. It calculates return, MFE,
MAE, high-after-scan, and low-after-scan. A deterministic simulated provider is
included strictly for tests; it is never presented as live market data. The GUI
History tab shows saved runs and outcome completion progress.

```powershell
python -m wurkio_scanner --input data/sample_stocks.csv --config scanner_config.json
```

JSON output is also available for a future GUI or API:

```powershell
python -m wurkio_scanner --input data/sample_stocks.csv --config scanner_config.json --format json
```

Run the tests:

```powershell
python -m unittest discover -s tests -v
```

## CSV format

The input must contain these columns:

```text
symbol,price,current_volume,avg_volume_5d,avg_volume_20d,atr_14d,latest_percent_change,float_shares
```

RVOL is calculated as `current_volume / avg_volume_5d`, matching the 5-day RVOL
shown in the supplied scanner settings. ATR% is calculated as
`atr_14d / price * 100`. Volume percent change uses the 20-day average:
`(current_volume - avg_volume_20d) / avg_volume_20d * 100`.

Edit `scanner_config.json` to change thresholds without touching Python code.
The `data/sample_stocks.csv` file is synthetic and exists only to demonstrate
the engine; it is not live market data.

## Screenshot presets

The `presets` directory contains all seven supplied configurations. Duplicate
filters were consolidated into the same engine fields. Run any preset by passing
its file to `--config`, for example:

```powershell
python -m wurkio_scanner --input data/sample_stocks.csv --config presets/early_swings_v0.6.json
```

Blank 5-day average-volume fields in the screenshots are stored as `null` and
therefore disabled. Values such as `500` and `1000` were preserved exactly as
shown; if those were intended to mean thousands, change them to `500000` and
`1000000` respectively.
