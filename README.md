# Smart Qora

AI livestock **gate monitoring** — counts animals in and out of a barn/paddock from a camera feed, in real time.

Camera frames → Ultralytics YOLOE detection → BoT-SORT tracking → line-crossing counter →
PostgreSQL + incremental rollups → FastAPI + WebSocket → React dashboard, with an annotated
MJPEG preview and aggregated Telegram alerts. The UI is fully translated into **Русский,
Қазақша, English, Türkçe**.

> **License:** AGPL-3.0-only. See [Licensing](#licensing).

---

## Deployment model

One self-contained box **per site**: `docker compose up` brings up PostgreSQL, the GPU
backend, and an nginx frontend that also reverse-proxies `/api` and `/ws` — so everything is
same-origin and there is no CORS to configure. Remote access is expected to run over
[Tailscale](#remote-access); the app still requires a login.

```
                         ┌─────────────── one box per site ───────────────┐
  camera (RTSP/USB/file) │  backend ── vision worker (GPU)                │
                         │     │       ├─ WorkerSupervisor (crash/backoff)│
                         │     │       ├─ LineCrossingCounter             │
                         │     │       ├─ FrameBus ─► GET /api/stream/*   │
                         │     │       └─ RunningTotals ─► daily_statistics│
                         │     │                                          │
                         │  FastAPI ── JWT auth (admin / viewer)          │
                         │     │       ├─ REST /api/*                     │
                         │     │       └─ WebSocket /ws/live (live totals)│
                         │     ▼                                          │
                         │  Postgres ◄── Alembic migrations               │
                         │     ▲                                          │
                         │  nginx ── serves the SPA + proxies /api & /ws  │
                         └───────────────────────────────────────────────┘
                                        ▲  Tailscale (network only)
                                   browser (login)  ·  Telegram (alerts + bot)
```

The line-crossing geometry is an independent reimplementation of the idea in
[NitinCVOrbit's YOLO11 line-crossing example](https://github.com/NitinCVOrbit).

---

## Quick start

Requirements: Docker + Compose, an NVIDIA GPU with the
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).

```bash
git clone https://github.com/RuslanHinizov/Smart-Qora.git && cd Smart-Qora
docker compose up -d --build
```

Open `http://localhost:5173`, sign in `admin` / `admin`. That's it — a fine-tuned
sheep model (`models/best.pt`) and a demo clip (`videos/crop_23.11.23-12.MP4`) are
bundled, so the dashboard starts counting on the looping demo video with nothing
else to download. `alembic upgrade head` runs automatically on every backend start.

*No NVIDIA GPU?* Delete the `deploy:` block in `docker-compose.yml` — it then runs
on CPU (much slower, but the UI and counting still work).

Health probes: `GET /api/health` (liveness), `GET /api/ready` (503 until DB + worker are up).

## Deploy a real site box

For an actual gate, override the demo defaults:

```bash
cp .env.example .env                 # set strong POSTGRES_PASSWORD / SECRET_KEY / ADMIN_PASSWORD
cp backend/.env.example backend/.env # then set VIDEO_SOURCE=rtsp://… + COUNT_LINE_* (or use the Cameras page)
docker compose up -d --build
```

Without `.env` the compose file falls back to insecure demo secrets (`admin` / `admin`,
a fixed `SECRET_KEY`) — fine for a laptop, **not** for anything reachable by others.

---

## Configuration

Two layers:

**1. `backend/.env` — box-level, needs a restart.** Model path, device/CUDA, tracker,
image size, and the *bootstrap* values for the first camera row. Secrets live only here;
they are git-ignored and never returned by the API.

| key | notes |
|---|---|
| `MODEL_PATH` | `models/best.pt` |
| `DEVICE` / `REQUIRE_CUDA` / `HALF_PRECISION` | `DEVICE=0` = first GPU; `REQUIRE_CUDA=true` fails startup instead of falling back to CPU |
| `CONFIDENCE` / `IOU` / `IMG_SIZE` / `FRAME_SKIP` / `TRACKER` | inference tuning; `IMG_SIZE` must be a multiple of 32 |
| `ALLOWED_CLASSES` | `sheep,cattle,goat,horse`; names are matched case-insensitively via synonyms (`cow` ↔ `cattle`). Empty = every class in the model |
| `VIDEO_SOURCE` + `COUNT_LINE_*` + `INSIDE_DIRECTION` | **seed only** — used once to create the first camera; edit later in the UI |
| `VIDEO_LOOP` | replay a video-*file* source forever so the live preview keeps running (ignored for RTSP/webcam) |
| `SECRET_KEY` / `ADMIN_USERNAME` / `ADMIN_PASSWORD` / `ACCESS_TOKEN_TTL_HOURS` | JWT auth; the admin is seeded on first boot only |

**2. The Settings and Cameras pages — runtime, no restart.** Default language, Telegram
token/chat, detection defaults, and per-camera source + counting line + inside-direction +
thresholds. Editing the active camera automatically restarts the vision worker. Point a
camera's `source` at `rtsp://user:pass@host/stream` for a real feed; credentials are masked
(`rtsp://user:***@host`) in every API response.

### Counting line

A track's smoothed center must cross fully from one side of the line to the other (a small
dead zone; touching the line never counts) in the direction that makes it "enter". Set it
visually by clicking on the live snapshot in the camera editor, or as pixel coordinates.

---

## Remote access

Install Tailscale on the box and on each operator's device. Reach the dashboard at
`http://<box-tailscale-name>:5173`. Tailscale handles the network; the app still enforces
login and admin/viewer roles.

## Backup & restore

```bash
docker compose exec db pg_dump -U postgres smart_qora > backup.sql          # backup
docker compose exec -T db psql -U postgres smart_qora < backup.sql          # restore
```

The Postgres data lives in the `postgres_data` volume; snapshot it for a full copy.

## Upgrade

```bash
git pull
docker compose up -d --build     # runs alembic upgrade head on start
```

Roll back by checking out the previous tag and, if a migration ran, `alembic downgrade`
to the prior revision. See `docs/RELEASE.md`.

## Single-process note

The vision worker and the WebSocket broadcaster are in-process, so the backend runs with
**one uvicorn worker** (`WEB_CONCURRENCY=1`, asserted at startup). One box serves one site;
horizontal scaling would need Redis pub/sub and per-camera worker supervision — out of
scope for the per-site model.

---

## Local development

Python 3.12+, Node 22+.

```bash
# backend — same-origin: the vite dev server proxies /api and /ws to :8000
pip install -r backend/requirements.txt
cd backend && alembic upgrade head && uvicorn app.main:app --reload

# frontend
cd frontend && npm ci && npm run dev
```

For GPU inference install the CUDA build of torch first (see `backend/requirements-gpu.txt`).

## Tests & CI

```bash
cd backend && ruff check . && pytest -q
cd frontend && npm run lint && npm run typecheck && npm run test && npm run build
```

GitHub Actions runs all of the above plus an Alembic-on-Postgres migration check and Docker
image builds on every push and PR.

---

## Model training

The bundled `models/best.pt` is a **YOLOv8s fine-tune** on the Zenodo sheep gate-crossing
set — on those clips it counts 158/158 (the YOLOE baseline it replaced managed 111/158).
The reproducible fine-tuning + counting-accuracy pipeline, the eval numbers, and how to
retrain on your own footage are in [`training/README.md`](training/README.md) and
[`models/README.md`](models/README.md). Only `sheep` is trained; cattle/goat/horse stay at
the base model's level until you add data for them.

## Licensing

Smart Qora is **AGPL-3.0-only** (`LICENSE`). Ultralytics — which this project links at
runtime for detection and tracking — is itself AGPL-3.0, so keeping Smart Qora under the
same license is the compliant path; there is no Ultralytics Enterprise license involved.

Because the app is served over a network, AGPL Section 13 applies: an operator running a
modified version must offer its source to its users. This repository is that offer. Full
third-party attributions are in `NOTICE`.
