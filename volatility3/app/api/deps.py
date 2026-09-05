"""Shared FastAPI dependencies.

`get_current_user` is a no-op for the MVP (single-user, no auth) but every
route already depends on it and every `Image`/`Job` row already carries a
nullable `created_by` — swapping this for real JWT/OIDC auth later is a
dependency change, not a schema/route redesign.
"""

from __future__ import annotations


def get_current_user() -> str | None:
    return None
