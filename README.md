# AVCE - ADA Visual Compliance Engine

A web application that analyzes YouTube educational videos for **ADA/WCAG 2.1 AA** compliance. AVCE generates WebVTT captions, detects visual content not described in audio, flags segments for human review, produces compliance scores, and now ships an interactive visual-description player plus curated educational visual-description subtitle exports.

Built as a UCLA proof-of-concept for 20 videos, designed for future SaaS scalability.

## Architecture

```
apps/
  api/          Python FastAPI backend (SQLAlchemy + SQLite)
  web/          Next.js 16 frontend (TypeScript + Tailwind CSS)
packages/
  shared/       Shared TypeScript types + VTT utilities
infra/
  scripts/      Development and deployment scripts
```

**Key design decisions:**
- `USE_MOCKS=true` env var switches all external services — full pipeline works without API keys
- In-process async job queue (`asyncio.Queue`, 2 workers) — no Celery for POC
- SQLite with `check_same_thread=False` — SQLAlchemy makes PostgreSQL migration trivial
- Caption versioning — every mutation creates a new `CaptionVersion` row
- Next.js rewrites `/api/*` to FastAPI at `localhost:8000`
- Segments now store both `risk_level` and `education_level`
- Visual descriptions are compacted, deduplicated, and curated after scanning

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- npm
- `yt-dlp` (for real YouTube caption/video download when `USE_MOCKS=false`)
- `ffmpeg` (for frame extraction when `USE_MOCKS=false`)
- `tesseract` (for OCR when `USE_MOCKS=false`)

### Setup

```bash
# Clone and enter the project
cd VTT_kudu

# Set up the Python backend
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ../..

# Set up the Next.js frontend
cd apps/web
npm install
cd ../..

# Copy environment config
cp .env.example .env
```

### Run

Start both services with the dev script:

```bash
./infra/scripts/dev.sh
```

Or start them separately:

```bash
# Terminal 1 — API (port 8000)
cd apps/api && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Web (port 3000)
cd apps/web
npm run dev
```

