# Known Issues (Pre-Existing, Intentionally Untouched)

These are quirks/bugs present in the **original** project. Per the
reorganization brief ("do not change any business logic/behavior"),
**none of these were fixed**. They're documented here so they're visible
rather than silently inherited.

## 1. `embedd_chunks` returns a leading empty placeholder

`app/embedding/embedding_model.py::embedd_chunks` initializes
`rag = [{}]` and appends to it, so the returned list always has an empty
dict at index 0. Callers compensate by slicing `[1:]`
(see `api.py`'s `/upload` endpoint and `insert_chunks(embedd_docs[1:])`).
If `embedd_chunks`'s output is ever used elsewhere without the same
slicing convention, this will silently insert a malformed record.

## 2. `extract_pdf` is broken and unused

`app/ingestion/extraction_process.py::extract_pdf` has a bug:
`text += page` appends the `PdfReader` page object (not `content`, the
extracted text) to a string, which would raise a `TypeError` if this
function were ever called. It is **not called anywhere in the active
`/upload` pipeline** — `extract_to_objects` (Docling-based) is used
instead. `extract_txt` and `extract_word` are similarly unused by the
current pipeline but do not have the same bug.

## 3. `clean_text` docstring doesn't match its logic

`app/ingestion/clean_text.py::clean_text` computes
`puncuations = string.punctuation` but never uses that variable. The
actual filtering only removes `*` characters (not all punctuation) and
lowercases the rest.

## 4. `Parse_Doc_for_Rag` has an unused intermediate variable

In `app/chunking/Parse_Documents.py`, the line
`Object_chunk = vectors.append(...)` assigns the (always `None`) return
value of `list.append()` to a variable that is never read. Harmless, but
preserved as-is rather than simplified, per the "no logic changes" rule.

## 5. `/upload` writes files to the current working directory

`api.py`'s `/upload` endpoint saves the uploaded file using
`open(file.filename, "wb")` — the **original client-provided filename**,
written relative to wherever the process's CWD happens to be, with no
path sanitization and no collision handling (concurrent uploads with the
same filename will overwrite each other). This is unchanged from the
original.

## 6. `Dockerfile` has a `WORKDIR` typo

`WORKDIR / app` (note the space) creates/uses a directory literally
named `app` at the filesystem root, rather than `/app`. The container
still builds and runs, since all subsequent Docker instructions are
relative to whatever `WORKDIR` resolves to — but this is almost
certainly not what was intended. See `docs/SETUP.md`.

## 7. `requierments.txt` filename typo

Kept as-is (not renamed to `requirements.txt`) since the `Dockerfile`
explicitly references this exact filename, and renaming it without also
updating the `Dockerfile` would break the build — and updating the
`Dockerfile` reference was outside the scope of "reorganize without
changing functionality" for this pass.
