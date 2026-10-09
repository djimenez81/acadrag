"""Grobid HTTP client.

Wraps the Grobid REST API and returns the raw response body so that
higher layers can decide what to do with it (parse, cache, retry).
"""

from __future__ import annotations

import logging
from pathlib import Path

import requests

log = logging.getLogger(__name__)

DEFAULT_URL = "http://localhost:8070"
DEFAULT_ENDPOINT = "api/processFulltextDocument"


class GrobidError(RuntimeError):
    """Base class for Grobid client errors."""


class GrobidUnavailable(GrobidError):
    """Raised when Grobid cannot be reached or returns a 5xx."""


class GrobidClient:
    """Minimal Grobid HTTP client.

    Args:
        base_url: Root URL of the Grobid server.
        endpoint: Endpoint path (relative to ``base_url``).
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_URL,
        endpoint: str = DEFAULT_ENDPOINT,
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.endpoint = endpoint.strip("/")
        self.timeout = timeout

    def is_available(self, probe_timeout: float = 5.0) -> bool:
        """Return True if Grobid answers a cheap probe request.

        Args:
            probe_timeout: Timeout in seconds for the probe.
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/version",
                timeout=probe_timeout,
            )
            return response.ok
        except requests.RequestException:
            return False

    def process_pdf(self, pdf_path: Path) -> str:
        """Send ``pdf_path`` to Grobid and return the response body.

        Args:
            pdf_path: Path to a PDF file.

        Returns:
            The response body as text (TEI XML for the full-text
            endpoint, BibTeX for the header endpoint).

        Raises:
            GrobidUnavailable: On connection errors or 5xx responses.
            GrobidError: On any other non-2xx response.
        """
        url = f"{self.base_url}/{self.endpoint}"
        try:
            with pdf_path.open("rb") as handle:
                response = requests.post(
                    url,
                    files={
                        "input": (
                            pdf_path.name,
                            handle,
                            "application/pdf",
                        )
                    },
                    timeout=self.timeout,
                )
        except requests.RequestException as exc:
            raise GrobidUnavailable(str(exc)) from exc

        if 500 <= response.status_code < 600:
            raise GrobidUnavailable(
                f"Grobid {response.status_code}: {response.text[:200]}"
            )
        if not response.ok:
            raise GrobidError(
                f"Grobid {response.status_code}: {response.text[:200]}"
            )
        return response.text

    def process_header(self, pdf_path: Path) -> str:
        """Send ``pdf_path`` to Grobid's header endpoint.

        Returns the raw BibTeX response body.

        Raises:
            GrobidUnavailable: On connection errors or 5xx responses.
            GrobidError: On any other non-2xx response.
        """
        url = f"{self.base_url}/api/processHeaderDocument"
        try:
            with pdf_path.open("rb") as handle:
                response = requests.post(
                    url,
                    files={
                        "input": (
                            pdf_path.name,
                            handle,
                            "application/pdf",
                        )
                    },
                    timeout=self.timeout,
                )
        except requests.RequestException as exc:
            raise GrobidUnavailable(str(exc)) from exc

        if 500 <= response.status_code < 600:
            raise GrobidUnavailable(
                f"Grobid {response.status_code}: {response.text[:200]}"
            )
        if not response.ok:
            raise GrobidError(
                f"Grobid {response.status_code}: {response.text[:200]}"
            )
        return response.text
