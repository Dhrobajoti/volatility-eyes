"""File handler for plugins that dump files (dumpfiles, procdump, malfind --dump, ...).

Modeled directly on `CLIDirectFileHandler` in
volatility3/volatility3/cli/__init__.py:822 — writes to a temp file under the
job's output directory and renames to the plugin's preferred filename on
close(), de-duplicating on collision with a `-N` suffix. `construct_plugin`
takes a *class* (not an instance) for its `open_method` parameter, so this
module exposes a factory that closes over `output_dir` and returns a subclass,
matching the CLI's own `file_handler_class_factory` pattern.
"""

from __future__ import annotations

import logging
import os
import tempfile

from volatility3.framework import interfaces

vollog = logging.getLogger(__name__)


def file_handler_class(output_dir: str) -> type[interfaces.plugins.FileHandlerInterface]:
    # Must exist before any handler is constructed: __init__ below calls
    # tempfile.mkstemp(dir=output_dir), which requires the directory to
    # already exist (unlike _get_final_filename's os.makedirs, mkstemp
    # doesn't create it) - and __init__ always runs before close() does.
    os.makedirs(output_dir, exist_ok=True)

    class JobFileHandler(interfaces.plugins.FileHandlerInterface):
        def _get_final_filename(self) -> str:
            os.makedirs(output_dir, exist_ok=True)
            output_filename = os.path.join(output_dir, self.preferred_filename)
            filename, extension = os.path.splitext(output_filename)

            counter = 1
            while os.path.exists(output_filename):
                output_filename = f"{filename}-{counter}{extension}"
                counter += 1
            return output_filename

        def __init__(self, filename: str):
            fd, self._name = tempfile.mkstemp(suffix=".vol3", prefix="tmp_", dir=output_dir)
            self._file = open(fd, mode="w+b")
            super().__init__(filename)
            for item in dir(self._file):
                if not item.startswith("_") and item not in (
                    "closed",
                    "close",
                    "mode",
                    "name",
                ):
                    setattr(self, item, getattr(self._file, item))

        def __getattr__(self, item):
            return getattr(self._file, item)

        @property
        def closed(self) -> bool:
            return self._file.closed

        @property
        def mode(self) -> str:
            return self._file.mode

        @property
        def name(self) -> str:
            return self._file.name

        def close(self) -> None:
            if self._file.closed:
                return None

            output_filename = self._get_final_filename()
            self.preferred_filename = os.path.basename(output_filename)

            self._file.close()
            os.rename(self._name, output_filename)
            vollog.info(f"Saved stored plugin file: {output_filename}")

    return JobFileHandler
