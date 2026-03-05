Below is a **technical task breakdown** you can paste into Codex as the build plan. It’s organized as epics → tasks → acceptance criteria, with clear interfaces so Codex can implement in chunks.

(Notes for correctness: YouTube captions work through `captions.list`, `captions.download`, `captions.insert` in the YouTube Data API. ([Google for Developers][1]))

---

# Technical Task Breakdown for Codex (AVCE v0.1 – UCLA POC)

## Epic 0 — Repo, Tooling, and Dev Environment

### Task 0.1: Monorepo scaffold

* Create repo structure:

  * `/apps/web` (Next.js)
  * `/apps/api` (FastAPI or Node)
  * `/packages/shared` (types, VTT utilities)
  * `/infra` (local docker compose, scripts)
    **Acceptance**
* `pnpm dev` (or `npm run dev`) starts web + api locally with proxy.

### Task 0.2: Local secrets + config

* `.env.example` with:

  * `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REDIRECT_URI`
  * `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, `AZURE_OPENAI_DEPLOYMENT`
  * `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` (optional)
  * `DATABASE_URL` (sqlite for POC)
    **Acceptance**
* App boots with placeholder envs; validates missing secrets with friendly errors.

---

## Epic 1 — Auth + YouTube API Integration

### Task 1.1: Google OAuth for YouTube scopes

* Implement OAuth flow (server-side):

  * Required scope for captions management (YouTube Data API)
* Store refresh token securely (POC: sqlite encrypted-at-rest optional)
  **Acceptance**
* User can “Connect YouTube” and sees connected channel info.

### Task 1.2: Video discovery (POC: manual list + optional channel list)

* Endpoint: `GET /youtube/videos?mine=true` (or accept pasted URLs)
* Parse URL → extract `videoId`
* Fetch metadata (title, duration, thumbnails)
  **Acceptance**
* UI can paste 20 URLs and shows a list with metadata.

### Task 1.3: Captions inventory

* API call: `captions.list(part=snippet, videoId=...)` ([Google for Developers][1])
* Return tracks: language, track kind, status
  **Acceptance**
* UI shows whether captions exist and which languages.

### Task 1.4: Captions download

* API call: `captions.download(id=captionTrackId, tfmt=...)` ([Google for Developers][2])
* Support `tfmt=srt` and `tfmt=vtt` where available
  **Acceptance**
* Can download existing track and display parsed cues in UI.

### Task 1.5: Captions upload (WebVTT)

* API call: `captions.insert(part=snippet, videoId=..., media_body=VTT)` ([Google for Developers][3])
* Ensure we do **not** rely on deprecated `sync` parameter ([Google for Developers][3])
  **Acceptance**
* User can upload generated VTT and see new track appear in `captions.list`.

---

## Epic 2 — Data Model + Job System (POC-first, SaaS-ready)

### Task 2.1: Database schema (POC)

Tables:

* `users`
* `youtube_accounts` (tokens)
* `videos` (videoId, title, duration)
* `jobs` (status, progress, logs)
* `segments` (time_start, time_end, transcript, visual_flags, risk, suggestions)
* `caption_versions` (json_cues, vtt_text, created_at, status)
  **Acceptance**
* Migrations run; CRUD endpoints work.

### Task 2.2: Background processing (POC)

* Use simple job runner:

  * Option A: in-process queue + worker thread
  * Option B: Celery/RQ (Python) / BullMQ (Node)
* Job states: `queued/running/failed/succeeded`
  **Acceptance**
* Submitting a scan returns `jobId`; polling shows progress.

---

## Epic 3 — Caption Base Layer (Audio-First)

### Task 3.1: Ingest auto captions if present

* Prefer using `captions.download` from existing track when available. ([Google for Developers][2])
* Parse SRT/VTT into canonical `Cue[]` structure:

  * `{startMs, endMs, text}`
    **Acceptance**
* You can render cues on a timeline and play them with the video.

### Task 3.2: Caption enhancement pipeline

* Normalize:

  * punctuation/casing
  * remove artifacts
  * add non-speech tags when detectable (POC: simple heuristics)
* Optional: glossary support (physics terms)
  **Acceptance**
* “Enhanced captions” differ from raw auto captions in obvious ways (punctuation, line breaks).

### Task 3.3: VTT generator + validator

* Generate strict WebVTT:

  * header `WEBVTT`
  * timestamps `HH:MM:SS.mmm --> HH:MM:SS.mmm`
* Validate:

  * monotonic time
  * no negative durations
  * no overlaps (or auto-fix by nudging)
    **Acceptance**
* Produced `.vtt` passes basic playback in browser `<track>` (WebVTT format is standard). ([MDN Web Docs][4])

---

## Epic 4 — Visual Analysis (Frame Sampling + Vision Model)

### Task 4.1: Frame sampling strategy (POC)

* For each video:

  * sample every 2 seconds
  * plus scene-change detection (optional POC: histogram diff)
* Note: for POC, you may process by downloading a temporary video copy only for analysis (since you own rights). Keep storage ephemeral.
  **Acceptance**
* For a 10-min video, you get ~300 frames (2s interval).

### Task 4.2: OCR pass (on-screen text extraction)

* Use an OCR tool (local Tesseract or Azure Vision OCR if available)
* Extract:

  * detected text
  * bounding boxes (optional)
  * confidence
    **Acceptance**
* Math/equation text is detected at least partially on typical lecture slides.

### Task 4.3: Vision-language analysis per frame

* Use Azure OpenAI vision to classify:

  * `has_text`, `has_diagram`, `has_equation`, `has_chart`
  * `likely_essential`
  * short description suggestion
  * uncertainty score
    **Acceptance**
* For frames with visible diagrams, model returns `likely_essential=true` often.

### Task 4.4: Align frames → segments

* Map frames to nearest caption cue windows:

  * If frame timestamp ∈ [cue.start, cue.end], attach to that cue
  * Otherwise create “visual-only” microsegment (e.g., 1–2s)
    **Acceptance**
* Each cue has associated “visual evidence” metadata.

---

## Epic 5 — Risk Engine + Compliance Confidence Score

### Task 5.1: Determine “visual not described in audio”

For each segment:

* Compare:

  * transcript text (cue)
  * OCR text / vision description
* Decide:

  * `described_in_audio: yes/no/uncertain`
* Heuristics:

  * If OCR contains tokens not in transcript (equation symbols, key terms) → higher risk
  * If model uncertainty high → “uncertain”
    **Acceptance**
* System flags segments where equations appear without being read aloud.

### Task 5.2: Segment risk scoring

* `risk_level: low/med/high`
* `risk_reason_codes`: e.g.

  * `VISUAL_TEXT_UNMENTIONED`
  * `DIAGRAM_UNDESCRIBED`
  * `MODEL_UNCERTAIN`
    **Acceptance**
* UI can filter by `high risk` and show reasons.

### Task 5.3: Overall compliance confidence score (0–100)

* Weighted formula (configurable):

  * caption completeness
  * % essential visuals described
  * manual review completion
  * uncertainty penalties
    **Acceptance**
* Score changes when user resolves/approves flagged segments.

---

## Epic 6 — “Visual Description Caption” Generation

### Task 6.1: Generate suggested descriptions

For segments flagged:

* Prompt Azure OpenAI to produce:

  * short, neutral description (<= 2 lines)
  * optionally prepend `[On screen: ...]` when OCR text is primary
  * avoid hallucination: must reference OCR text or detected elements
    **Acceptance**
* Suggestions are concise and consistently formatted.

### Task 6.2: Insert suggestions into caption cue set (as draft)

* Two modes:

  1. Inline in same cue (append)
  2. New cue inserted at same timestamp
* Mark `source=ai_draft`
  **Acceptance**
* Generated VTT includes these cues but with “draft” status until reviewed.

---

## Epic 7 — Review & Correction UI (Web)

### Task 7.1: Video + timeline player

* YouTube embedded player (IFrame API)
* Caption timeline with cue list
* Jump-to-time behavior
  **Acceptance**
* Clicking a cue seeks the YouTube video.

### Task 7.2: Flag visualization

* Show markers on timeline for risk segments
* Filter toggles: `high/med/low`
  **Acceptance**
* User can quickly jump through high-risk segments.

### Task 7.3: Editable cue editor

* Inline edit caption text
* Accept/Reject AI suggestion
* Mark “adequately described”
* Save version
  **Acceptance**
* Editing updates score + generated VTT.

### Task 7.4: Diff + versioning

* Maintain versions:

  * raw auto captions
  * enhanced captions
  * reviewed captions
    **Acceptance**
* User can revert to prior version for a cue or whole track.

---

## Epic 8 — Export, Upload, and Compliance Report

### Task 8.1: Export VTT + JSON

* Download buttons for:

  * `.vtt`
  * `.json` canonical cues
    **Acceptance**
* Files download with correct names: `VIDEOID.en.reviewed.vtt`.

### Task 8.2: Upload to YouTube

* Publish to YouTube via API `captions.insert` ([Google for Developers][3])
* Store uploaded captionTrackId
  **Acceptance**
* Track appears in YouTube Studio and in `captions.list`.

### Task 8.3: Compliance report generator

* Generate report (JSON first; PDF optional later):

  * videoId, title, run date
  * flags count
  * resolved count
  * confidence score
  * limitations disclaimer (no legal guarantee)
    **Acceptance**
* Report downloadable per video and for batch.

---

## Epic 9 — Batch Processing (POC-lite)

### Task 9.1: Batch submit scan jobs

* UI: select multiple videos → “Scan”
* Backend: create one job per video or a parent job with children
  **Acceptance**
* Can run scans across 20 videos and see progress per video.

### Task 9.2: Cost controls + throttling (POC)

* Rate limit vision calls
* Cache frame analyses by hash
  **Acceptance**
* Re-running scan doesn’t re-charge for identical frames.

---

## Epic 10 — Quality Gates (Compliance-Oriented)

### Task 10.1: Automated tests

* Unit tests:

  * SRT/VTT parsing
  * VTT generation
  * risk scoring determinism
* Integration tests:

  * YouTube API mocked
    **Acceptance**
* CI passes with >70% coverage on parsing/core logic.

### Task 10.2: “Red flag” QA checklist

* Ensure:

  * no empty cues
  * all times within duration
  * no overlapping cues (or documented)
  * risky segments not silently ignored
    **Acceptance**
* A “pre-upload validation” screen blocks upload if critical issues remain.

---

# Implementation Notes for Codex (practical constraints)

* Use YouTube Data API caption endpoints: list/download/insert. ([Google for Developers][1])
* Don’t rely on deprecated `sync` param; keep timing under your control. ([Google for Developers][3])
* ADA Title II web rule compliance timelines being discussed widely have April 24, 2026 for 50k+ entities; your tool is explicitly a “reduce risk + document diligence” compliance workflow. ([ADA.gov][5])

---


