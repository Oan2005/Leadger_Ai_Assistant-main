# Security Note

## Hardcoded Pinecone API key (found and remediated)

The original `vector_database/pinecone_client.py` contained a **live
Pinecone API key hardcoded in plain text**:

```python
pc = Pinecone(api_key="pcsk_...")   # real key, redacted in this document
```

This is a real credential-exposure risk: anyone with read access to the
source (git history included, even if later removed) can use it.

### What was changed

With the project owner's explicit approval, this is the **one deliberate
behavioral deviation** in this reorganization:

- `app/vector_database/pinecone_client.py` now reads the key from the
  `PINECONE_API_KEY` environment variable instead of a literal string.
- A `.env.example` template was added documenting the required variable.
- Everything else in that file (the index name `"hr"`, the
  `describe_index_stats()` call on import, `ServerlessSpec` import) is
  unchanged.

This changes **where the key comes from**, not any runtime behavior of
the Pinecone client or index once the environment variable is set
correctly — functionally identical as long as `PINECONE_API_KEY` is
exported before the app starts (see `docs/ENVIRONMENT.md` /
`docs/SETUP.md`).

### Action required from you

1. **Rotate the key** in the Pinecone dashboard — treat the original key
   as compromised, since it was committed to source.
2. Set `PINECONE_API_KEY` in your deployment environment (or `.env` for
   local dev) to the new key.
3. If this project's history is in git, consider scrubbing the old key
   from git history as well (e.g. with `git filter-repo` or BFG Repo
   Cleaner), since removing it from the current file does not remove it
   from prior commits.
