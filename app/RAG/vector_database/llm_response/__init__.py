"""
llm_response
============

Generates final natural-language answers by forwarding retrieved
context (or greetings) to an external n8n webhook workflow, which
runs the actual LLM call.

Modules:
    - LLM: `LLM_response`, `LLM_response_greeting`.

Note on folder naming: this sub-package was originally named
`LLM_Response` (mixed case). It has been renamed to `llm_response`
(lowercase, PEP 8-style) purely for organizational consistency with
the rest of the codebase's package names. All import paths have been
updated accordingly — see docs/MIGRATION_NOTES.md.
"""
