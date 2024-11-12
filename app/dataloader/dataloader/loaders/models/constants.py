from dataloader.loaders.base import WebDocumentLoader
from dataloader.loaders.langchain import LangchainLoader
from dataloader.loaders.llamaindex import JiraLoader
from dataloader.loaders.magentainfos import MagentaInfosLoader
from dataloader.loaders.models.webloader import LoaderName
from dataloader.loaders.staffbase import StaffbaseLoader

WEBLOADER_REGISTRY: dict[LoaderName, type[WebDocumentLoader]] = {
    LoaderName.DOCUSAURUS: LangchainLoader,
    LoaderName.CONFLUENCE: LangchainLoader,
    LoaderName.WEBSITE: LangchainLoader,
    LoaderName.GIT: LangchainLoader,
    LoaderName.MAGENTAINFOS: MagentaInfosLoader,
    LoaderName.STAFFBASE: StaffbaseLoader,
    LoaderName.JIRA: JiraLoader,
}
