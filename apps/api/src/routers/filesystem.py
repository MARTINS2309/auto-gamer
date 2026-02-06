"""
Filesystem Router - Browse directories on the server.

Used by the frontend to pick directories for ROM imports, storage paths, etc.
"""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/filesystem")


class DirectoryEntry(BaseModel):
    """A file or directory entry."""

    name: str
    path: str
    is_dir: bool
    is_readable: bool


class DirectoryListResponse(BaseModel):
    """Response from listing a directory."""

    path: str
    parent: str | None
    entries: list[DirectoryEntry]


@router.get("/list", response_model=DirectoryListResponse)
def list_directory(
    path: str = Query(default="~", description="Directory path to list"),
    show_hidden: bool = Query(default=False, description="Include hidden files/folders"),
    dirs_only: bool = Query(default=True, description="Only show directories"),
):
    """
    List contents of a directory.

    Used by directory picker dialog to browse the filesystem.
    """
    # Expand user home directory
    expanded_path = os.path.expanduser(path)

    # Resolve to absolute path
    try:
        resolved = Path(expanded_path).resolve()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid path: {e}")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")

    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {path}")

    # Get parent directory
    parent = str(resolved.parent) if resolved.parent != resolved else None

    entries: list[DirectoryEntry] = []

    try:
        for item in sorted(resolved.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            # Skip hidden files unless requested
            if not show_hidden and item.name.startswith("."):
                continue

            # Skip files if dirs_only
            if dirs_only and not item.is_dir():
                continue

            # Check if readable
            is_readable = os.access(item, os.R_OK)

            entries.append(
                DirectoryEntry(
                    name=item.name,
                    path=str(item),
                    is_dir=item.is_dir(),
                    is_readable=is_readable,
                )
            )
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied: {path}")

    return DirectoryListResponse(
        path=str(resolved),
        parent=parent,
        entries=entries,
    )


@router.get("/home")
def get_home_directory():
    """Get the user's home directory path."""
    return {"path": os.path.expanduser("~")}


@router.get("/validate")
def validate_path(
    path: str = Query(..., description="Path to validate"),
    must_exist: bool = Query(default=False, description="Path must exist"),
    must_be_dir: bool = Query(default=False, description="Path must be a directory"),
):
    """
    Validate a path.

    Returns whether the path is valid and exists.
    """
    expanded = os.path.expanduser(path)

    try:
        resolved = Path(expanded).resolve()
        exists = resolved.exists()
        is_dir = resolved.is_dir() if exists else False
        is_readable = os.access(resolved, os.R_OK) if exists else False
        is_writable = os.access(resolved, os.W_OK) if exists else False
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "path": path,
            "resolved": None,
        }

    valid = True
    error = None

    if must_exist and not exists:
        valid = False
        error = "Path does not exist"
    elif must_be_dir and exists and not is_dir:
        valid = False
        error = "Path is not a directory"

    return {
        "valid": valid,
        "error": error,
        "path": path,
        "resolved": str(resolved),
        "exists": exists,
        "is_dir": is_dir,
        "is_readable": is_readable,
        "is_writable": is_writable,
    }
