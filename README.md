# book-mobility-program-data

Find supported travel and exchanges with destination and coverage terms.

Status: **local source pilot**, version 0.1.0. Five manually invoked official
sources now use the shared local lake runtime; there is no published remote,
scheduler, hosted API, or consumer integration.
The CLI provides a machine-readable JSON contract, validates an explicit export,
and searches synthetic examples. It never falls back from live data to fixtures.

## Users and boundary

For people and small teams discovering travel and exchange programs.
Mobility-specific support; flight prices remain book-flight-data and jobs remain job.v1.

Subcategories: travel-grant, exchange, conference-support, artist-residency, volunteer-exchange.

Domain-specific terms: `destination_country`, `travel_start`, `coverage`, `visa_support`.
`destination_country: MULTI` represents a program with multiple destinations;
it is not a country-code eligibility claim.
Each record represents one program/offer intake window. A repeat intake receives
a distinct source record ID. Cross-domain packages use `related_records` rather
than copying the same award into several products.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
book-mobility-program-data contract
book-mobility-program-data demo --open-only
book-mobility-program-data demo --query "travel-grant"
book-mobility-program-data validate src/book_mobility_program_data/demo.json
python -m unittest discover -s tests -v
```

Developer checks (the same commands CI runs in `.github/workflows/ci.yml` on
Python 3.10 and 3.12, plus a `contract`/`validate`/`demo` CLI smoke):

```bash
python -m pip install -e ".[dev]"
ruff check .
python -m pytest -q
```

All tests are offline: source adapters are exercised with inline fixtures, the
capture entry point is only checked for its fail-closed guard, and no test needs
the shared data-lake runtime or network access. `tests/test_policy.py` keeps
`sources.json`, every `source*.json` policy and the bundled schema consistent.

With dependencies already available, use `PYTHONPATH=src python3 -m book_mobility_program_data`.
`demo` uses the fixed synthetic clock 2026-09-07T00:00:00Z unless `--as-of` is
provided. `--open-only` excludes closed, unknown-deadline, expired, stale (72h
default), and future-checked records. This is an availability filter; it does
not assert personal eligibility, selection probability, or a guaranteed payout.

Contract: `src/book_mobility_program_data/schema.json` (`mobility_program.v1`).
Unknown amounts, currencies, eligibility and deadlines remain unknown. Cash,
credit, discount, in-kind benefits and access are different value kinds. Never
sum them as cash income. Queries and validation are read-only and do not persist
provided files. The `live` label requires captured lineage, but validation alone
does not verify that referenced lake objects exist or prove source truth.

## Data ownership and source policy

Owner: bookchaowalit. Public program metadata only; no applications, personal
screening answers, financial credentials, cookies, or private transcripts.
See `sources.json` and the source policy files under `src/`. DiscoverEU, Erasmus+
Youth Exchanges, COST EU-RESOLVE, Culture Moves Europe and European Solidarity
Corps pages are reviewed for public read access and captured only for bounded
program metadata. The adapters keep official eligibility, support and date
claims without collecting identity numbers or application answers. No spending,
account creation or messaging is performed.

Implemented flow: approved source pull → immutable landing bytes
and checksum → Bronze Parquet and manifest through the shared lake runtime →
versioned read-only contract → consumer pull. Each product owns its source
adapters and lake prefix. Producers never write into another app's database,
CRM, tasks, application tracker, or notification system.

## Official source pilots

Sources: [DiscoverEU rules for the autumn 2026 call](https://youth.europa.eu/discovereu/rules_en),
[Erasmus+ Youth Exchanges](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1/youth-exchanges),
[COST EU-RESOLVE conference grants](https://www.cost.eu/cost-events/euresolve-stsm-conference-grants-2026/),
[Culture Moves Europe residency hosts](https://culture.ec.europa.eu/culture-moves-europe/call-for-residency-hosts),
and [European Solidarity Corps volunteering](https://youth.europa.eu/solidarity/organisations/volunteering-projects_en).
The official page plans applications from 1 October 2026 at 12:00 Brussels time
through 15 October 2026 at 12:00 Brussels time. It describes travel passes for
seven train days in a chosen period of up to 30 days between 1 March 2027 and
31 May 2028, plus a DiscoverEU discount card. The record stays conservative:
selection is not guaranteed, visa support is unknown, and participants still
need to plan accommodation, subsistence and basic insurance. The record is `open` only from
the opening time until the deadline; captures before 1 October 2026 12:00 or at/after
15 October 2026 12:00 Brussels time report `closed`.

Run with the existing data-lake Python environment:

```bash
export SOLO_DATA_LAKE_ROOT=/path/to/solo-data-lake
PYTHONPATH=src "$SOLO_DATA_LAKE_ROOT/.venv/bin/python" -m book_mobility_program_data.capture acquire --lake "$PWD/data/lake" --state-dir "$PWD/data/control"
PYTHONPATH=src "$SOLO_DATA_LAKE_ROOT/.venv/bin/python" -m book_mobility_program_data.capture records --lake "$PWD/data/lake" --state-dir "$PWD/data/control"
```

The lane depends on the explicit local `discovery.capture_runtime` v1. Capture
is manual, rate-limited to one check per six hours, and rejects sensitive source
markers before archival. A failed latest fetch has no fixture fallback; parser
failures leave a quarantined capture reference.

## Remaining implementation gates

1. Expand field extraction and current-call monitoring without inferring selection,
   visa or employment outcomes.
2. Add live source tests, retention/access controls and runtime monitoring.
3. Connect a read-only consumer. Personal eligibility, ranking, deadlines and
   application workflow belong to consumers with separate private storage.

No runtime port is reserved. The former `opportunity.v1` is archival; `job.v1` remains a separate job-data contract.
Breaking contract changes require a new version and a consumer migration.
There is no production deployment to roll back; discard demo output or restore
the previous contract version locally. Source permission, live availability,
lake replay and real eligibility are **unverified**, not passing gates.

## Development

```bash
uv sync --frozen --all-extras && uv run mypy  # locked env (uv.lock) as CI installs it
uv run pytest -q --cov
```
