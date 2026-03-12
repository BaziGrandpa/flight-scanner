# Flight Scanner

Simple personal flight scanning tool.

## What it does

Given:

- origin airport lists,
- destination airport lists,
- a departure date window,
- a trip-length window,

this project scans once or twice per day and summarizes the cheapest flights found for that day.

V1 is intentionally simple.
It is built for personal use, not as a general flight intelligence platform.

## V1 approach

The current V1 flow is:

1. generate route pairs,
2. run a bounded API coarse scan,
3. find the cheapest route/date seeds,
4. run a small Trip.com local verification around those seeds,
5. write the cheapest top 5 to Markdown,
6. store browser-verified results in a simple database table.

## Current V1 principles

- API-first coarse scan
- Trip.com used only for local verification
- no complex cache logic
- no historical learning system
- one simple results table
- Markdown summary is the main output

## Key docs

- `docs/project_description.md` — full project description and agreed V1 scope
- `docs/technical_design_v1.md` — detailed V1 technical design

## Planned structure

```text
flight_scanner/
├─ README.md
├─ requirements.txt
├─ config/
│  └─ default.yaml
├─ data/
│  ├─ flight_scanner.db
│  └─ reports/
│     └─ latest_summary.md
├─ docs/
│  ├─ technical_design_v1.md
│  └─ project_description.md
├─ scripts/
│  └─ run_scan.py
└─ src/
   └─ flight_scanner/
      ├─ __init__.py
      ├─ config.py
      ├─ db.py
      ├─ models.py
      ├─ query_builder.py
      ├─ scan.py
      ├─ report.py
      └─ providers/
         ├─ __init__.py
         ├─ amadeus_api.py
         └─ trip_verifier.py
```

## Manual run

From the project root, run:

```bash
python3 run_scan.py
```

Optional custom config:

```bash
python3 run_scan.py --config config/default.yaml
```

## Configuration

The project uses a two-layer config setup:

- `config/default.yaml` — safe public template
- `config/local.yaml` — local private overrides, loaded automatically when present

`local.yaml` is merged on top of the main config file, so it only needs to contain the fields you want to override.

Recommended setup for local secrets:

- keep placeholder values or environment-variable names in `default.yaml`
- keep real API credentials only in `local.yaml` or environment variables
- do not commit `config/local.yaml`

Current runtime prerequisites:

- Python dependencies installed from `requirements.txt`
- Playwright Chromium installed
- environment variables `AMADEUS_API_KEY` and `AMADEUS_API_SECRET` set

The older implementation entrypoint `scripts/run_scan.py` still works, but `run_scan.py` at the repository root is the preferred manual entry.

## Status

Implemented minimal V1 with a working Amadeus coarse scan plus Trip.com verification flow.

The current direction is a minimal V1 that prioritizes:

- cheap-ticket discovery,
- simple implementation,
- easy local operation,
- easy future iteration.
