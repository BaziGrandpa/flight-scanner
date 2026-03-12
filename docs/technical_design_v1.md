# Flight Scanner V1 Technical Design

## Status

V1 technical design for a deliberately simple personal flight-scanning tool.

## V1 goal

The goal of V1 is very narrow:

> Given origin airport lists, destination airport lists, a departure date window, and a trip-length window, scan once or twice per day and produce a summary of the cheapest flights found that day.

This is a personal-use tool.
V1 should optimize for:

1. simplicity,
2. usefulness,
3. low maintenance,
4. easy inspection,
5. cheap-ticket discovery.

## Product scope

V1 only needs to do the following:

1. load configured origin and destination airport lists,
2. generate route pairs,
3. generate date pairs inside the configured windows,
4. run a small API-based coarse scan,
5. identify the cheapest route/date seeds,
6. run a small Trip.com browser-based local verification around those seeds,
7. output the cheapest results in Markdown,
8. store scan results in a simple database table.

That is enough for V1.

## Explicit non-goals

V1 does **not** need:

- route scoring,
- exploration vs exploitation,
- adaptive budgeting,
- cache freshness logic,
- quote reuse logic,
- smart historical learning,
- historical cheapest-price comparison,
- purchase links,
- advanced analytics,
- complex provider abstractions.

The user can compare historical runs manually if needed.
The system does not need to act on historical comparison yet.

## Core workflow

The V1 scan flow is:

1. load config,
2. generate route pairs,
3. run API coarse scan on a bounded set of route/date combinations,
4. sort API results by lowest price,
5. choose the cheapest one or two seeds,
6. run Trip.com local verification around each seed using five nearby date pairs,
7. merge and rank browser results,
8. write top 5 to Markdown,
9. store browser results in the database.

## Main use case

Example input:

- origins: `GOT`, `CPH`
- destinations: `HKG`, `PVG`, `HND`
- departure window: `2026-05-20` to `2026-05-31`
- trip length window: `14` to `28` days
- run frequency: once or twice per day

The output should answer a single practical question:

> What are the cheapest flights I found today for the search space I care about?

## Execution model

V1 should remain script-driven and local.

Example entry point:

```bash
python scripts/run_scan.py --config config/default.yaml
```

No daemon is required.
No web service is required.
No task queue is required.

## Recommended project layout

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
│  └─ technical_design_v1.md
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

This structure is intentionally small.

## Input configuration

### Required inputs

- origin airport list
- destination airport list
- departure window start
- departure window end
- minimum trip length in days
- maximum trip length in days

### Optional inputs

- max API queries
- number of cheapest seeds to verify
- browser local queries per seed
- request currency
- target currency
- API cache TTL in hours
- cabin
- adults

## Example config shape

```yaml
origins:
  - GOT
  - CPH

destinations:
  - HKG
  - PVG
  - HND

departure_window:
  start: 2026-05-20
  end: 2026-05-31

trip_length_days:
  min: 14
  max: 28

search:
  max_api_queries: 30
  cheapest_seed_count: 2
  browser_local_queries_per_seed: 5
  currency: EUR
  cabin: economy
  adults: 1
```

## Search strategy

V1 uses a two-stage search strategy.

## Stage 1: API coarse scan

Purpose:

- cover the configured search space cheaply,
- identify which route/date regions look promising,
- avoid using browser automation for the full space.

### Step 1: generate route pairs

If the config contains:

- 2 origins,
- 3 destinations,

then V1 generates:

- `2 × 3 = 6` route pairs.

### Step 2: generate date samples

V1 should use **fixed interval sampling**, not random sampling.

Reason:

- fixed interval sampling is more stable,
- easier to reason about,
- easier to debug,
- good enough for V1.

### Departure date sampling

Inside the configured departure window, pick a small number of evenly spaced departure dates.

Example:

- start-like point,
- middle-like point,
- end-like point,

or only two points if the budget is tighter.

### Trip-length sampling

Inside the configured trip-length window, pick a small number of representative values.

For example:

- minimum trip length,
- middle trip length,
- optionally maximum trip length.

V1 should keep this small.

### Practical V1 target

A good starting point is:

- 2 sampled departure dates per route pair,
- 2 sampled trip lengths per route pair.

If there are 6 route pairs:

- `6 × 2 × 2 = 24` API queries.

