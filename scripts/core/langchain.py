import os
from typing import Callable
from typing import Dict
from typing import Generator
from typing import List

from bs4 import BeautifulSoup as Soup
from langchain_community.document_loaders import ConfluenceLoader
from langchain_community.document_loaders import DocusaurusLoader
from langchain_community.document_loaders import GitLoader
from langchain_community.document_loaders import RecursiveUrlLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .custom_loaders.loaders import custom_load_magentainfos
from .custom_loaders.loaders import custom_load_staffbase
from .custom_loaders.loaders import get_magentainfos_map
from .custom_loaders.loaders import get_staffbase_map


def lc_load_url_docs(url: str, max_depth=2):
    url = url
    loader = RecursiveUrlLoader(url=url, max_depth=max_depth, extractor=lambda x: Soup(x, "html.parser").text)
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
    return documents


def lc_load_confluence_docs(
    url: str,
    username: str,
    token_ref: str,
    space_key: str,
    include_att=False,
    limit=50,
    max_pages=50,
    show_restricted_content=False,
) -> List[Document]:

    token = os.getenv(token_ref)

    if not token:
        raise ValueError("Token for ConfluenceLoader is not set in Environment")

    if username.lower() == "token":
        print("using token only")
        loader = ConfluenceLoader(
            url=url,
            token=token,
            space_key=space_key,
            include_attachments=include_att,
            limit=limit,
            max_pages=max_pages,
            include_restricted_content=show_restricted_content,
        )
    else:
        print("using username and api_token")
        loader = ConfluenceLoader(
            url=url,
            username=username,
            api_key=token,
            space_key=space_key,
            include_attachments=include_att,
            limit=limit,
            max_pages=max_pages,
            include_restricted_content=show_restricted_content,
        )
    documents = loader.load()
    return documents


def lc_load_git_docs(url: str, path: str, file_suffix: str | None):
    if file_suffix is not None and file_suffix != "":
        loader = GitLoader(
            clone_url=url,
            repo_path=path,
            file_filter=lambda file_path: file_path.endswith(file_suffix),
        )
    else:
        loader = GitLoader(
            clone_url=url,
            repo_path=path,
        )

    documents = loader.load()
    return documents


# loaders from langchain community that are loaded via langchain loading process
loader_map: Dict[str, Callable] = {
    "confluence": lc_load_confluence_docs,
    "docusaurus": lc_load_docusaurus_docs,
    "git": lc_load_git_docs,
    "rurl": lc_load_url_docs,
}

# custom loaders, that are loaded via langchain loading process
custom_loader_map: Dict[str, Callable] = {
    "staffbase": custom_load_staffbase,
    "magentainfos": custom_load_magentainfos,
}


def handle_lc_config_item(config_item: dict) -> list[tuple[str, str, str]] | int:
    if config_item["loader"] in loader_map:
        try:
            documents = loader_map[config_item["loader"]](**config_item["config"])
            base = config_item["config"]["url"]
            if config_item["loader"] == "confluence":
                base += f'/display/{config_item["config"]["space_key"]}'
            lc_map = get_langchain_map(documents=documents, base=base)
            return lc_map
        except Exception as e:
            print(e)
            print(f"no valid config for {config_item['loader']}, checking custom loaders...")
            return []
    elif config_item["loader"] in custom_loader_map:
        try:
            map = []
            documents = custom_loader_map[config_item["loader"]](**config_item["config"])
            base = config_item["config"]["url"]
            if config_item["loader"] == "staffbase":
                map = get_staffbase_map(posts=documents, base=base)
            elif config_item["loader"] == "magentainfos":
                map = get_magentainfos_map(documents=documents, base=base)
            return map
        except Exception as e:
            print(e)
            print(f"no valid custom config for {config_item['loader']}, please check docs")
            return []
    else:
        print(f"no valid loader found for {config_item['loader']}, please check docs")
        return []


def get_langchain_map(documents: List[Document], base: str):
    document_map: List[tuple[str, str, str]] = []

    for _, document in enumerate(documents):

        document_text = document.page_content
        document_source = document.metadata["source"]
        document_map.append((document_source, base, document_text))
    return document_map


def split_langchain_text_recursive(
    document_map: List[tuple[str, str, str]], section_overlap=100, max_section_length=1100
) -> Generator[tuple[str, str, str], None, None]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_section_length,
        chunk_overlap=section_overlap,
    )

    for val in document_map:
        s_text = splitter.split_text(val[2])
        for text in s_text:
            yield (val[0], val[1], text)


def split_langchain_text(
    document_map: list[tuple[str, str, str]],
    section_overlap: int,
    max_section_length: int,
    sentence_search_limit: int,
) -> Generator[tuple[str, str, str], None, None]:
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
                if end < length and all_text[end] not in SENTENCE_ENDINGS and last_word > 0:
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
            if last_table_start > 2 * sentence_search_limit and last_table_start > section_text.rfind("</table"):
                # If the section ends with an unclosed table, we need to start the next section with the table.
                # If table starts inside sentence_search_limit, we ignore it,
                # as that will cause an infinite loop for tables longer than max_section_length
                # If last table starts inside section_overlap, keep overlapping
                start = min(end - section_overlap, start + last_table_start)
            else:
                start = end - section_overlap

        if start + section_overlap < end:
            yield (p[0], p[1], all_text[start:end])
