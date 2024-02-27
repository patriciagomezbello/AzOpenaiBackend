from azure.ai.formrecognizer import DocumentAnalysisClient
from pypdf import PdfReader
from .helper import table_to_html


def process_page(page, form_recognizer_results):
    tables_on_page = []
    if form_recognizer_results.tables is not None:
        tables_on_page = [
            table
            for table in form_recognizer_results.tables
            if table.bounding_regions is not None
            and table.bounding_regions[0].page_number == page.page_number
        ]

    page_offset = page.spans[0].offset
    page_length = page.spans[0].length
    table_chars = [-1] * page_length
    for table_id, table in enumerate(tables_on_page):
        for span in table.spans:
            for i in range(span.length):
                idx = span.offset - page_offset + i
                if idx >= 0 and idx < page_length:
                    table_chars[idx] = table_id

    page_text = ""
    added_tables = set()
    for idx, table_id in enumerate(table_chars):
        if table_id == -1:
            page_text += form_recognizer_results.content[page_offset + idx]
        elif table_id not in added_tables:
            page_text += table_to_html(tables_on_page[table_id])
            added_tables.add(table_id)

    page_text += " "
    return page_text


def get_document_text(
    file_path, formrecognizer_creds, formrecognizerservice, localpdf, verbose=False
):
    offset = 0
    page_map = []

    if localpdf:
        reader = PdfReader(file_path)
        pages = reader.pages
        for page_num, p in enumerate(pages):
            page_text = p.extract_text()
            page_map.append((page_num, offset, page_text))
            offset += len(page_text)
    else:
        if verbose:
            print(f"Extracting text from '{file_path}' using Azure Form Recognizer")
        form_recognizer_client = DocumentAnalysisClient(
            endpoint=f"https://{formrecognizerservice}.cognitiveservices.azure.com/",
            credential=formrecognizer_creds,
            headers={"x-ms-useragent": "azure-search-chat/1.0.0"},
        )
        with open(file_path, "rb") as f:
            poller = form_recognizer_client.begin_analyze_document(
                "prebuilt-layout", document=f
            )
        form_recognizer_results = poller.result()

        for page_num, page in enumerate(form_recognizer_results.pages):
            page_text = process_page(page, form_recognizer_results)
            page_map.append((page_num, offset, page_text))
            offset += len(page_text)

    return page_map


def get_document_text_from_blob(
    sas_token, blob_url, formrecognizer_creds, formrecognizerservice, verbose=False
):
    offset = 0
    page_map = []

    if verbose:
        print(f"Extracting text from '{blob_url}' using Azure Form Recognizer")

    form_recognizer_client = DocumentAnalysisClient(
        endpoint=f"https://{formrecognizerservice}.cognitiveservices.azure.com/",
        credential=formrecognizer_creds,
        headers={"x-ms-useragent": "azure-search-chat/1.0.0"},
    )

    blob_sas_url = f"{blob_url}?{sas_token}"

    poller = form_recognizer_client.begin_analyze_document(
        "prebuilt-layout", document=bytes(blob_sas_url, "utf-8")
    )
    form_recognizer_results = poller.result()

    for page_num, page in enumerate(form_recognizer_results.pages):
        page_text = process_page(page, form_recognizer_results)
        page_map.append((page_num, offset, page_text))
        offset += len(page_text)

    return page_map


def split_text(
    page_map,
    file_path,
    section_overlap,
    max_section_length,
    sentence_search_limit,
    verbose=False,
):
    SENTENCE_ENDINGS = [".", "!", "?"]
    WORDS_BREAKS = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]
    if verbose:
        print(f"Splitting '{file_path}' into sections")

    def find_page(offset):
        leng = len(page_map)
        for i in range(leng - 1):
            if offset >= page_map[i][1] and offset < page_map[i + 1][1]:
                return i
        return leng - 1

    for p in page_map:
        # yield (p[2],p[0])

        all_text = p[2]
        length = len(all_text)
        start = 0
        end = length
        while start + section_overlap < length:
            last_word = -1
            end = start + max_section_length

            if end > length:
                end = length
            else:
                # Try to find the end of the sentence
                while (
                    end < length
                    and (end - start - max_section_length) < sentence_search_limit
                    and all_text[end] not in SENTENCE_ENDINGS
                ):
                    if all_text[end] in WORDS_BREAKS:
                        last_word = end
                    end += 1
                if (
                    end < length
                    and all_text[end] not in SENTENCE_ENDINGS
                    and last_word > 0
                ):
                    end = last_word  # Fall back to at least keeping a whole word
            if end < length:
                end += 1

            # Try to find the start of the sentence or at least a whole word boundary
            last_word = -1
            while (
                start > 0
                and start > end - max_section_length - 2 * sentence_search_limit
                and all_text[start] not in SENTENCE_ENDINGS
            ):
                if all_text[start] in WORDS_BREAKS:
                    last_word = start
                start -= 1
            if all_text[start] not in SENTENCE_ENDINGS and last_word > 0:
                start = last_word
            if start > 0:
                start += 1

            section_text = all_text[start:end]
            yield (section_text, p[0])

            last_table_start = section_text.rfind("<table")
            if (
                last_table_start > 2 * sentence_search_limit
                and last_table_start > section_text.rfind("</table")
            ):
                # If the section ends with an unclosed table, we need to start the next section with the table.
                # If table starts inside sentence_search_limit, we ignore it,
                # as that will cause an infinite loop for tables longer than max_section_length
                # If last table starts inside section_overlap, keep overlapping
                if verbose:
                    print(
                        f"Section ends with unclosed table, starting next section with the table at page  \
                            {find_page(start)} offset {start} table start {last_table_start}"
                    )
                start = min(end - section_overlap, start + last_table_start)
            else:
                start = end - section_overlap

        if start + section_overlap < end:
            yield (all_text[start:end], p[0])
