"""
File upload router with async operations
"""

import os
import uuid
import aiofiles
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy import select, insert, delete, func, and_
from databases import Database

from ..database import database
from ..models import files
from ..schemas import FileResponse as FileResponseModel, FileList, PaginationParams, UserResponse
from ..dependencies import (
    get_database,
    get_current_active_user,
    get_current_superuser,
    get_pagination_params,
    calculate_pagination
)
from ..config import settings

router = APIRouter()


async def validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    
    # Check file size
    if file.size and file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size too large. Maximum size: {settings.MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    # Check file type
    if file.content_type not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_FILE_TYPES)}"
        )


async def save_file(file: UploadFile, user_id: int) -> dict:
    """Save uploaded file to disk and return file info"""
    
    # Generate unique filename
    file_extension = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Create upload directory if it doesn't exist
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(exist_ok=True)
    
    # Save file
    file_path = upload_dir / unique_filename
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    return {
        "filename": unique_filename,
        "original_filename": file.filename,
        "file_path": str(file_path),
        "file_size": len(content),
        "content_type": file.content_type,
        "uploaded_by": user_id
    }


@router.post("/upload", response_model=FileResponseModel, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_active_user),
    db: Database = Depends(get_database)
):
    """Upload a file"""
    
    # Validate file
    await validate_file(file)
    
    # Save file
    file_info = await save_file(file, current_user.id)
    
    # Save file info to database
    query = insert(files).values(**file_info)
    file_id = await db.execute(query)
    
    # Fetch created file record
    query = select(files).where(files.c.id == file_id)
    file_record = await db.fetch_one(query)
    
    return FileResponseModel(**file_record)


@router.post("/upload-multiple", response_model=List[FileResponseModel], status_code=status.HTTP_201_CREATED)
async def upload_multiple_files(
    files_list: List[UploadFile] = File(...),
    current_user: UserResponse = Depends(get_current_active_user),
    db: Database = Depends(get_database)
):
    """Upload multiple files"""
    
    if len(files_list) > 10:  # Limit to 10 files
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many files. Maximum 10 files allowed"
        )
    
    uploaded_files = []
    
    for file in files_list:
        # Validate file
        await validate_file(file)
        
        # Save file
        file_info = await save_file(file, current_user.id)
        
        # Save file info to database
        query = insert(files).values(**file_info)
        file_id = await db.execute(query)
        
        # Fetch created file record
        query = select(files).where(files.c.id == file_id)
        file_record = await db.fetch_one(query)
        
        uploaded_files.append(FileResponseModel(**file_record))
    
    return uploaded_files


@router.get("/", response_model=FileList)
async def list_files(
    pagination: PaginationParams = Depends(get_pagination_params),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    current_user: UserResponse = Depends(get_current_active_user),
    db: Database = Depends(get_database)
):
    """List user's uploaded files"""
    
    # Build base query
    query = select(files).where(files.c.uploaded_by == current_user.id)
    
    # Apply content type filter
    if content_type:
        query = query.where(files.c.content_type.ilike(f"%{content_type}%"))
    
    # Get total count
    count_query = select(func.count()).select_from(query.alias())
    total = await db.fetch_val(count_query)
    
    # Apply pagination
    offset = (pagination.page - 1) * pagination.size
    query = query.offset(offset).limit(pagination.size).order_by(files.c.created_at.desc())
    
    # Execute query
    results = await db.fetch_all(query)
    
    # Calculate pagination metadata
    pagination_meta = calculate_pagination(total, pagination.page, pagination.size)
    
    return FileList(
        files=[FileResponseModel(**file) for file in results],
        **pagination_meta
    )


