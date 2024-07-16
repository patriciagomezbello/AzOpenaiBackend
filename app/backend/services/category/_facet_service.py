from typing import List
from typing import Optional

from clients import SearchClient
from services.category._interface import CategoryService
from services.logger import new_logger
from services.schemas import Facets
from services.schemas import SearchOptions
from services.search import SearchService
from services.timer import timer


logger = new_logger(__name__)


class FacetCategoryService(CategoryService):
    """FacetCategoryService provides a service for searching categories."""

    def __init__(self, search_client: SearchClient):
        self.client = search_client

    @timer()
    async def get_categories(self, roles: Optional[List[str]]) -> List[str]:
        """get_categories returns a list of categories."""
        filter = "roles/any(r:search.in(r, 'public'))"
        if roles and len(roles) > 0:
            filter = f"""roles/any(r:search.in(r, 'public, {", ".join(roles)}'))"""
            logger.debug(f"Filtering categories by roles: {roles}")

        facets = await self._search_facets(["category,count:0"], filter=filter)
        return [str(cat["value"]) for cat in facets["category"]]

    @timer()
    async def sync_facets(self, search_svc: SearchService) -> None:
        """sync_facets syncronizes the local facets with the ones in the search index."""
        doclangs = (await self._search_facets(["doclang"], ""))["doclang"]

        search_svc.initialize_search_index(doclangs)

    async def _search_facets(self, facets: List[str], filter: str) -> Facets:
        try:
            facets_search = await self.client.search(
                opts=SearchOptions(
                    top=0,
                    skip=0,
                    query_type="simple",
                    select=[""],
                    search_text="*",
                    search_fields=[],
                    filter=filter,
                    facets=facets,
                    order_by=[""],
                    include_total_count=True,
                ),
            )
            res: Optional[Facets] = await facets_search.get_facets()
            if not res:
                raise ValueError("No facets found")
            return res
        except Exception as e:
            logger.warning("Error while searching categories", {"error": str(e)}, exc_info=True)
            return self._default_facets(facets)

    def _default_facets(self, facets: List[str]) -> Facets:
        """_default_facets returns the default facets."""
        match facets[0]:
            case "category":
                return {"category": []}
            case "doclang":
                return {"doclang": [{"count": 1, "value": "de"}]}
            case _:
                return {facet: [] for facet in facets}
