from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from common.schema import normalize_arxiv_id


class ArxivClient:
    base_url = "https://export.arxiv.org/api/query"

    def normalize_arxiv_id(self, value: str | None) -> str | None:
        return normalize_arxiv_id(value)

    def build_pdf_url(self, arxiv_id: str) -> str:
        clean = normalize_arxiv_id(arxiv_id) or arxiv_id
        return f"https://arxiv.org/pdf/{clean}.pdf"

    def get_metadata(self, arxiv_id: str) -> dict[str, Any] | None:
        clean = normalize_arxiv_id(arxiv_id)
        if not clean:
            return None
        try:
            with urlopen(f"{self.base_url}?{urlencode({'id_list': clean})}", timeout=20) as response:
                root = ET.fromstring(response.read())
        except Exception:
            return None
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entry = root.find("a:entry", ns)
        if entry is None:
            return None
        title = re.sub(r"\s+", " ", (entry.findtext("a:title", default="", namespaces=ns))).strip()
        return {"arxiv_id": clean, "title": title, "pdf_url": self.build_pdf_url(clean), "source": "arxiv"}
