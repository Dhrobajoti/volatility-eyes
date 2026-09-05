"""End-to-end test of vol_service.run_plugin against a real memory image.

No memory image ships with this repo (they're large and often
sensitive/licensed), so this test is skipped unless an image path is provided
via the VOL_TEST_IMAGE environment variable, e.g.:

    VOL_TEST_IMAGE=/path/to/image.raw pytest tests/test_vol_service_runner.py

Once a real image is available, this is the authoritative check that the
construct_plugin -> run -> HeadlessJsonRenderer pipeline actually produces
correct forensics output, not just that it doesn't crash.
"""

import os
import tempfile

import pytest

from app.vol_service import run_plugin
from app.vol_service.exceptions import MissingParametersError

IMAGE_PATH = os.environ.get("VOL_TEST_IMAGE")

pytestmark = pytest.mark.skipif(
    not IMAGE_PATH, reason="set VOL_TEST_IMAGE to a real memory image to run this test"
)


def test_pslist_returns_flat_process_rows():
    with tempfile.TemporaryDirectory() as output_dir:
        result = run_plugin(
            image_path=IMAGE_PATH,
            plugin_name="windows.pslist.PsList",
            params={},
            output_dir=output_dir,
        )
    assert len(result.data) > 0
    assert "PID" in result.columns
    first_row = result.data[0]
    assert "PID" in first_row
    assert "ImageFileName" in first_row


def test_pstree_returns_hierarchical_rows():
    with tempfile.TemporaryDirectory() as output_dir:
        result = run_plugin(
            image_path=IMAGE_PATH,
            plugin_name="windows.pstree.PsTree",
            params={},
            output_dir=output_dir,
        )
    assert len(result.data) > 0
    assert "__children" in result.data[0]


def test_progress_callback_is_invoked():
    calls = []

    def progress_cb(pct, description):
        calls.append((pct, description))

    with tempfile.TemporaryDirectory() as output_dir:
        run_plugin(
            image_path=IMAGE_PATH,
            plugin_name="windows.pslist.PsList",
            params={},
            output_dir=output_dir,
            progress_cb=progress_cb,
        )
    assert len(calls) > 0


def test_unsupported_pid_filter_still_runs_and_filters():
    with tempfile.TemporaryDirectory() as output_dir:
        result = run_plugin(
            image_path=IMAGE_PATH,
            plugin_name="windows.pslist.PsList",
            params={"pid": [4]},
            output_dir=output_dir,
        )
    assert all(row["PID"] == 4 for row in result.data)


def test_missing_required_param_raises_missing_parameters_error():
    with tempfile.TemporaryDirectory() as output_dir:
        with pytest.raises(MissingParametersError):
            run_plugin(
                image_path=IMAGE_PATH,
                plugin_name="windows.pe_symbols.PESymbols",
                params={},  # 'source' is required and not supplied
                output_dir=output_dir,
            )
