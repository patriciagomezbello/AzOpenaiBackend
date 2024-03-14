from langchain_community.document_loaders import (
    ConfluenceLoader,
    DocusaurusLoader,
    RecursiveUrlLoader,
    GitLoader,
)
from bs4 import BeautifulSoup as Soup
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter


def lc_load_url_docs(url, max_depth=2):
    url = url
    loader = RecursiveUrlLoader(
        url=url, max_depth=max_depth, extractor=lambda x: Soup(x, "html.parser").text
    )
    documents = loader.load()
    return documents


def lc_load_docusaurus_docs(url):

    loader = DocusaurusLoader(
        url,
        # filter_urls=[filter_url],
        # # This will only include the content that matches these tags, otherwise they will be removed
        # custom_html_tags=["#content", ".main"],
    )
    documents = loader.load()
    print(documents)
    return documents


def lc_load_confluence_docs(
    url, username, token_ref, space_key, include_att=False, limit=50, max_pages=50
):
    token = os.getenv(token_ref)
    loader = ConfluenceLoader(url=url, username=username, api_key=token)
    documents = loader.load(
        space_key=space_key,
        include_attachments=include_att,
        limit=limit,
        max_pages=max_pages,
    )
    return documents


def lc_load_git_docs(url, path, filter):
    if filter != "" or filter is not None:
        loader = GitLoader(
            clone_url=url,
            repo_path=path,
            file_filter=lambda file_path: file_path.endswith(filter),
        )
    else:
        loader = GitLoader(
            clone_url=url,
            repo_path=path,
        )

    documents = loader.load()
    return documents


loader_map = {
    "confluence": lc_load_confluence_docs,
    "docusaurus": lc_load_docusaurus_docs,
    "git": lc_load_git_docs,
    "rurl": lc_load_url_docs,
}


def handle_lc_config_item(config_item):
    try:
        documents = loader_map[config_item["loader"]](**config_item["config"])
        base = config_item["config"]["url"]
        if config_item["loader"] == "confluence":
            base += f'/display/{config_item["config"]["space_key"]}'
        lc_map = get_langchain_map(documents=documents, base=base)
        return lc_map
    except Exception as e:
        print(e)
        print(f"no valid config for {config_item['loader']}, please check docs")
        return -1


# TODO: baselink for deletion
def get_langchain_map(documents, base):
    document_map = []

    for i, document in enumerate(documents):
        # mark all positions of the table spans in the page

        # build page text by replacing charcters in table spans with table html
        document_text = document.page_content
        document_source = document.metadata["source"]
        document_base = base

        document_map.append((document_source, document_base, document_text))
    return document_map


def split_langchain_text_recursive(
    document_map, section_overlap=100, max_section_length=1100
):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_section_length,
        chunk_overlap=section_overlap,
    )

    for val in document_map:
        s_text = splitter.split_text(val[2])
        for text in s_text:
            yield (val[0], val[1], text)


def split_langchain_text(
    document_map,
    section_overlap,
    max_section_length,
    sentence_search_limit,
):
    SENTENCE_ENDINGS = [".", "!", "?"]
    WORDS_BREAKS = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]

    for p in document_map:
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
            yield (p[0], p[1], section_text)

            last_table_start = section_text.rfind("<table")
            if (
                last_table_start > 2 * sentence_search_limit
                and last_table_start > section_text.rfind("</table")
            ):
                # If the section ends with an unclosed table, we need to start the next section with the table.
                # If table starts inside sentence_search_limit, we ignore it,
                # as that will cause an infinite loop for tables longer than max_section_length
                # If last table starts inside section_overlap, keep overlapping
                start = min(end - section_overlap, start + last_table_start)
            else:
                start = end - section_overlap

        if start + section_overlap < end:
            yield (p[0], p[1], all_text[start:end])
