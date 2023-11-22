from langchain.document_loaders import (
    ConfluenceLoader,
    DocusaurusLoader,
    RecursiveUrlLoader,
)
from bs4 import BeautifulSoup as Soup


def lc_load_url_docs(url, max_depth=2):
    url = url
    loader = RecursiveUrlLoader(
        url=url, max_depth=max_depth, extractor=lambda x: Soup(x, "html.parser").text
    )
    documents = loader.load()
    return documents


def lc_load_docusaurus_docs(url, filter_url):
    loader = DocusaurusLoader(
        url,
        filter_urls=[filter_url],
        # This will only include the content that matches these tags, otherwise they will be removed
        custom_html_tags=["#content", ".main"],
    )
    documents = loader.load()
    return documents


def lc_load_confluence_docs(
    url, token, include_attachments=False, limit=50, max_pages=50
):
    loader = ConfluenceLoader(url=url, token=token)
    documents = loader.load(
        space_key="openjpa",
        include_attachments=include_attachments,
        limit=limit,
        max_pages=max_pages,
    )
    return documents


def get_langchain_map(documents):
    document_map = []

    for i, document in enumerate(documents):
        # mark all positions of the table spans in the page

        # build page text by replacing charcters in table spans with table html
        document_text = document.page_content
        document_title = document.metadata["title"]
        document_source = document.metadata["source"]

        document_map.append(
            {"source": document_source, "title": document_title, "text": document_text}
        )
    return document_map


def split_langchain_text(
    document_map, section_overlap, max_section_length, sentence_search_limit
):
    SENTENCE_ENDINGS = [".", "!", "?"]
    WORDS_BREAKS = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]

    for p in document_map:
        all_text = p.text
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
            yield (section_text, p.source, p.title)

        if start + section_overlap < end:
            yield (all_text[start:end], p.source, p.title)
