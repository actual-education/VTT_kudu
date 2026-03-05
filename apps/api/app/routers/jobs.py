from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import Job
from app.models.video import Video
from app.schemas.job import ScanRequest, BatchScanRequest, JobResponse
from app.pipeline.queue import enqueue_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/scan", response_model=JobResponse)
async def start_scan(req: ScanRequest, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == req.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    job = Job(video_id=video.id, status="queued", progress=0)
    db.add(job)
    video.status = "scanning"
    db.commit()
    db.refresh(job)

    await enqueue_job(job.id, video.id)
    return job


@router.post("/batch", response_model=list[JobResponse])
async def start_batch_scan(req: BatchScanRequest, db: Session = Depends(get_db)):
    jobs = []
    for video_id in req.video_ids:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            continue
        job = Job(video_id=video.id, status="queued", progress=0)
        db.add(job)
        video.status = "scanning"
        jobs.append(job)
    db.commit()
    for job in jobs:
        db.refresh(job)
        await enqueue_job(job.id, job.video_id)
    return jobs


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/videos/{video_id}/latest", response_model=JobResponse | None)
def get_latest_job_for_video(video_id: str, db: Session = Depends(get_db)):
    return (
        db.query(Job)
        .filter(Job.video_id == video_id)
        .order_by(Job.updated_at.desc())
        .first()
    )


@router.get("/videos/{video_id}/latest-summary", response_model=JobResponse | None)
def get_latest_completed_or_failed_job_for_video(video_id: str, db: Session = Depends(get_db)):
    return (
        db.query(Job)
        .filter(
            Job.video_id == video_id,
            Job.status.in_(["completed", "failed"]),
        )
        .order_by(Job.updated_at.desc())
        .first()
    )
