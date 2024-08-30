import pytest
from azure.identity.aio import AzureDeveloperCliCredential
from azure.identity.aio import ChainedTokenCredential
from dataloader.extractor.models import Page
from dataloader.indexer.index import DocumentChunker
from dataloader.indexer.models import ChunkerConfig
from dataloader.indexer.models import TextSplitter

samples = [
    (
        "This is a test document. It has multiple sentences. And it spans one page. And it has tables, like "
        "<table><tr><td>Table data 1</td><td>Table data 2</td></tr></table>. I would like to keep the table."
    ),
    (
        "Also several tables can be in the same page. <table>Table 1</table>. And some text can be beeteen of them."
        "Really a lot of text.Really a lot of text.Really a lot of text.Really a lot of text.Really a lot of text."
        " <table>Table 2</table> <table>Table 3</table> <table>Table 4</table>"
    ),
    (
        "<table> Have you ever seen a long table?"
        "I am a long table. I am a long table. I am a long table. I am a long table. I am a long table. "
        "I am a long table. I am a long table. I am a long table. I am a long table. I am a long table. "
        "I am a long table. I am a long table. I am a long table. I am a long table. I am a long table. "
        "I am a long table. I am a long table. I am a long table. I am a long table. I am a long table. "
        "I am a long table. I am a long table. I am a long table. I am a long table. I am a long table. "
        "I am a long table. I am a long table. I am a long table. I am a long table. I am a long table. "
        "I am a long table. I am a long table. I am a long table. I am a long table. I am a long table. "
        "I am a long table. I am a long table. I am a long table. I am a long table. I am a long table. "
        "I am a long table. I am a long table. I am a long table. I am a long table. I am a long table. "
        "I am a long table. I am a long table. I am a long table. I am a long table. I am a long table. "
        "I am a long table. I am a long table. I am a long table. I am a long table. I am a long table. "
        "I am a long table. I am a long table. I am a long table. I am a long table. I am a long table. "
        "I am a long table. I am a long table. I am a long table. I am a long table. I am a long table. "
        "I am a long table. I am a long table. I am a long table. I am a long table. I am a long table. "
        "I am a long table. I am a long table. I am a long table. I am a long table. I am a long table.</table>"
    ),
    "And it works with data that doesn`t have any tables.",
]


def get_chunker(splitter):
    config = ChunkerConfig(service="test", model="test", timeout=30.0, splitter=splitter)
    credential = ChainedTokenCredential(AzureDeveloperCliCredential())
    return DocumentChunker(config, credential)


@pytest.fixture(params=[splitter for splitter in TextSplitter])
def all_chunkers(request):
    return get_chunker(request.param)


@pytest.mark.parametrize("text", samples)
def test_splitters_interface(text: str, all_chunkers):
    """Test that the splitter interface works in the same way for all splitters"""
    page = Page(text=text, document="", number=1, offset=None)
    splitter = all_chunkers.get_splitter()
    for section in splitter(page, max_section_length=10, section_overlap=2):
        assert isinstance(section, str)
        assert len(section) > 1


@pytest.mark.parametrize("text", samples)
def test_dynamic_splitter(text):
    """Test that the dynamic splitter works with tables data as intended"""
    page = Page(text=text, document="", number=1, offset=None)
    splitter = get_chunker(TextSplitter.DYNAMIC).get_splitter()
    tables_sections = 0
    tables_in_page = text.count("<table>")
    for section in splitter(page, max_section_length=10, section_overlap=2):
        print(section)
        assert section.count("<table>") == section.count("</table>")  # table isn't broken
        tables_sections += section.count("<table>")
        print(section)
    assert tables_sections == tables_in_page
