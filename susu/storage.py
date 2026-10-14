"""Load and save a susu group to a JSON file on disk.

The command line interface keeps the group in a JSON file so that each command
(add a member, record a payment, close a week) runs as a separate program and
still sees the earlier changes. Saving is done atomically: the new state is
written to a temporary file and then moved into place, so an interrupted write
cannot leave a half-written, corrupt state file behind.
"""

from __future__ import annotations

import json
import os
import tempfile

from .errors import ValidationError
from .group import SusuGroup


def load_group(path: str) -> SusuGroup | None:
    """Load a group from ``path``, or return None if the file does not exist."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as error:
        raise ValidationError("state file %s is corrupt: %s" % (path, error))
    return SusuGroup.from_dict(data)


def save_group(group: SusuGroup, path: str) -> None:
    """Save ``group`` to ``path`` atomically so state is never half-written."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)

    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=directory,
        prefix=".susu-",
        suffix=".tmp",
        delete=False,
    )
    try:
        with handle:
            json.dump(group.to_dict(), handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(handle.name, path)
    except BaseException:
        # Clean up the temporary file if anything went wrong before the move.
        if os.path.exists(handle.name):
            os.remove(handle.name)
        raise
