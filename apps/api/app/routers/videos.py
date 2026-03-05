from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.caption_version import CaptionVersion
from app.models.frame_analysis import FrameAnalysis
from app.models.job import Job
from app.models.segment import Segment
from app.models.video import Video
from app.schemas.video import VideoImportRequest, VideoResponse, VideoListResponse
from app.services.youtube_service import youtube_service

router = APIRouter(prefix="/videos", tags=["videos"])
logger = logging.getLogger(__name__)


@router.post("", response_model=VideoResponse)
def import_video(req: VideoImportRequest, db: Session = Depends(get_db)):
    try:
        metadata = youtube_service.get_video_metadata(req.url)
    except ValueError as exc:
        # Invalid YouTube URL/video id or unsupported input format.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        # Missing configuration/dependency for real integrations.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("YouTube metadata import failed for url=%s", req.url)
        raise HTTPException(status_code=502, detail=f"YouTube metadata fetch failed: {exc}") from exc

    existing = db.query(Video).filter(Video.youtube_id == metadata["youtube_id"]).first()
    if existing:
        return existing

    video = Video(**metadata)
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


@router.get("", response_model=VideoListResponse)
def list_videos(db: Session = Depends(get_db)):
    videos = db.query(Video).order_by(Video.created_at.desc()).all()
    return VideoListResponse(videos=videos, total=len(videos))


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(video_id: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.delete("/{video_id}", status_code=204)
def delete_video(video_id: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Delete children explicitly because FK constraints are not configured with cascade.
    db.query(Job).filter(Job.video_id == video_id).delete(synchronize_session=False)
    db.query(Segment).filter(Segment.video_id == video_id).delete(synchronize_session=False)
    db.query(FrameAnalysis).filter(FrameAnalysis.video_id == video_id).delete(synchronize_session=False)
    db.query(CaptionVersion).filter(CaptionVersion.video_id == video_id).delete(synchronize_session=False)
    db.delete(video)
    db.commit()

    return Response(status_code=204)
