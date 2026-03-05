from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.segment import Segment
from app.schemas.segment import SegmentResponse, SegmentUpdateRequest

router = APIRouter(prefix="/videos/{video_id}/segments", tags=["segments"])


@router.get("", response_model=list[SegmentResponse])
def list_segments(
    video_id: str,
    risk_level: Optional[str] = Query(None, description="Filter by risk level: low, medium, high"),
    review_status: Optional[str] = Query(None, description="Filter by review status"),
    db: Session = Depends(get_db),
):
    query = db.query(Segment).filter(Segment.video_id == video_id)
    if risk_level:
        query = query.filter(Segment.risk_level == risk_level)
    if review_status:
        query = query.filter(Segment.review_status == review_status)
    return query.order_by(Segment.start_time).all()


@router.get("/{segment_id}", response_model=SegmentResponse)
def get_segment(video_id: str, segment_id: str, db: Session = Depends(get_db)):
    segment = (
        db.query(Segment)
        .filter(Segment.video_id == video_id, Segment.id == segment_id)
        .first()
    )
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment


@router.patch("/{segment_id}", response_model=SegmentResponse)
def update_segment(
    video_id: str,
    segment_id: str,
    req: SegmentUpdateRequest,
    db: Session = Depends(get_db),
):
    segment = (
        db.query(Segment)
        .filter(Segment.video_id == video_id, Segment.id == segment_id)
        .first()
    )
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    if req.review_status is not None:
        segment.review_status = req.review_status
    if req.transcript_text is not None:
        segment.transcript_text = req.transcript_text
    if req.ai_suggestion is not None:
        segment.ai_suggestion = req.ai_suggestion

    db.commit()
    db.refresh(segment)
    return segment
