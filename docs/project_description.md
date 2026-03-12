# Project Description

## What this project is

This project is a **simple personal flight scanning tool**.

The purpose of V1 is not to build a smart flight intelligence system.
It is not trying to learn route behavior, optimize budgets dynamically, or maintain a complex historical search brain.

The purpose is much simpler:

> Given airport lists, a departure date window, and a trip-length window, scan once or twice per day and summarize the cheapest tickets found that day.

This is a personal-use tool.
The main value is replacing repetitive manual searching with a small, inspectable workflow.

---

## Core user need

The core user need is:

- flexible departure airports,
- flexible destination airports,
- flexible departure dates,
- flexible trip lengths,
- daily or twice-daily scans,
- final output focused on **cheap tickets**.

The user does **not** currently need:

- advanced analytics,
- history-driven search strategy,
- automatic route learning,
- caching/freshness systems,
- purchase links,
- full booking automation.

The user mainly wants:

> Tell me what the cheapest flights are today in the search space I care about.

---

## V1 scope

V1 should do only the following:

1. read configured origin airport lists,
2. read configured destination airport lists,
3. read a departure date window,
4. read a trip-length window,
5. generate route/date query combinations,
6. run a bounded API-based coarse scan,
7. find the cheapest route/date seeds,
8. run a bounded Trip.com local verification around those seeds,
9. write the cheapest results into Markdown,
10. store result records in a simple database table.

That is enough for V1.

---

## Explicit non-goals for V1

The following are intentionally out of scope for V1:

- route scoring,
- exploration vs exploitation logic,
- adaptive query budgeting,
- cache reuse,
- quote freshness rules,
- historical cheapest tracking,
- automatic comparison against prior runs,
- purchase links,
- booking automation,
- deep analytics,
- complex multi-provider abstractions.

History may still be stored, but only as raw records for later manual comparison.
The system itself does not need to reason over historical results yet.

---

## Agreed V1 product behavior

The agreed behavior is:

### 1. Daily usage

The tool runs once or twice per day.
It does not need to be a daemon.
It does not need background services.
It can just be a script.

### 2. Search philosophy

The search is intentionally two-stage:

- **API first** for a cheap broad scan,
- **Trip.com second** for local verification and nearby date exploration.

### 3. Output philosophy

The output should be human-friendly and focused:

- Markdown summary for the cheapest top 5,
- database records for all browser-verified results.

### 4. Database philosophy

The database is only a record store.
It is not a planner, not a cache, and not a learning engine.

---

## Final agreed search strategy

The current agreed V1 search strategy is the following.

## Step 1: generate route pairs

If the config has:

- `N` origins
- `M` destinations

then generate all route pairs:

- `N × M`

Example:

- origins: `GOT`, `CPH`
- destinations: `HKG`, `PVG`, `HND`

This produces 6 route pairs:

- GOT → HKG
- GOT → PVG
- GOT → HND
- CPH → HKG
- CPH → PVG
- CPH → HND

---

## Step 2: API coarse scan

The API layer is responsible for broad cheap coverage of the search space.

### Coarse-scan principle

Do **not** search all date combinations.
Instead, do a bounded coarse scan using **fixed interval sampling**.

### Why fixed interval sampling

Fixed interval sampling was chosen over random sampling because it is:

- simpler,
- more stable,
- easier to reason about,
- easier to debug,
- good enough for V1.

### Departure date sampling

Inside the departure window, pick a small number of evenly spaced departure dates.

For V1, a practical approach is:

- 2 sampled departure dates per route pair,
- or 3 if the budget allows.

### Trip-length sampling

Inside the trip-length window, pick a small number of representative trip lengths.

For V1, a practical approach is:

- minimum trip length,
- middle trip length,
- optionally maximum trip length.

### Practical API budget

The current target is roughly:

- around **20–30 API searches** per run.

A practical default example:

- 6 route pairs,
- 2 departure samples,
- 2 trip-length samples,
- total API queries = `6 × 2 × 2 = 24`

That is the current preferred V1 starting point.

---

## Step 3: choose cheapest seeds

After the API scan:

1. normalize API results,
2. sort by price ascending,
3. choose the cheapest **1 or 2 seeds**.

A seed is:

- one origin,
- one destination,
- one departure date,
- one return date.

Example seed:

- `CPH -> HKG`
- depart `2026-05-21`
- return `2026-06-13`

---

## Step 4: Trip.com local verification