Verify: [http://localhost:3000/api/health](http://localhost:3000/api/health) should return `{"status":"ok"}`

### Real Integration Mode

Set `USE_MOCKS=false` in `.env` to use real integrations. At minimum you must set:

- `YOUTUBE_API_KEY` for metadata lookup
- Working `yt-dlp`, `ffmpeg`, and `tesseract` binaries

Optional AI integrations:

- OpenAI: `OPENAI_API_KEY` (+ optionally `OPENAI_MODEL`, `OPENAI_BASE_URL`)
- Azure OpenAI: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`

YouTube caption upload (`POST /videos/{id}/export/upload`) needs OAuth files:

- `YOUTUBE_OAUTH_CLIENT_SECRETS_FILE`
- `YOUTUBE_OAUTH_TOKEN_FILE`

### Run Tests

```bash
cd apps/api
source .venv/bin/activate
pytest tests/ -v
```

Tests cover VTT/SRT parsing, risk scoring, compliance calculation, caption export behavior, full pipeline integration, and pre-upload validation.

## Recent Features

- Interactive player route at `/player/[videoId]` with:
  - visual-description overlay
  - right-column description panel
  - `All`, `Educational`, and `Off` display modes
  - optional pause-on-cue playback behavior
- Education-level curation pass after description generation:
  - AI reviews `transcript_text` plus `visual_description` as a whole
  - segments receive `education_level = high | low`
  - duplicate visual descriptions are removed
  - obvious instructional graphics are promoted to `high` even if the model under-classifies them
- Curated visual-description exports:
  - all visual descriptions
  - only high education-level visual descriptions
- Adjacent duplicate visual-description cues are merged in exports and in the interactive player

## 11-Step Analysis Pipeline

When you submit a scan job, the pipeline runs these steps:

| Step | Name | What it does |
|------|------|-------------|
| 1 | `fetch_metadata` | Fetch/refresh video metadata from YouTube |
| 2 | `download_captions` | Download raw auto-generated captions |
| 3 | `enhance_captions` | Fix casing, punctuation, add non-speech tags |
| 4 | `extract_frames` | Extract frames at 10-second intervals |
| 5 | `analyze_frames_ocr` | Run OCR on each extracted frame |
| 6 | `analyze_frames_vision` | Classify visual content (text, diagrams, equations) |
| 7 | `align_segments` | Align captions with frame analyses into segments |
| 8 | `score_risk` | Assign risk levels by comparing transcript vs visual content |
| 9 | `generate_descriptions` | Generate AI audio descriptions, compact visual descriptions, and curate `education_level` |
| 10 | `compute_compliance` | Calculate weighted compliance score |
| 11 | `finalize` | Mark video as scanned |

### Visual Description Curation

After segments are aligned and descriptions are generated, AVCE runs a second pass over the segment timeline to:

- review visual descriptions together with transcript context
- assign `education_level`
- remove duplicate or near-duplicate visual descriptions
- keep presenter/studio ambience low priority
- preserve diagrams, equations, labeled graphics, charts, and other instructional visuals as high-priority educational cues

## Risk Engine

Segments are classified by comparing what's visible on screen against what's spoken in the audio:

| Risk | Reason Code | Meaning |
|------|------------|---------|
| High | `EQUATION_UNREAD` | Equation visible but not read aloud |
| High | `DIAGRAM_UNDESCRIBED` | Diagram present but not described |
| High | `CHART_UNDESCRIBED` | Chart/graph not mentioned in speech |
| Medium | `VISUAL_TEXT_UNMENTIONED` | On-screen text not covered (<30% word overlap) |
| Medium | `MODEL_UNCERTAIN` | Visual content present but low analysis confidence |
| Low | — | Content adequately described |

## Compliance Score

Weighted score with 5 components:

| Component | Weight | What it measures |
|-----------|--------|-----------------|
| Caption completeness | 30% | Captions exist, enhanced, covering all segments |
| Visual coverage | 30% | Visual elements described (low-risk segments) |
| Manual review | 20% | Segments approved/edited by human reviewer |
| Model confidence | 10% | Average frame analysis confidence |
| OCR reliability | 10% | OCR text present where visual text detected |

## API Endpoints

### Videos
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/videos` | Import video by YouTube URL |
| `GET` | `/videos` | List all videos |
| `GET` | `/videos/{id}` | Get video details |

### Jobs
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/jobs/scan` | Start scan for a single video |
| `POST` | `/jobs/batch` | Start batch scan for multiple videos |
| `GET` | `/jobs/{id}` | Get job status and progress |

### Captions
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/videos/{id}/captions/ingest` | Ingest VTT/SRT caption file |
| `POST` | `/videos/{id}/captions/enhance` | Enhance captions (casing, punctuation) |
| `GET` | `/videos/{id}/captions/latest` | Download latest VTT |
| `GET` | `/videos/{id}/captions/versions` | List all caption versions |
| `POST` | `/videos/{id}/captions/validate` | Validate VTT format |

### Segments
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/videos/{id}/segments` | List segments (filterable by `risk_level`, `review_status`) |
| `GET` | `/videos/{id}/segments/{segId}` | Get segment details |
| `PATCH` | `/videos/{id}/segments/{segId}` | Update segment (review status, text) |

### Compliance
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/videos/{id}/compliance` | Get compliance score breakdown |
| `GET` | `/videos/{id}/compliance/report` | Get full compliance report |

### Export
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/videos/{id}/export/vtt` | Download VTT file |
| `GET` | `/videos/{id}/export/vtt/original` | Download original/raw caption VTT |
| `GET` | `/videos/{id}/export/vtt/descriptions` | Download all curated visual-description subtitles |
| `GET` | `/videos/{id}/export/vtt/descriptions/high` | Download only high education-level visual-description subtitles |
| `GET` | `/videos/{id}/export/report` | Download JSON compliance report |
| `GET` | `/videos/{id}/export/validate` | Pre-upload validation check |
| `POST` | `/videos/{id}/export/upload` | Upload captions to YouTube |

## Frontend Pages

| Route | Description |
|-------|-------------|
| `/` | Dashboard — paste YouTube URL to import |
| `/videos` | Video list — status, scores, scan/batch buttons |
| `/videos/[id]` | Review page — split layout with video player, cue timeline, segment editor, and review panel |
| `/player/[id]` | Interactive player — standalone viewing mode for curated visual descriptions |

## Project Structure

```
apps/api/
  app/
    main.py              FastAPI app factory with lifespan
    config.py            Pydantic Settings (USE_MOCKS, DB URL, API keys)
    database.py          SQLAlchemy engine + session
    models/              8 SQLAlchemy models
    routers/             6 route modules
    schemas/             Pydantic request/response models
    services/            8 service classes (YouTube, caption, frame, OCR, vision, risk, compliance, description)
    pipeline/            Job queue + 11-step runner
    utils/               VTT and SRT parsers
    mocks/               Mock implementations + fixture data
  tests/                 46 tests across 4 test files
  alembic/               Database migration config

apps/web/
  src/
    app/                 Dashboard, video list, review page, interactive player
    components/
      layout/            AppShell, Header, Sidebar
      video/             VideoPlayer, VisualDescriptionOverlay, PlayerControls
      caption/           CueTimeline, CueList, CueEditor, VersionSelector
      review/            ReviewPanel, SuggestionCard, RiskBadge, ComplianceScore
      job/               BatchSubmitForm
    hooks/               useVideoPlayer, useJobPolling, useCueSync, useVisualDescriptionSync, usePauseOnCue
    lib/                 Typed API client

packages/shared/
  src/                   TypeScript types + VTT utilities
```

## Environment Variables

```bash
USE_MOCKS=true              # Toggle mock services (no API keys needed)
DATABASE_URL=sqlite:///./avce.db
SECRET_KEY=change-me

# Required only when USE_MOCKS=false
YOUTUBE_API_KEY=
YT_DLP_BINARY=yt-dlp
FFMPEG_BINARY=ffmpeg
VIDEO_CACHE_DIR=/tmp/avce_videos
FRAME_OUTPUT_DIR=/tmp/avce_frames
TESSERACT_CMD=tesseract

# Optional OpenAI
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=

# Optional Azure OpenAI
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=
AZURE_OPENAI_API_VERSION=2024-10-21

# Optional tuning
DESCRIPTION_MODEL_MAX_SEGMENTS=30
EDUCATION_MODEL_MAX_SEGMENTS=120

# Required for /export/upload in real mode
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
YOUTUBE_OAUTH_CLIENT_SECRETS_FILE=
YOUTUBE_OAUTH_TOKEN_FILE=
```

## License

UCLA POC — not yet licensed for distribution.
