import re
from typing import List

from api.models.common import DataPoint
from services.citation._interface import CitationService
from services.logger import new_logger
from services.timer import timer


logger = new_logger(__name__)


class RegexCitationService(CitationService):
    """RegexCitationService provides a service for generating citations."""

    @timer()
    def get_citations(self, text: str) -> List[DataPoint]:
        """get_citations extracts citation information from the given text
        and returns a list of citations without duplicates."""
        citations = []
        doc_pattern = re.compile(r"\[(.*?)\]")
        page_pattern = re.compile(r"-([0-9]+)(?:-\d)?\.")

        matches = doc_pattern.findall(text)
        if len(matches) == 0:
            return citations

        for match in matches:
            doc_name = match

            pg_match = page_pattern.search(doc_name)
            page = None
            if pg_match:
                page_val = int(pg_match.group(1)) + 1
                page = page_val

            # Remove additional numbering from document name
            citations.append(DataPoint(docName=re.sub(r"-\d+\.pdf", ".pdf", doc_name), page=page))

        return self.filter_duplicates(citations)

    def filter_duplicates(self, citations: List[DataPoint]) -> List[DataPoint]:
        """filter_duplicates removes duplicate citations from the list."""
        unique: List[DataPoint] = []
        encountered: dict[str, None] = {}

        for citation in citations:
            key = str(citation)
            if key not in encountered:
                encountered[key] = None
                unique.append(citation)

        return unique