@router.get("/admin/", response_model=FileList)
async def list_all_files(
    pagination: PaginationParams = Depends(get_pagination_params),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    current_user: UserResponse = Depends(get_current_superuser),
    db: Database = Depends(get_database)
):
    """List all uploaded files (admin only)"""
    
    # Build base query
    query = select(files)
    conditions = []
    
    # Apply filters
    if content_type:
        conditions.append(files.c.content_type.ilike(f"%{content_type}%"))
    
    if user_id:
        conditions.append(files.c.uploaded_by == user_id)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Get total count
    count_query = select(func.count()).select_from(query.alias())
    total = await db.fetch_val(count_query)
    
    # Apply pagination
    offset = (pagination.page - 1) * pagination.size
    query = query.offset(offset).limit(pagination.size).order_by(files.c.created_at.desc())
    
    # Execute query
    results = await db.fetch_all(query)
    
    # Calculate pagination metadata
    pagination_meta = calculate_pagination(total, pagination.page, pagination.size)
    
    return FileList(
        files=[FileResponseModel(**file) for file in results],
        **pagination_meta
    )


@router.get("/{file_id}", response_model=FileResponseModel)
async def get_file_info(
    file_id: int,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Database = Depends(get_database)
):
    """Get file information"""
    
    query = select(files).where(files.c.id == file_id)
    file_record = await db.fetch_one(query)
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check permissions (file owner or admin)
    if file_record["uploaded_by"] != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return FileResponseModel(**file_record)


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Database = Depends(get_database)
):
    """Download a file"""
    
    query = select(files).where(files.c.id == file_id)
    file_record = await db.fetch_one(query)
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check permissions (file owner or admin)
    if file_record["uploaded_by"] != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if file exists on disk
    file_path = Path(file_record["file_path"])
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )
    
    return FileResponse(
        path=file_path,
        filename=file_record["original_filename"],
        media_type=file_record["content_type"]
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: int,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Database = Depends(get_database)
):
    """Delete a file"""
    
    query = select(files).where(files.c.id == file_id)
    file_record = await db.fetch_one(query)
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check permissions (file owner or admin)
    if file_record["uploaded_by"] != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Delete file from disk
    file_path = Path(file_record["file_path"])
    if file_path.exists():
        file_path.unlink()
    
    # Delete file record from database
    query = delete(files).where(files.c.id == file_id)
    await db.execute(query)


@router.get("/stats/", response_model=dict)
async def get_file_stats(
    current_user: UserResponse = Depends(get_current_active_user),
    db: Database = Depends(get_database)
):
    """Get file upload statistics for current user"""
    
    # Total files count
    total_files_query = select(func.count()).where(files.c.uploaded_by == current_user.id)
    total_files = await db.fetch_val(total_files_query)
    
    # Total file size
    total_size_query = select(func.sum(files.c.file_size)).where(files.c.uploaded_by == current_user.id)
    total_size = await db.fetch_val(total_size_query) or 0
    
    # Files by content type
    content_type_query = select(
        files.c.content_type, 
        func.count().label('count')
    ).where(
        files.c.uploaded_by == current_user.id
    ).group_by(files.c.content_type)
    
    content_types = await db.fetch_all(content_type_query)
    
    return {
        "total_files": total_files,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "files_by_type": {row["content_type"]: row["count"] for row in content_types}
    }


@router.get("/admin/stats/", response_model=dict)
async def get_admin_file_stats(
    current_user: UserResponse = Depends(get_current_superuser),
    db: Database = Depends(get_database)
):
    """Get file upload statistics for all users (admin only)"""
    
    # Total files count
    total_files_query = select(func.count()).select_from(files)
    total_files = await db.fetch_val(total_files_query)
    
    # Total file size
    total_size_query = select(func.sum(files.c.file_size)).select_from(files)
    total_size = await db.fetch_val(total_size_query) or 0
    
    # Files by content type
    content_type_query = select(
        files.c.content_type, 
        func.count().label('count')
    ).group_by(files.c.content_type)
    
    content_types = await db.fetch_all(content_type_query)
    
    # Files by user
    user_query = select(
        files.c.uploaded_by,
        func.count().label('count'),
        func.sum(files.c.file_size).label('total_size')
    ).group_by(files.c.uploaded_by)
    
    users_stats = await db.fetch_all(user_query)
    
    return {
        "total_files": total_files,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "files_by_type": {row["content_type"]: row["count"] for row in content_types},
        "files_by_user": [
            {
                "user_id": row["uploaded_by"], 
                "count": row["count"], 
                "size_mb": round(row["total_size"] / 1024 / 1024, 2)
            } 
            for row in users_stats
        ]
    } 