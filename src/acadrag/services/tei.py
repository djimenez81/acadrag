"""Parse Grobid TEI XML: extract references as plain dicts.

Deliberately conservative: if a field cannot be extracted, it is left
absent rather than guessed. The raw ``<biblStruct>`` text is preserved
in every record so nothing is lost.
"""

# TODO(stage2.1): expose a `quality` estimate per parsed reference
# so the repository can persist it without re-parsing TEI.

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def _text_or_none(elem) -> str | None:
    """Return stripped text of ``elem`` or ``None`` if empty/missing."""
    if elem is None:
        return None
    text = "".join(elem.itertext()).strip()
    return text or None


def _parse_authors(bibl: ET.Element) -> list[str]:
    """Extract author names from a ``<biblStruct>`` element."""
    names: list[str] = []
    for author in bibl.findall(".//tei:author", _NS):
        pers = author.find(".//tei:persName", _NS)
        if pers is None:
            continue
        forenames = [
            t.text for t in pers.findall("tei:forename", _NS) if t.text
        ]
        surname = pers.find("tei:surname", _NS)
        parts = forenames + ([surname.text] if surname is not None
                             and surname.text else [])
        if parts:
            names.append(" ".join(parts))
    return names


def _parse_one(bibl: ET.Element) -> dict[str, Any]:
    """Convert one ``<biblStruct>`` into a plain dict."""
    title = _text_or_none(bibl.find(".//tei:title[@level='a']", _NS))
    if title is None:
        title = _text_or_none(bibl.find(".//tei:title", _NS))

    year = None
    date = bibl.find(".//tei:date", _NS)
    if date is not None:
        when = date.get("when")
        if when:
            match = re.match(r"(\d{4})", when)
            if match:
                year = int(match.group(1))
        else:
            year = _text_or_none(date)  # type: ignore[assignment]

    venue = _text_or_none(bibl.find(".//tei:title[@level='j']", _NS))
    if venue is None:
        venue = _text_or_none(bibl.find(".//tei:monogr/tei:title", _NS))

    doi = None
    idno = bibl.find(".//tei:idno[@type='DOI']", _NS)
    if idno is not None:
        doi = _text_or_none(idno)

    arxiv = None
    for idno in bibl.findall(".//tei:idno", _NS):
        if idno.get("type") == "arXiv":
            arxiv = _text_or_none(idno)
            break

    return {
        "title": title,
        "authors": _parse_authors(bibl),
        "year": year,
        "venue": venue,
        "doi": doi,
        "arxiv_id": arxiv,
        "raw": _text_or_none(bibl),
    }


def parse_references(tei_xml: str) -> list[dict[str, Any]]:
    """Extract all references from Grobid TEI XML.

    Args:
        tei_xml: The raw TEI XML returned by Grobid.

    Returns:
        A list of reference dicts (possibly empty).
    """
    if not tei_xml.strip():
        return []
    try:
        root = ET.fromstring(tei_xml)
    except ET.ParseError:
        return []
    return [_parse_one(b) for b in root.findall(".//tei:biblStruct", _NS)]
