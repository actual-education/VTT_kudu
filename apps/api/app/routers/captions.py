from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.video import Video
from app.schemas.caption import CaptionVersionResponse, CaptionIngestRequest, CaptionValidationResponse
from app.services.caption_service import caption_service

router = APIRouter(prefix="/videos/{video_id}/captions", tags=["captions"])


@router.post("/ingest", response_model=CaptionVersionResponse)
def ingest_captions(video_id: str, req: CaptionIngestRequest, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    version = caption_service.ingest(req.content, video_id, db)
    return version


@router.post("/enhance", response_model=CaptionVersionResponse)
def enhance_captions(video_id: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    version = caption_service.enhance(video_id, db)
    if not version:
        raise HTTPException(status_code=400, detail="No captions to enhance")
    return version


@router.get("/latest", response_class=PlainTextResponse)
def get_latest_vtt(video_id: str, db: Session = Depends(get_db)):
    vtt = caption_service.get_latest_vtt(video_id, db)
    if not vtt:
        raise HTTPException(status_code=404, detail="No captions found")
    return PlainTextResponse(vtt, media_type="text/vtt")


@router.get("/versions", response_model=list[CaptionVersionResponse])
def list_versions(video_id: str, db: Session = Depends(get_db)):
    return caption_service.get_versions(video_id, db)


@router.post("/validate", response_model=CaptionValidationResponse)
def validate_captions(video_id: str, req: CaptionIngestRequest, db: Session = Depends(get_db)):
    errors = caption_service.validate(req.content)
    return CaptionValidationResponse(valid=len(errors) == 0, errors=errors)
