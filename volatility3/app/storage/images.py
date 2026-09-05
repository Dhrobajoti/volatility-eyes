"""Streams uploaded memory images to disk without buffering them in memory.

Images can be many GB, so the upload handler must never call `await file.read()`
on the whole body — it copies in fixed-size chunks straight to disk while
incrementally computing a SHA256 for later integrity/reference checks.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass

from fastapi import UploadFile

from ..config import get_settings

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MiB


@dataclass
class SavedImage:
    image_id: uuid.UUID
    storage_path: str  # relative to STORAGE_ROOT
    absolute_path: str
    size_bytes: int
    sha256: str


def images_dir(image_id: uuid.UUID) -> str:
    return os.path.join(get_settings().storage_root, "images", str(image_id))


async def save_uploaded_image(upload: UploadFile) -> SavedImage:
    image_id = uuid.uuid4()
    directory = images_dir(image_id)
    os.makedirs(directory, exist_ok=True)

    filename = os.path.basename(upload.filename or "image.raw")
    absolute_path = os.path.join(directory, filename)
    # Stored with forward slashes regardless of host OS: os.path.relpath uses
    # the native separator, which breaks lookups if the DB is ever read from
    # a different OS than wrote it (e.g. a dev container vs. a Windows host
    # sharing the same Postgres volume). os.path.join happily accepts forward
    # slashes on both Windows and POSIX, so normalizing here is safe both ways.
    storage_path = os.path.relpath(absolute_path, get_settings().storage_root).replace(os.sep, "/")

    hasher = hashlib.sha256()
    size_bytes = 0
    with open(absolute_path, "wb") as out:
        while chunk := await upload.read(CHUNK_SIZE):
            out.write(chunk)
            hasher.update(chunk)
            size_bytes += len(chunk)

    return SavedImage(
        image_id=image_id,
        storage_path=storage_path,
        absolute_path=absolute_path,
        size_bytes=size_bytes,
        sha256=hasher.hexdigest(),
    )


def absolute_path_for(storage_path: str) -> str:
    return os.path.join(get_settings().storage_root, storage_path)


def delete_image_files(storage_path: str) -> None:
    directory = os.path.dirname(absolute_path_for(storage_path))
    if os.path.isdir(directory):
        import shutil

        shutil.rmtree(directory, ignore_errors=True)
