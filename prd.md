---

# 📄 PRODUCT REQUIREMENTS DOCUMENT (PRD)

## Product Name

**ADA Visual Compliance Engine (AVCE)**
Version 0.1 – UCLA Proof of Concept

---

# 1. Executive Summary

The ADA Visual Compliance Engine (AVCE) is a web-based application designed to ensure YouTube-hosted educational videos comply with **ADA Title II (DOJ 2024 Final Rule)** requirements aligning with **WCAG 2.1 AA** standards.

The system will:

* Analyze audio and visual content of YouTube videos
* Generate compliant WebVTT (.vtt) caption files
* Detect visually essential content not described in audio
* Flag segments requiring human review
* Produce a compliance confidence score
* Provide a review and correction interface
* Allow upload of final caption tracks via YouTube API

Initial scope:

* 20 YouTube videos owned by the creator (UCLA course)
* Proof of concept
* Designed for eventual SaaS scalability

---

# 2. Compliance Target

## Regulatory Standard

* ADA Title II (DOJ 2024 Final Rule)
* WCAG 2.1 AA

## Required WCAG Media Criteria

The system must address:

### 2.1 Captions (WCAG 1.2.2)

* Accurate transcription of spoken dialogue
* Include non-speech sounds relevant to understanding
* Proper timing alignment

### 2.2 Audio Description (WCAG 1.2.3)

* Identify visual information essential to understanding
* Generate descriptive caption inserts when missing
* Flag high-risk segments for manual review

---

# 3. Goals

### Primary Goal

Produce legally defensible caption files that satisfy ADA requirements for prerecorded educational media.

### Secondary Goals

* Provide measurable compliance confidence score
* Reduce manual accessibility workload
* Establish architecture scalable to SaaS

---

# 4. Non-Goals (V1)

* Real-time live captioning
* Multi-language support
* External YouTube channel support
* Automated legal liability guarantee

---

# 5. User Roles

## 5.1 Instructor (Primary User)

* Inputs YouTube URL
* Runs compliance scan
* Reviews flagged segments
* Approves final captions
* Uploads captions to YouTube

## 5.2 Future Admin (SaaS expansion)

* Batch process videos
* Access compliance dashboard

---

# 6. System Architecture (Web-Based)

## 6.1 Frontend

* React (Next.js recommended)
* Video player with synchronized transcript timeline
* Segment flag visualization
* Compliance score display
* Editable caption interface
* Download .vtt button
* Upload-to-YouTube button

## 6.2 Backend

* Node.js or Python (FastAPI preferred)
* Azure-hosted
* REST API

## 6.3 Core Components

### 6.3.1 YouTube Integration

* YouTube Data API v3
* Pull:

  * Video metadata
  * Existing caption tracks
* Upload:

  * Final VTT caption track

---

# 7. Processing Pipeline

## Step 1 – Video Input

User provides:

* YouTube URL

System:

* Verifies ownership via OAuth
* Fetches metadata
* Checks existing captions

---

## Step 2 – Audio Caption Processing

### 2.1 Pull Existing Auto Captions

If available:

* Retrieve transcript
* Convert to structured time-aligned format

If unavailable:

* Extract audio via legal API methods
* Use Azure Speech-to-Text API

### 2.2 Caption Enhancement

Enhance transcript to meet WCAG 1.2.2:

* Insert punctuation
* Normalize casing
* Add speaker detection
* Insert non-speech cues:

  * [music]
  * [applause]
  * [laughter]

Output:
Structured caption JSON with timestamps

---

## Step 3 – Visual Content Analysis

### 3.1 Frame Sampling

* Extract frames every N seconds (configurable, default 2s)
* Additional sampling during scene changes

### 3.2 Visual Analysis via Azure OpenAI Vision

For each frame:

Prompt model to determine:

* Is there text on screen?
* Is there a diagram?
* Is there math/equations?
* Is the visual essential to understanding?
* Is this information verbally described?

Return structured response:

