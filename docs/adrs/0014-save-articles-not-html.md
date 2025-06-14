<!--
SPDX-FileCopyrightText: 2023-2025 Legadilo contributors

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# 14 - Save articles not in HTML

* **Date:** 2025-06-10
* **Status:** Postponed

## Context

Currently, only responses in HTML are supported.
If the response is in any other format, only the URL will be saved.
Some formats are common and could be supported to save and archive even more content!

Formats that could be saved:
- Plain text: save the file as content and extract a summary from the start of the file.
  Assume that the first line is the title.
- PDF could be saved as files and displayed within a `object` tag.
- EPUB could be imported into groups of articles.
  Since this is a ZIP based format, this implies enabling protections to prevent ZIP bombs.
  File path based attacks be handled correctly by [Python `zipfile` automatically](https://docs.python.org/3/library/zipfile.html#zipfile.ZipFile.extract) if we use `ZipFile.extract`.
  If the content is only read and saved in the database without an intermediate file, they won’t even be a problem.
- Raw HTML: save the raw HTML response before parsing and allow users to see it if parsing failed as a fallback.
  We could even allow them to pass a selector to extract the title and the content if we fail to do it manually.

Notes:
- Just like with HTML, if the file is too big, only the URL of the article is saved.
  *This will remain true no matter the format!*
  We are not a file sharing service.
- If an unsupported file format is used, only save the URL just like now.
- For PDF and EPUB, we need to save files:
  - The PDF so it can be displayed.
  - The EPUB so the initial file can be downloaded and all the included images so they can be viewed in the app.

See:
- [Support more article formats and sources](https://github.com/Jenselme/legadilo/issues/257)

### Code excerpts for ZIP protection

- Check the total size based on ZIP headers (they can be altered by an attacker): `total_size = sum(info.file_size for info in my_zip.filelist)`
- Check the archive doesn’t contain too many files: `len(my_zip.filelist) > max_files`
- Check the compression ratio with:
```python
for info in my_zip.filelist:
    if info.compress_size == 0 or info.file_size == 0:
        continue
        
    ratio = info.file_size / info.compress_size
```
- Check for path traversal attempts (done automatically by `extract` and `extractall`):
```python
for info in my_zip.filelist:
    target_path = Path(extract_path) / info.filename
    try:
        target_path.relative_to(extract_path)
    except ValueError as e:
        raise ValueError(f"Attempted path traversal with {info.filename}") from e
```
- Check the actually decompressed size to detect attacks and make sure this size is really under a certains threshold.

```python
extracted_size = 0

for info in my_zip.filelist:
    with my_zip.open(info) as file:
        while chunk := file.read(8*1024):
            extracted_size += len(chunk)
            if extracted_size > max_size:
                raise ValueError(
                    f"Extracted data exceeds maximum size of {max_size} bytes"
                )
```


## Decisions

We’ll only allow articles in raw text for now.
It’s easier to handle correctly, doesn’t need file storage and will fit better in the app.
It will also pave the way to support other formats by forcing the functions to be more generic and handle other formats.

This will be re-opened in the future if needed or if interest for other formats is higher.

## Consequences

- Only plain text is supported right now.
- No need to save files right now.
  So no need to set up something on disk or a bucket to store these files.
  - A bucket is more future-proof, but not needed right now and requires some setup.
  - Saving on disk is easier but requires constraints on the storage.
  - I don’t want to be bothered to migrate files in case of hosting provider or saving backend switch.
  - I’d like things to remain simple for now.
  - [django-storage](https://pypi.org/project/django-storages/) is the library to help do that and allow instance administrators to choose the storage backend.
- No need to bother with the EPUB format, ZIP bomb protection, saving images.
  - This includes writing an EPUB reader or finding a good library that reads EPUB.
- No risk of becoming a file hosting service.
