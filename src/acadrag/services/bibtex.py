"""Parse Grobid's BibTeX header response.

Grobid's ``processHeaderDocument`` returns a single BibTeX entry. We
extract only the fields we store; if the entry has no usable title,
we return None so the caller can flag the document for review.
"""

from __future__ import annotations

import logging
import re

import bibtexparser
from bibtexparser.bparser import BibTexParser

log = logging.getLogger(__name__)


def _first_year(text: str) -> int | None:
    """Return the first 4-digit year found in ``text``, or None."""
    match = re.search(r"\b(\d{4})\b", text)
    return int(match.group(1)) if match else None


def _split_authors(raw: str) -> list[str]:
    """Split a BibTeX author field on ' and ' into a list."""
    return [a.strip() for a in raw.split(" and ") if a.strip()]


def parse_bibtex(text: str) -> dict | None:
    """Parse a Grobid BibTeX response into a metadata dict.

    Args:
        text: Raw BibTeX text from Grobid.

    Returns:
        A dict with keys ``title``, ``authors``, ``year``, ``venue``,
        ``doi``, ``arxiv_id``, ``abstract``, ``raw_bibtex``. Returns
        ``None`` if no usable entry (title missing) is found.
    """
    if not text or not text.strip():
        return None

    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False
    parser.homogenize_fields = False

    try:
        db = bibtexparser.loads(text, parser=parser)
    except Exception as exc:
        log.warning("Could not parse BibTeX: %s", exc)
        return None

    if not db.entries:
        return None
    entry = db.entries[0]

    title = (entry.get("title") or "").strip()
    if not title:
        return None

    year = _first_year(
        (entry.get("year") or entry.get("date") or "").strip()
    )

    return {
        "title": title,
        "authors": _split_authors(entry.get("author") or ""),
        "year": year,
        "venue": (entry.get("journal")
                  or entry.get("booktitle")
                  or "").strip() or None,
        "doi": (entry.get("doi") or "").strip() or None,
        "arxiv_id": (entry.get("eprint") or "").strip() or None,
        "abstract": (entry.get("abstract") or "").strip() or None,
        "raw_bibtex": text,
    }
