"""
clean_text
==========

Lightweight text-cleaning helper applied to each chunk immediately
before it is stored, as used by `app.chunking.Parse_Documents`.
"""

import string


def clean_records(text_to_clean: str) -> str:
    """
    Clean a chunk of text before it is stored in the final chunk object.

    Lowercases every character and strips out asterisk characters.
    (Existing behavior — the `puncuations` variable is currently
    unused by the filtering logic below; preserved as-is.)

    Args:
        text (str): Raw chunk text.

    Returns:
        str: Cleaned, lowercased text with `*` characters removed.
    """
    puncuations = string.punctuation
    fix = [char.lower() for char in text_to_clean if char not in "" and char not in "*"]
    return "".join(fix)