The browser layer should not brute-force the whole space.
It should only search **around the cheapest seeds**.

### Browser source

The agreed V1 browser source is:

- **Trip.com via Playwright**

This was chosen because testing showed that in the current WSL headless environment it can:

- load search pages,
- render stable filter/sidebar signals such as `Alliance`,
- render actionable result controls such as `Select`,
- extract visible prices and result cards,
- work robustly across multiple tested route/date queries.

### Important Trip.com verification experience

The current Trip.com approach was validated with two key observations:

1. The left-side filter area rendered stable markers such as `Alliance`.
2. The result area rendered actionable markers such as `Select` together with real fare text.

That means the browser flow is not based only on a visual guess.
It has two strong signals:

- the page structure has reached a stable, result-ready state,
- the visible page content shows real prices and real flight cards.

This is an important implementation detail for future sessions, because it means Trip.com verification can rely on both:

- visible page extraction,
- ready-state confirmation from stable on-page UI signals.

### Local search neighborhood

For each selected seed, generate **5 nearby date pairs**.

This is the agreed V1 rule.

If the seed is:

- depart `2026-05-21`
- return `2026-06-13`

then generate:

1. `2026-05-20` → `2026-06-13`
2. `2026-05-21` → `2026-06-13`
3. `2026-05-22` → `2026-06-13`
4. `2026-05-21` → `2026-06-12`
5. `2026-05-21` → `2026-06-14`

This 5-query pattern is the agreed V1 browser local-search strategy.

It is preferred because it is:

- simple,
- bounded,
- cheaper than a 3×3 grid,
- still strong enough to find a local minimum around the API-discovered cheap point.

---

## Step 5: browser result handling

Trip.com local verification searches may return multiple result cards per query.

The browser layer should extract as much of the following as it can:

- visible price,
- airline,
- stops,
- duration,
- route match,
- departure and arrival times,
- result count,
- cheapest visible price,
- structured raw extraction summary.

The browser layer does **not** need to produce perfectly structured airline data in V1.
It only needs to reliably extract enough information to rank results and show useful summaries.

---

## Step 6: ranking and reporting

After browser verification:

1. merge all browser results,
2. sort by lowest price,
3. take the cheapest top 5,
4. write them to Markdown.

### Markdown output policy

The Markdown report should contain only the cheapest **top 5** final results.

This is the main user-facing artifact.

It should stay concise and easy to read.

---

## Step 7: database insertion policy

The agreed policy is:

- store **all browser-verified results** in the database,
- do **not** require API coarse-scan results to be stored in V1.

This keeps the table small and focused on the higher-value, more user-relevant results.

---

## Database design

V1 keeps the database extremely simple.

### Database purpose

The database exists only to:

1. preserve scan results,
2. allow later manual comparison,
3. make future analysis possible.

It does **not** exist to:

- deduplicate quotes,
- cache queries,
- drive planning,
- learn route behavior,
- compute history-aware decisions.

---

## Single-table database design

The agreed V1 database design is one table.

### Table name

- `flight_results`

### Primary key

Use a simple auto-increment primary key:

- `id INTEGER PRIMARY KEY AUTOINCREMENT`

### Why auto-increment instead of hash

Hash-based identity is unnecessary in V1 because:

- records are append-only,
- V1 does not deduplicate,
- V1 does not upsert,
- V1 does not cache,
- V1 does not require a logical quote identity.

The simplest useful choice is an auto-increment `id`.

---

## Final agreed table fields

The agreed V1 table fields are:

- `id`
- `run_id`
- `origin`
- `destination`
- `departure_date`
- `return_date`
- `price`
- `currency`
- `airline`
- `stops`
- `duration_text`
- `fetched_at`
- `raw_json`

### Suggested SQL shape

```sql
CREATE TABLE flight_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  origin TEXT NOT NULL,
  destination TEXT NOT NULL,
  departure_date TEXT NOT NULL,
  return_date TEXT NOT NULL,
  price REAL,
  currency TEXT,
  airline TEXT,
  stops TEXT,
  duration_text TEXT,
  fetched_at TEXT NOT NULL,
  raw_json TEXT
);
```

---

## Field meaning

### `run_id`

`run_id` groups all records from the same scan execution.

This is useful even in a simple V1 because it lets the user distinguish:

- one run from another,
- morning scan vs evening scan,
- today’s results vs tomorrow’s results.

### `fetched_at`

