from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from overstats.src.client.apiclient import DashenAPIClient
    from overstats.src.modules.errors import ModuleError
    from overstats.src.modules.bnet_search import BnetSearchModule, BnetSearchResult, bnet_search_module
except ModuleNotFoundError:
    from src.client.apiclient import DashenAPIClient
    from src.modules.errors import ModuleError
    from src.modules.bnet_search import BnetSearchModule, BnetSearchResult, bnet_search_module

from .render import RenderedImage, render_match_detail, render_match_list
from .requests import DashenMatchDetail, DashenMatchQuery, DashenMatchRequests


@dataclass(frozen=True)
class DashenMatchListOutput:
    matches: List[Dict[str, Any]]
    customer_token: str
    resolved_bnet: Optional[BnetSearchResult] = None
    image: Optional[RenderedImage] = None


@dataclass(frozen=True)
class DashenMatchDetailOutput:
    detail: DashenMatchDetail
    customer_token: str
    resolved_bnet: Optional[BnetSearchResult] = None
    image: Optional[RenderedImage] = None


class DashenMatchModule:
    def __init__(
        self,
        api_client: Optional[DashenAPIClient] = None,
        search_module: Optional[BnetSearchModule] = None,
    ) -> None:
        self.requests = DashenMatchRequests(api_client)
        self.search_module = search_module or bnet_search_module

    async def query_match_list(self, query: DashenMatchQuery, *, render: bool = True) -> DashenMatchListOutput:
        query, resolved_bnet = await self._resolve_query(query)
        matches = await self.requests.list_recent_matches(query)
        full_id = resolved_bnet.full_id if resolved_bnet else query.bnet_id
        image = render_match_list(matches, full_id=full_id) if render else None
        return DashenMatchListOutput(
            matches=matches,
            customer_token=query.customer_token,
            resolved_bnet=resolved_bnet,
            image=image,
        )

    async def query_match_detail(
        self,
        customer_token: str,
        match: Dict[str, Any] | str,
        *,
        query_full_id: str = "",
        query_bnet_id: str = "",
        render: bool = True,
    ) -> DashenMatchDetailOutput:
        detail = await self.requests.get_match_detail(customer_token, match)
        image = (
            render_match_detail(
                detail.payload,
                source_match=detail.source_match,
                query_full_id=query_full_id,
                query_bnet_id=query_bnet_id,
            )
            if render
            else None
        )
        return DashenMatchDetailOutput(detail=detail, customer_token=customer_token, image=image)

    async def query_match_detail_by_index(
        self,
        query: DashenMatchQuery,
        index: int,
        *,
        render: bool = True,
    ) -> DashenMatchDetailOutput:
        query, resolved_bnet = await self._resolve_query(query)
        matches = await self.requests.list_recent_matches(query)
        if index < 0 or index >= len(matches):
            raise ModuleError(
                error="match_index_out_of_range",
                message=f"Match index out of range: {index}",
                status_code=400,
                hint=f"Use an index from 0 to {max(len(matches) - 1, 0)}.",
                details={"index": index, "match_count": len(matches)},
            )
        detail = await self.requests.get_match_detail(query.customer_token, matches[index])
        image = (
            render_match_detail(
                detail.payload,
                source_match=detail.source_match,
                query_full_id=resolved_bnet.full_id if resolved_bnet else query.bnet_id,
                query_bnet_id=resolved_bnet.bnet_id if resolved_bnet else "",
            )
            if render
            else None
        )
        return DashenMatchDetailOutput(
            detail=detail,
            customer_token=query.customer_token,
            resolved_bnet=resolved_bnet,
            image=image,
        )

    async def query_match_list_by_bnet_id(
        self,
        bnet_id: str,
        *,
        render: bool = True,
        **query_options: Any,
    ) -> DashenMatchListOutput:
        return await self.query_match_list(DashenMatchQuery(bnet_id=bnet_id, **query_options), render=render)

    async def query_match_detail_by_bnet_id(
        self,
        bnet_id: str,
        index: int,
        *,
        render: bool = True,
        **query_options: Any,
    ) -> DashenMatchDetailOutput:
        return await self.query_match_detail_by_index(
            DashenMatchQuery(bnet_id=bnet_id, **query_options),
            index,
            render=render,
        )

    async def _resolve_query(self, query: DashenMatchQuery) -> tuple[DashenMatchQuery, Optional[BnetSearchResult]]:
        if query.customer_token:
            return query, None
        if not query.bnet_id:
            raise ModuleError(
                error="missing_target",
                message="Missing query target: bnet_id or customer_token is required.",
                status_code=400,
                hint='Example: {"bnet_id":"Player#12345","limit":20}',
            )

        search_output = await self.search_module.search(query.bnet_id, render=False)
        customer_token = search_output.result.customer_token
        if not customer_token:
            payload = search_output.result.payload
            data = payload.get("data") if isinstance(payload, dict) else None
            raise ModuleError(
                error="bnet_not_found",
                message=f"Could not resolve customerToken from bnet_id: {query.bnet_id}",
                status_code=404,
                hint=(
                    "Check exact letter case and the number after '#'. "
                    "Dashen search is often case-sensitive. "
                    "If you already have customer_token, query with customer_token directly."
                ),
                details={
                    "query": search_output.result.query,
                    "upstream_code": payload.get("code") if isinstance(payload, dict) else None,
                    "upstream_msg": payload.get("msg") if isinstance(payload, dict) else None,
                    "has_data": isinstance(data, dict),
                    "has_customer_token": bool(customer_token),
                    "resolved_name": search_output.result.full_id,
                    "resolved_bnet_id": search_output.result.bnet_id,
                },
            )

        resolved_query = DashenMatchQuery(
            customer_token=customer_token,
            bnet_id=search_output.result.full_id,
            seasons=query.seasons,
            include_previous_season=query.include_previous_season,
            include_fight=query.include_fight,
            target_count=query.target_count,
            filters=query.filters,
        )
        return resolved_query, search_output.result


dashen_match_module = DashenMatchModule()
