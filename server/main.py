"""
FastAPI service that stores and serves video metadata in a MariaDB database.

Uses SQLAlchemy ORM for clean database operations without manual cursor management.

Run with:
    uvicorn main:app --reload --port 8002
"""

from __future__ import annotations

import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Path, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl, validator
from sqlalchemy import create_engine, Column, String, Integer, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# --------------------------------------------------------------------------- #
# Database configuration
# --------------------------------------------------------------------------- #
DATABASE_URL = "mysql+pymysql://vibeout:viebout@localhost/vibeout_quips"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --------------------------------------------------------------------------- #
# SQLAlchemy Model
# --------------------------------------------------------------------------- #
class Video(Base):
    __tablename__ = "videos"

    id = Column(String(50), primary_key=True, index=True)
    url = Column(String(500), nullable=False)
    name = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    image = Column(String(500), nullable=True)
    video = Column(String(500), nullable=True)
    user = Column(String(255), nullable=True)
    poster = Column(String(500), nullable=True)
    script = Column(String(2000), nullable=True)
    views = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# Create tables (if they don't exist)
Base.metadata.create_all(bind=engine)


# --------------------------------------------------------------------------- #
# Pydantic models
# --------------------------------------------------------------------------- #
class VideoBase(BaseModel):
    url: str
    name: str
    title: str
    image: Optional[str] = None
    video: Optional[str] = None
    user: Optional[str] = None
    poster: Optional[str] = None
    script: Optional[str] = None


class VideoCreate(VideoBase):
    """All fields required for creation (except the auto-generated id)."""
    pass


class VideoUpdate(BaseModel):
    """All fields optional – only supplied keys are updated."""
    url: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    image: Optional[str] = None
    video: Optional[str] = None
    user: Optional[str] = None
    poster: Optional[str] = None
    script: Optional[str] = None

    @validator("*", pre=True, always=True)
    def empty_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


class VideoResponse(VideoBase):
    id: str = Field(..., description="Primary key")
    views: int = Field(..., ge=0)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2 (use orm_mode = True for v1)


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    videos: List[VideoResponse]


# --------------------------------------------------------------------------- #
# Dependency
# --------------------------------------------------------------------------- #
def get_db():
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# FastAPI app
# --------------------------------------------------------------------------- #
app = FastAPI(
    title="Video Metadata Service",
    description="CRUD API for video records with automatic view counting.",
    version="2.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/videos", response_model=PaginatedResponse)
def list_videos(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: Optional[str] = Query(None, regex="^(views|title|created_at)$"),
    db: Session = Depends(get_db),
):
    """
    Return paginated video records.
    
    - **page**: Page number (starts at 1)
    - **page_size**: Number of videos per page (max 100)
    - **sort_by**: Sort field (views, title, or created_at)
    """
    # Get total count
    total = db.query(func.count(Video.id)).scalar()
    
    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size
    
    # Build query with sorting
    query = db.query(Video)
    if sort_by == "views":
        query = query.order_by(Video.views.desc())
    elif sort_by == "title":
        query = query.order_by(Video.title.asc())
    else:  # Default to created_at
        query = query.order_by(Video.created_at.desc())
    
    # Apply pagination
    videos = query.offset(offset).limit(page_size).all()
    
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        videos=videos,
    )

@app.get("/videos/search", response_model=PaginatedResponse)
def search_videos(
    q: str = Query(..., min_length=1, description="Search query for title, name, or script"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """
    Search videos by title, name, or script content (case-insensitive).
    
    - **q**: Search query string
    - **page**: Page number (starts at 1)
    - **page_size**: Number of videos per page (max 100)
    """
    # Build search filter (case-insensitive)
    search_pattern = f"%{q}%"
    query = db.query(Video).filter(
        (Video.title.ilike(search_pattern)) |
        (Video.name.ilike(search_pattern)) |
        (Video.script.ilike(search_pattern))
    )
    
    # Get total count for search results
    total = query.count()
    
    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size
    
    # Apply pagination and ordering
    videos = query.order_by(Video.views.desc()).offset(offset).limit(page_size).all()
    
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        videos=videos,
    )

@app.get(
    "/videos/{video_id}",
    response_model=VideoResponse,
    responses={404: {"description": "Video not found"}},
)
def get_video(
    video_id: str = Path(..., description="Video identifier"),
    db: Session = Depends(get_db),
):
    """
    Retrieve a single video and increment its view counter.
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Increment view count
    video.views += 1
    db.commit()
    db.refresh(video)
    
    return video


@app.post(
    "/videos",
    response_model=VideoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"description": "Invalid payload"}},
)
def create_video(payload: VideoCreate, db: Session = Depends(get_db)):
    """Insert a new video record. The id is generated as a UUID4 string."""
    video = Video(
        id=uuid.uuid4().hex,
        url=payload.url,
        name=payload.name,
        title=payload.title,
        image=payload.image,
        video=payload.video,
        user=payload.user,
        poster=payload.poster,
        script=payload.script,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


@app.put(
    "/videos/{video_id}",
    response_model=VideoResponse,
    responses={404: {"description": "Video not found"}},
)
def update_video(
    payload: VideoUpdate,
    video_id: str = Path(..., description="Video identifier"),
    db: Session = Depends(get_db),
):
    """Update supplied fields of an existing video."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update")
    
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Update fields
    for key, value in updates.items():
        setattr(video, key, value)
    
    video.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(video)
    return video


@app.delete(
    "/videos/{video_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Video not found"}},
)
def delete_video(
    video_id: str = Path(..., description="Video identifier"),
    db: Session = Depends(get_db),
):
    """Remove a video record permanently."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    db.delete(video)
    db.commit()
    return None