`fetched_at` records the exact scan timestamp for that result.

This was explicitly kept because it enables later analysis such as:

- how long before departure the ticket was found,
- whether morning or evening scans were better,
- when a particular cheap ticket was observed.

### `raw_json`

`raw_json` is intentionally flexible.

It does **not** need to mean the same thing for every source.

#### For API results

It may store:

- the raw provider response,
- or a trimmed raw provider payload.

#### For browser results

It may store:

- a structured extracted summary,
- a compact normalized browser payload,
- not necessarily HTML,
- not necessarily the exact raw underlying network response.

This flexibility is intentional, because API results are usually more structured than browser results.

---

## Normalized record expectation

Both API and browser flows should aim to populate the same minimal common fields when possible.

Example V1 record shape:

```python
{
    "run_id": "2026-03-10T20:00:00+01:00",
    "origin": "GOT",
    "destination": "HKG",
    "departure_date": "2026-05-24",
    "return_date": "2026-06-19",
    "price": 758.0,
    "currency": "EUR",
    "airline": "Finnair",
    "stops": "1",
    "duration_text": "14 hr 45 min",
    "fetched_at": "2026-03-10T20:02:18+01:00",
    "raw_json": "{...}"
}
```

If a browser result cannot populate every field, that is acceptable.
The common fields should be filled when available, and the rest can remain in `raw_json`.

---

## Engineering structure

The agreed V1 engineering structure is:

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

---

## File responsibilities

### `config/default.yaml`

Stores:

- origins,
- destinations,
- departure window,
- trip-length window,
- API budget,
- number of cheapest seeds,
- browser local-query count,
- basic traveler settings.

### `scripts/run_scan.py`

The single script entry point.

Responsibilities:

- load config,
- create `run_id`,
- trigger the scan flow,
- write final report.

### `src/flight_scanner/config.py`

Load and validate config values.

### `src/flight_scanner/models.py`

Define the minimal normalized result model used inside the app.

### `src/flight_scanner/db.py`

Responsibilities:

- create the `flight_results` table,
- insert browser result rows.

### `src/flight_scanner/query_builder.py`

Responsibilities:

- generate route pairs,
- generate API coarse-scan query samples,
- generate 5-query Trip.com neighborhoods around a seed.

### `src/flight_scanner/scan.py`

Main orchestration logic.

Responsibilities:

1. generate route pairs,
2. run API coarse scan,
3. normalize and sort API results,
4. choose cheapest seeds,
5. run Trip.com local verification,
6. merge and rank browser results,
7. insert browser results into DB,
8. pass top 5 to the report writer.

### `src/flight_scanner/report.py`

Write the Markdown summary of the cheapest top 5.

### `src/flight_scanner/providers/amadeus_api.py`

Responsibilities:

- run the bounded API coarse scan,
- normalize API results into the shared minimal result shape.

### `src/flight_scanner/providers/trip_verifier.py`

Responsibilities:

- run Trip.com searches for the 5-query local neighborhoods,
- pass consent if necessary,
- extract visible flight results,
- build browser result records,
- attach flexible `raw_json` payloads.

---

## Agreed output behavior

### Markdown

Write top 5 cheapest final browser-verified results.

Each line or item should include at least:

- route,
- departure date,
- return date,
- price,
- currency,
- airline,
- stops,
- duration.

### Database

Insert all browser verification results from that run.

---

## Risks accepted in V1

The agreed V1 accepts the following risks:

### 1. Browser instability

Some Trip.com searches may fail for a particular route/date combination.
That is acceptable.

### 2. Partial field mismatch

API results are more structured than browser results.
That is acceptable.
The system should use common fields plus flexible `raw_json`.

### 3. No automatic history reasoning

The system will not compare against prior runs automatically.
That is acceptable, because the user can compare manually if needed.

---

## V1 success criteria

V1 is successful if it can:

1. run once or twice per day,
2. scan the configured route/date space with a bounded API budget,
3. find the cheapest route/date seeds,
4. run 5-query Trip.com local verification around those seeds,
5. write a useful top-5 Markdown summary,
6. store browser-verified result records in a single database table.

---

## Final summary

The final agreed V1 is intentionally simple.

- one local script,
- one config file,
- one results table,
- one bounded API coarse scan,
- one Trip.com local verifier,
- one Markdown summary.

The tool only needs to do one thing well:

> Find and summarize the cheapest flight options for the configured airport lists and travel windows on the day the scan runs.
