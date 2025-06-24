# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import contextlib
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile


@contextlib.contextmanager
def ensure_file_on_disk(django_file: TemporaryUploadedFile | InMemoryUploadedFile):
    """Ensure the uploaded file is on the disk.

    For TemporaryUploadedFile it yields the file and for InMemoryUploadedFile it saves the content
    into a temporary file.
    """
    if hasattr(django_file, "temporary_file_path"):
        yield django_file.temporary_file_path()
        return

    with NamedTemporaryFile() as f:
        f.write(django_file.read())
        f.flush()
        yield f.name


@contextlib.contextmanager
def file_or_stdout(file_path: str | None):
    if file_path is None:
        yield sys.stdout
        return

    with Path(file_path).open(mode="w", encoding="UTF-8") as f:
        yield f
