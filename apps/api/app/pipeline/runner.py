import logging
import asyncio
import time

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.video import Video
from app.models.job import Job
from app.config import settings
from app.services.ai_usage import (
    clear_ai_usage_tracking,
    get_ai_usage_stats,
    start_ai_usage_tracking,
)
from app.pipeline.steps import (
    step_fetch_metadata,
    step_download_captions,
    step_enhance_captions,
    step_extract_frames,
    step_analyze_frames_ocr,
    step_analyze_frames_vision,
    step_align_segments,
    step_score_risk,
    step_generate_descriptions,
    step_compute_compliance,
    step_finalize,
)

logger = logging.getLogger(__name__)

PIPELINE_STEPS = [
    ("fetch_metadata", 5),
    ("download_captions", 15),
    ("enhance_captions", 25),
    ("extract_frames", 35),
    ("analyze_frames_ocr", 45),
    ("analyze_frames_vision", 55),
    ("align_segments", 65),
    ("score_risk", 75),
    ("generate_descriptions", 85),
    ("compute_compliance", 92),
    ("finalize", 100),
]


def _update_job(db: Session, job_id: str, step: str, progress: int, status: str = "running"):
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.status = status
        job.current_step = step
        job.progress = progress
        db.commit()


def _format_job_summary(score: float, duration_seconds: float) -> str:
    usage = get_ai_usage_stats()
    estimated_cost = usage.estimate_cost_usd()
    if settings.AI_COST_INPUT_PER_1M_TOKENS <= 0 and settings.AI_COST_OUTPUT_PER_1M_TOKENS <= 0:
        cost_part = "Estimated AI cost: unavailable (set AI_COST_INPUT_PER_1M_TOKENS / AI_COST_OUTPUT_PER_1M_TOKENS)."
    else:
        cost_part = (
            f"Estimated AI cost: ${estimated_cost:.4f} "
            f"(input ${settings.AI_COST_INPUT_PER_1M_TOKENS}/1M, output ${settings.AI_COST_OUTPUT_PER_1M_TOKENS}/1M)."
        )
    return (
        f"Scan complete. Compliance score: {score:.1f}%. "
        f"Duration: {duration_seconds:.1f}s. "
        f"AI tokens: total={usage.total_tokens}, input={usage.prompt_tokens}, output={usage.completion_tokens}. "
        f"{cost_part}"
    )


async def run_pipeline(job_id: str, video_id: str):
    """Run the full 11-step analysis pipeline for a video."""
    db = SessionLocal()
    started_at = time.perf_counter()
    start_ai_usage_tracking()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            _update_job(db, job_id, "error", 0, "failed")
            return

        _update_job(db, job_id, "fetch_metadata", 0, "running")

        # Step 1: Fetch metadata
        _update_job(db, job_id, "fetch_metadata", 5)
        await asyncio.to_thread(step_fetch_metadata, video, db)

        # Step 2: Download captions
        _update_job(db, job_id, "download_captions", 15)
        await asyncio.to_thread(step_download_captions, video, db)

        # Step 3: Enhance captions
        _update_job(db, job_id, "enhance_captions", 25)
        await asyncio.to_thread(step_enhance_captions, video, db)

        # Step 4: Extract frames
        _update_job(db, job_id, "extract_frames", 35)
        frames = await asyncio.to_thread(step_extract_frames, video, db)

        # Step 5: Analyze frames (OCR)
        _update_job(db, job_id, "analyze_frames_ocr", 45)
        analyses = await asyncio.to_thread(step_analyze_frames_ocr, video, frames, db)

        # Step 6: Analyze frames (vision)
        _update_job(db, job_id, "analyze_frames_vision", 55)
        await asyncio.to_thread(step_analyze_frames_vision, video, frames, analyses, db)

        # Step 7: Align segments
        _update_job(db, job_id, "align_segments", 65)
        segments = await asyncio.to_thread(step_align_segments, video, db)

        # Step 8: Score risk
        _update_job(db, job_id, "score_risk", 75)
        await asyncio.to_thread(step_score_risk, video, segments, db)

        # Step 9: Generate descriptions
        _update_job(db, job_id, "generate_descriptions", 85)
        await asyncio.to_thread(step_generate_descriptions, video, segments, db)

        # Step 10: Compute compliance
        _update_job(db, job_id, "compute_compliance", 92)
        score = await asyncio.to_thread(step_compute_compliance, video, segments, db)

        # Step 11: Finalize
        _update_job(db, job_id, "finalize", 100)
        await asyncio.to_thread(step_finalize, video, db)

        # Mark job complete
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "completed"
            job.progress = 100
            job.current_step = "done"
            job.result_summary = _format_job_summary(
                score=score,
                duration_seconds=time.perf_counter() - started_at,
            )
            db.commit()

        logger.info(f"Pipeline complete for video {video_id}, score={score:.1f}%")

    except Exception as e:
        logger.exception(f"Pipeline failed for job {job_id}: {e}")
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(e)
                usage = get_ai_usage_stats()
                elapsed = time.perf_counter() - started_at
                estimated_cost = usage.estimate_cost_usd()
                job.result_summary = (
                    f"Scan failed after {elapsed:.1f}s. "
                    f"AI tokens: total={usage.total_tokens}, input={usage.prompt_tokens}, output={usage.completion_tokens}. "
                    f"Estimated AI cost so far: ${estimated_cost:.4f}."
                )
                db.commit()
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.status = "imported"
                db.commit()
        except Exception:
            pass
    finally:
        clear_ai_usage_tracking()
        db.close()