```
{
  essential_visual: true/false,
  described_in_audio: true/false,
  risk_level: low/medium/high,
  description_suggestion: "..."
}
```

---

## Step 4 – Risk Detection Engine

Flag segments where:

* Essential visual = true
* AND described_in_audio = false

Assign:

* Risk score per segment
* Overall compliance confidence score (0–100)

Confidence score factors:

* % of runtime with essential visual not described
* Audio clarity confidence
* OCR confidence
* Model uncertainty flags

---

## Step 5 – Description Injection Logic

For flagged segments:

System may:

* Auto-generate descriptive caption block
  OR
* Insert placeholder:
  “[Visual content requires manual description]”

These must be clearly marked for review.

---

## Step 6 – Human Review Interface

Frontend features:

* Video playback
* Timeline with flagged markers
* Editable caption blocks
* Side panel with:

  * AI suggested visual description
  * Risk level
  * Compliance reasoning

User can:

* Accept suggestion
* Modify suggestion
* Mark as “adequately described in audio”

Changes are saved in structured caption JSON.

---

## Step 7 – VTT Generation

System generates:

Standards-compliant WebVTT:

```
WEBVTT

00:00:01.000 --> 00:00:04.000
Today we analyze Newton’s Second Law.

00:00:05.000 --> 00:00:09.000
[On screen: F = ma]

00:00:10.000 --> 00:00:15.000
A free-body diagram appears showing a block on an incline.
```

Must:

* Follow strict formatting
* Validate timestamp ordering
* Avoid overlapping intervals

---

## Step 8 – Upload to YouTube

Use YouTube API:

* captions.insert endpoint
* Set track as:

  * English
  * Draft or Published (configurable)

---

# 8. Compliance Report Output

System generates downloadable JSON + PDF report including:

* Video ID
* Scan date
* Total duration
* # of flagged segments
* % reviewed
* Final compliance confidence score
* Known limitations disclaimer

Purpose:

* Legal defensibility documentation
* Audit trail

---

# 9. Compliance Confidence Score Model

Score calculated using weighted factors:

| Factor                   | Weight |
| ------------------------ | ------ |
| Caption completeness     | 30%    |
| Visual coverage          | 30%    |
| Manual review completion | 20%    |
| Model uncertainty flags  | 10%    |
| OCR reliability          | 10%    |

Score Range:

* 90–100 = High confidence ADA-aligned
* 75–89 = Moderate confidence (manual review advised)
* <75 = High risk of non-compliance

---

# 10. Security & Legal Considerations

* OAuth required for YouTube access
* Store minimal video data
* Temporary frame storage only
* Clear disclaimer:
  “Tool assists in compliance but does not guarantee legal immunity.”

---

# 11. Scalability Design (Future SaaS)

Design backend to support:

* Batch processing queue
* Async job system
* User accounts
* Multi-channel support
* Storage in Azure Blob Storage
* Stripe billing integration

---

# 12. Azure Services Recommended

* Azure OpenAI (GPT-4o w/ vision)
* Azure Speech-to-Text
* Azure Blob Storage
* Azure Functions or App Service
* Azure SQL or CosmosDB

---

# 13. MVP Success Criteria (UCLA POC)

* Process 20 YouTube videos
* Generate VTT files
* Identify at least 90% of major visual-only instructional moments
* Provide usable compliance score
* Allow manual correction

---

# 14. Risks

* Vision model hallucinations
* Over-flagging (fatigue)
* Under-flagging (liability risk)
* YouTube API quota limits
* Processing cost scaling

---

# 15. Future Enhancements

* Equation LaTeX detection
* STEM glossary injection
* Confidence heatmap timeline
* Automated audio description track generation
* LMS integration
* Enterprise dashboard

---

# Strategic Note (Important)

This tool positions you not just as compliant —
but as someone proactively building institutional accessibility infrastructure.

If this works well, this becomes:

* A UCLA internal solution
* Or an Actual Education SaaS product
* Or something universities license

