# COIP: Conservation Operations Intelligence Platform

One system that spots forest loss from satellites, turns it into cases, sends field teams to act, and checks whether the action worked.

**Pilot:** Rwanda: Nyungwe, Akagera, Volcans and Gishwati-Mukura National Parks, plus a 5 km ring around each.
**Change type:** forest loss and degradation.

## The core loop

Detected → Prioritized → Assigned → Investigated → Intervened → Verifying → Closed.
After Verifying, a case that is resolved or improving closes; otherwise it goes back to Intervened. Only these transitions are allowed, and each change is logged with who, when and why.

Diagrams are in [`diagrams/`](diagrams/): ERD, case lifecycle and system architecture.

## Status

| Deliverable | State |
|---|---|
| D1 Pilot scope memo | Approved |
| D2 System design | ERD, case lifecycle and architecture diagrams drawn; transition table and priority formula write-up pending |
| D3 Protected Area Forest Change Report | Analysis scripts done; accuracy check in progress (43 of 100 points judged) |
| D4 Monitoring pipeline and case engine | Started: FastAPI app, state machine and tests; weekly run not built yet |
| D5 Web command center | Not started |
| D6 Field app | Not started (KoboToolbox form planned) |
| D7 Verification module | Not started |
| D8 Demo and handover | Not started |

## Repository layout

| Path | What it holds |
|---|---|
| `scripts/` | Numbered analysis scripts for Part 1 (run in numeric order) |
| `app/` | FastAPI case engine: models, schemas, scoring, seed data, state machine |
| `tests/` | pytest tests for the state machine and the lifecycle API |
| `diagrams/` | ERD, case lifecycle and system architecture |
| `results/` | In-progress accuracy verdicts |
| `data/` | Downloaded and generated data (git-ignored) |

## Setup

Requirements: Python 3.14, Docker, an Earth Engine project and a Global Forest Watch Data API key.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d --wait        # PostGIS database
```

Create a `.env` file (git-ignored) holding the GFW API key: [variable name used in `scripts/04_alerts.py`]. Earth Engine runs under project `coip-1410`; log in once with `earthengine authenticate`.

### Data to download into `data/`

- WDPA Rwanda shapefiles, October 2026 release, from protectedplanet.net
- Hansen Global Forest Change 2025 v1.13 tiles `00N_020E` and `00N_030E`: `lossyear` and `treecover2000`

## Run the analysis (Part 1)

```bash
python scripts/01_boundaries.py
python scripts/02_buffers.py
python scripts/03_hansen_stats.py
python scripts/04_alerts.py
python scripts/05_patches.py
python scripts/06_ranking.py
python scripts/07_hotspot_map.py
python scripts/08_accuracy_sample.py
python scripts/08b_accuracy_thumbnails.py
```

Outputs land in `data/processed/`. `04_plot_loss.py` and `plot_map.py` draw the yearly loss charts and alerts map.

## Run the case engine

```bash
python -m app.seed                  # load sample data
python -m pytest -q                 # about 2 minutes
uvicorn app.main:app --reload       # API docs at http://localhost:8000/docs
```

Database settings: [defaults in `app/config.py`].

## Starting thresholds (provisional)

- Patch cut-off 0.5 ha: keeps about 35% of alert area; to be confirmed by the accuracy check
- Ring around each park: 5 km
- Severity bands: under 1 ha Low, 1 to 5 Medium, 5 to 20 High, over 20 Critical
- Hotspot: a patch of at least 0.5 ha detected within the last 90 days

## Known limits

- Hansen loss includes plantation harvest.
- Nyungwe ring alerts and Hansen loss differ about tenfold; the cause is unverified.
- Alert confidence depends on alert age.
- The 5 km rings cross into other countries, and patches are cut at park boundaries.
- The 0.5 ha cut-off hides loss in small, fragmented forests (Akagera and Gishwati-Mukura have no kept patches).

## Data sources

- Hansen, M. C., et al. (2013). High-resolution global maps of 21st-century forest cover change. *Science, 342*(6160), 850–853.
- Global Forest Watch integrated deforestation alerts (GLAD-L, GLAD-S2, RADD).
- UNEP-WCMC & IUCN. (2026). Protected Planet: WDPA and WD-OECM. www.protectedplanet.net
- Contains modified Copernicus Sentinel data (2025–2026).