This fits the target of roughly 20–30 API searches.

### API query cache

To avoid repeating the same coarse API queries multiple times in a short period, the Amadeus layer should use a database-backed query cache.

Current implementation behavior:

- cache key = `origin + destination + departure_date + return_date`
- cache freshness is controlled by a configurable TTL in hours
- cached payload stores the full normalized result list for one coarse API query
- empty API results are **not** cached
- expired cache rows are left in place for now; the newest row is checked first
- cache behavior is logged with `cache_hit`, `cache_miss`, `cache_expired`, and `cache_store`

This keeps the API budget low while preserving a simple implementation.

## Stage 2: Trip.com local verification

Purpose:

- take the cheapest route/date seeds from the API scan,
- search around those seeds more carefully,
- use Trip.com to validate nearby date combinations and extract real rendered fares.

### Seed selection

After the API scan:

1. sort API results by price,
2. choose the cheapest 1 or 2 seeds.

A seed is:

- one origin,
- one destination,
- one departure date,
- one return date.

### Local date generation

For each seed, V1 should generate **5 nearby date pairs**.

Example if the seed is:

- depart `2026-05-21`
- return `2026-06-13`

then the browser local search may query:

1. `2026-05-20` → `2026-06-13`
2. `2026-05-21` → `2026-06-13`
3. `2026-05-22` → `2026-06-13`
4. `2026-05-21` → `2026-06-12`
5. `2026-05-21` → `2026-06-14`

This 5-query neighborhood is the preferred V1 approach.
It is a good balance between search quality and simplicity.

## Why Trip.com is the preferred browser verifier

Current testing in the WSL2 headless environment showed that Trip.com can support V1 browser verification because:

1. Playwright can load Trip.com flight result pages in the current headless setup,
2. search pages load successfully,
3. the result page exposes stable visible signals for readiness detection,
4. visible result cards and prices can be extracted,
5. repeated robustness tests were successful across multiple routes.

### Important implementation note from current validation

The current Trip.com validation was established through two concrete signals:

1. the left-side filter area rendered stable markers such as `Alliance`,
2. the result area rendered actionable markers such as `Select` together with real fare text.

This matters because future implementation should remember that Trip.com verification can be supported by both:

- page-visible extraction,
- ready-state confirmation from stable visible UI signals.

In practice, this means the verifier does not need to depend on only one layer.
If the visible page is slow or partially unstable, the stable UI markers still provide a strong debugging and readiness signal.

Trip.com is the current best fit for the implemented V1.

### Challenge-page handling

Trip.com may sometimes return a verification or puzzle challenge page instead of a real result page.

Current implementation behavior:

- detect challenge text markers such as `verification test`, `Select icons in the correct order`, and `Slide to complete the puzzle`
- log the event explicitly as `verification_challenge_detected`
- stop the remaining Trip verification queries immediately for the current batch
- return the results already collected so the run can finish without further touching Trip.com in the same session

This is intentionally conservative: once challenge is detected, the verifier should stop rather than continue probing and risk increasing the site's anti-bot response.

## Result handling

V1 should treat API and browser results as sharing one small common schema, while allowing each source to keep source-specific raw payloads.

This means:

- API results may be more structured,
- browser results may be more semi-structured,
- both can still be inserted into one table as long as common fields are filled when available.

## Output policy

### Markdown output

Write the cheapest **top 5** results to Markdown.

This is the main user-facing output.

### Database output

Store **all browser verification results** in the database.

Reason:

- browser verification is already a small bounded set,
- storing all of it preserves useful context,
- database is only a record store in V1.

API coarse-scan results do not need to be stored unless later desired.
V1 can start by storing browser results only.

## Database design

V1 should keep the database extremely simple.

### Important rule

The database in V1 is:

- not a cache,
- not a planner,
- not a learning system,
- not a quote deduplication system.

It is only a scan-result record store.

## Single-table design

V1 should use one table:

- `flight_results`

### Primary key

Use a simple auto-increment primary key:

- `id INTEGER PRIMARY KEY AUTOINCREMENT`

Reason:

- V1 inserts records append-only,
- V1 does not need deduplication,
- V1 does not need hash-based identity,
- V1 does not need upsert logic.

### Suggested fields

- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `run_id` TEXT NOT NULL
- `origin` TEXT NOT NULL
- `destination` TEXT NOT NULL
- `departure_date` TEXT NOT NULL
- `return_date` TEXT NOT NULL
- `price` REAL
- `currency` TEXT
- `airline` TEXT
- `stops` TEXT
- `duration_text` TEXT
- `fetched_at` TEXT NOT NULL
- `raw_json` TEXT

## Field notes

### `run_id`

Groups all results from the same scan execution.
Even in a very simple V1, this is useful for separating:

- today morning’s run,
- today evening’s run,
- tomorrow’s run.

### `fetched_at`

This records when the result was scanned.
It is useful for later manual analysis, such as:

- how far before departure the scan happened,
- whether earlier or later scans found better prices,
- how prices changed over time.

### `raw_json`

This field should be interpreted flexibly.

For API results:

- store the provider raw result or a trimmed raw quote payload.

For browser results:

- store a structured extracted summary,
- not necessarily raw HTML,
- not necessarily the full underlying browser response.

This allows browser and API results to coexist in the same table even when their original structures differ.

## Minimal normalized result shape

V1 should normalize records into a simple Python structure like:

```python
{
    "run_id": "2026-03-10T19:00:00+01:00",
    "origin": "GOT",
    "destination": "HKG",
    "departure_date": "2026-05-24",
    "return_date": "2026-06-19",
    "price": 758.0,
    "currency": "EUR",
    "airline": "Finnair",
    "stops": "1",
    "duration_text": "14 hr 45 min",
    "fetched_at": "2026-03-10T19:02:30+01:00",
    "raw_json": "{...}"
}
```

## Ranking logic

V1 ranking should remain very simple:

1. sort browser-verified results by price,
2. choose the cheapest top 5 for Markdown,
3. store all browser results in the database.

No complex weighting is required.

## Reporting

The main user-facing output is a daily Markdown summary.

It should include:

- scan time,
- configured origins and destinations,
- departure window,
- trip-length window,
- API search count,
- browser verification count,
- cheapest top 5 results.

### Each top result should include

- route,
- departure date,
- return date,
- price,
- currency,
- airline,
- stops,
- duration,
- whether it was browser-verified.

## Module responsibilities

### `config.py`
Load and validate the simple config.

### `models.py`
Define the minimal normalized result model.

### `db.py`
Create the results table, create the API query cache table, and handle row insertion plus cache read/write helpers.

### `query_builder.py`
Generate:

- route pairs,
- coarse API date samples,
- 5-query local browser neighborhoods.

### `scan.py`
Run the full daily flow:

- generate route pairs,
- run API coarse scan,
- choose cheapest seeds,
- run Trip.com local verification,
- sort final results,
- insert browser results,
- call report generation.

### `report.py`
Write the top-5 Markdown summary.

### `providers/amadeus_api.py`
Run the coarse API scan and use the database-backed query cache before calling the remote API.

### `providers/trip_verifier.py`
Run the 5-query Trip.com local verification for each selected seed, detect challenge pages, and stop the remaining Trip queries early when challenge is triggered.

## Recommended implementation order

1. finalize config shape,
2. implement route/date sampling in `query_builder.py`,
3. implement API coarse scan,
4. implement cheapest-seed selection,
5. implement Trip.com 5-query local verifier,
6. implement Markdown summary,
7. implement single-table result insertion.

## Risks

### 1. Browser instability

Some Trip.com searches may fail for particular route/date combinations.
This is acceptable in V1 as long as the verifier usually works and failures are inspectable.

### 2. Frontend changes

Trip.com DOM or rendered text patterns may change.
This is acceptable for a personal V1 tool and can be fixed when needed.

### 3. Partial field availability

API results may provide richer structured data than browser results.
That is acceptable as long as common fields can be filled and source-specific detail is retained in `raw_json`.

## V1 success criteria

V1 is successful if it can:

1. run once or twice per day,
2. scan the configured space with a bounded API budget,
3. identify cheap seeds,
4. verify nearby date combinations in Trip.com,
5. produce a useful top-5 summary,
6. store browser results in a simple database table.

## Summary

V1 should be intentionally simple.

- one local script,
- one simple config,
- one simple result table,
- one API coarse scan,
- one Trip.com local verifier,
- one Markdown summary.

The system only needs to do one thing well:

> Find and summarize the cheapest flight options for the configured airport lists and travel windows on the day the scan runs.
