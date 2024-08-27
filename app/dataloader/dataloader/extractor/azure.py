import html

from azure.ai.formrecognizer import AnalyzeResult
from azure.ai.formrecognizer import DocumentPage
from azure.ai.formrecognizer import DocumentTable
from azure.ai.formrecognizer.aio import DocumentAnalysisClient
from azure.identity.aio import ChainedTokenCredential
from dataloader.base import ClientManager
from dataloader.extractor.models import ExtractorConfig
from dataloader.extractor.models import Page
from dataloader.indexer.models import Document


class DocumentIntelligence(ClientManager):
    def __init__(self, config: ExtractorConfig, credential: ChainedTokenCredential):
        super().__init__(credential)
        self.client = DocumentAnalysisClient(
            endpoint=f"https://{config.service}.cognitiveservices.azure.com/",
            credential=credential,
            headers={"x-ms-useragent": "azure-search-chat/1.0.0"},
        )

    async def extract_pages(self, document: Document) -> list[Page]:
        """Extract the pages from the document."""
        offset = 0
        pages: list[Page] = []
        poller = await self.client.begin_analyze_document("prebuilt-layout", document=document.get_content(bytes))
        results = await poller.result()

        for page_num, page in enumerate(results.pages):
            text = PageProcessor(results).process(page)
            pages.append(Page(document=document.metadata.name, number=page_num, text=text, offset=offset))
            offset += len(text)

        return pages


class PageProcessor:
    """PageProcessor handles the DocumentAnalysis results for a single page."""

    def __init__(self, result: AnalyzeResult):
        self.result = result

    def process(self, page: DocumentPage) -> str:
        """process_page processes the OCR results for a single page."""
        tables = self._extract_tables(page)
        page_offset = page.spans[0].offset
        page_length = page.spans[0].length
        table_chars = self._map_table_characters(tables, page_offset, page_length)

        return self._construct_page_text(tables, table_chars, page_offset)

    def _extract_tables(self, page: DocumentPage) -> list[DocumentTable]:
        """_extract_tables extracts the tables from the result for the given page."""
        return (
            [
                table
                for table in self.result.tables
                if table.bounding_regions and table.bounding_regions[0].page_number == page.page_number
            ]
            if self.result.tables
            else []
        )

    def _map_table_characters(self, tables: list[DocumentTable], page_offset: int, page_length: int) -> list[int]:
        """_map_table_characters maps characters to their respective tables."""
        table_chars = [-1] * page_length
        for table_id, table in enumerate(tables):
            for span in table.spans:
                for i in range(span.length):
                    idx = span.offset - page_offset + i
                    if 0 <= idx < page_length:
                        table_chars[idx] = table_id
        return table_chars

    def _construct_page_text(self, tables: list[DocumentTable], table_chars: list[int], page_offset: int) -> str:
        """_construct_page_text constructs the page text, including HTML tables."""
        text = ""
        added_tables = set()
        for idx, table_id in enumerate(table_chars):
            if table_id == -1:
                text += self.result.content[page_offset + idx]
            elif table_id not in added_tables:
                text += TableProcessor.table_to_html(tables[table_id])
                added_tables.add(table_id)
        return text + " "


class TableProcessor:
    """TableProcessor handles conversion of tables to HTML."""

    @staticmethod
    def table_to_html(table: DocumentTable) -> str:
        """table_to_html converts a DocumentTable to an HTML table."""
        output = "<table>"
        rows = [
            sorted(
                [cell for cell in table.cells if cell.row_index == i],
                key=lambda cell: cell.column_index,
            )
            for i in range(table.row_count)
        ]
        for row_cells in rows:
            output += "<tr>"
            for cell in row_cells:
                if not cell.column_span or not cell.row_span:
                    continue
                tag = "th" if (cell.kind == "columnHeader" or cell.kind == "rowHeader") else "td"
                cell_spans = ""
                if cell.column_span > 1:
                    cell_spans += f" colSpan={cell.column_span}"
                if cell.row_span > 1:
                    cell_spans += f" rowSpan={cell.row_span}"
                output += f"<{tag}{cell_spans}>{html.escape(cell.content)}</{tag}>"
            output += "</tr>"
        output += "</table>"
        return output
