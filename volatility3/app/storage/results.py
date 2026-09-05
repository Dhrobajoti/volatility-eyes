"""Reads/writes plugin run results and lists extracted files on disk.

`Job.result_path` stores a relative path, not the JSON body in Postgres —
plugin output (e.g. filesystem-walking or malfind results) can be tens of MB,
which doesn't belong in a database row.
"""

from __future__ import annotations

import json
import os
import uuid

from ..config import get_settings

RESULT_FILENAME = "result.json"
# Separate from result.json/read_result: legacy (volatility2) jobs produce
# plain text, not the structured row-JSON volatility3 plugins return, and
# were never going to share a file format with something the UI renders as
# an interactive sortable/hex-aware table.
LEGACY_RESULT_FILENAME = "result.txt"


def job_dir(job_id: uuid.UUID) -> str:
    return os.path.join(get_settings().storage_root, "jobs", str(job_id))


def job_files_dir(job_id: uuid.UUID) -> str:
    return os.path.join(job_dir(job_id), "files")


def write_result(job_id: uuid.UUID, data: list[dict]) -> str:
    directory = job_dir(job_id)
    os.makedirs(directory, exist_ok=True)
    absolute_path = os.path.join(directory, RESULT_FILENAME)
    with open(absolute_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    # See images.py's save_uploaded_image for why this is normalized to
    # forward slashes rather than left as the native os.path.relpath separator.
    return os.path.relpath(absolute_path, get_settings().storage_root).replace(os.sep, "/")


def read_result(result_path: str) -> list[dict]:
    absolute_path = os.path.join(get_settings().storage_root, result_path)
    with open(absolute_path, encoding="utf-8") as f:
        return json.load(f)


def write_legacy_result(job_id: uuid.UUID, text: str) -> str:
    directory = job_dir(job_id)
    os.makedirs(directory, exist_ok=True)
    absolute_path = os.path.join(directory, LEGACY_RESULT_FILENAME)
    with open(absolute_path, "w", encoding="utf-8") as f:
        f.write(text)
    return os.path.relpath(absolute_path, get_settings().storage_root).replace(os.sep, "/")


def read_legacy_result(result_path: str) -> str:
    absolute_path = os.path.join(get_settings().storage_root, result_path)
    with open(absolute_path, encoding="utf-8") as f:
        return f.read()


def list_job_files(job_id: uuid.UUID) -> list[str]:
    directory = job_files_dir(job_id)
    if not os.path.isdir(directory):
        return []
    return sorted(
        name for name in os.listdir(directory) if os.path.isfile(os.path.join(directory, name))
    )


def job_file_path(job_id: uuid.UUID, filename: str) -> str:
    return os.path.join(job_files_dir(job_id), filename)


def delete_job_files(job_id: uuid.UUID) -> None:
    import shutil

    shutil.rmtree(job_dir(job_id), ignore_errors=True)
