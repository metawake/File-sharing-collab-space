from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import httpx


@dataclass
class TokenBundle:
    access_token: str
    refresh_token: Optional[str]


class GoogleDriveClient:
    def __init__(
        self, tokens: TokenBundle, client: Optional[httpx.AsyncClient] = None
    ) -> None:
        self.tokens = tokens
        self._client = client or httpx.AsyncClient(timeout=30.0)

    async def _authorized_get(
        self, url: str, *, headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        base_headers = {"Authorization": f"Bearer {self.tokens.access_token}"}
        if headers:
            base_headers.update(headers)
        return await self._client.get(url, headers=base_headers)

    async def _refresh_access_token(self, client_id: str, client_secret: str) -> bool:
        if not self.tokens.refresh_token:
            return False
        resp = await self._client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.tokens.refresh_token,
            },
        )
        if resp.status_code != 200:
            return False
        data = resp.json()
        self.tokens.access_token = data.get("access_token", self.tokens.access_token)
        return True

    async def get_metadata(self, file_id: str) -> Tuple[int, Dict[str, Any]]:
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields=id,name,mimeType,size,md5Checksum"
        resp = await self._authorized_get(url)
        return resp.status_code, (
            resp.json() if resp.status_code == 200 else {"error": resp.text}
        )

    async def download_file(self, file_id: str) -> Tuple[int, bytes, Dict[str, str]]:
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        resp = await self._authorized_get(url)
        return (
            resp.status_code,
            (resp.content if resp.status_code == 200 else b""),
            dict(resp.headers),
        )

    async def get_metadata_with_refresh(
        self, file_id: str, client_id: str, client_secret: str
    ) -> Tuple[int, Dict[str, Any]]:
        status, data = await self.get_metadata(file_id)
        if status == 401 and await self._refresh_access_token(client_id, client_secret):
            status, data = await self.get_metadata(file_id)
        return status, data

    async def download_with_refresh(
        self, file_id: str, client_id: str, client_secret: str
    ) -> Tuple[int, bytes, Dict[str, str]]:
        status, content, headers = await self.download_file(file_id)
        if status == 401 and await self._refresh_access_token(client_id, client_secret):
            status, content, headers = await self.download_file(file_id)
        return status, content, headers

    async def list_files(
        self,
        q: Optional[str] = None,
        page_size: int = 50,
        page_token: Optional[str] = None,
    ) -> httpx.Response:
        params = {
            "pageSize": str(page_size),
            "fields": "nextPageToken, files(id,name,mimeType,size)",
        }
        if q:
            params["q"] = q
        if page_token:
            params["pageToken"] = page_token
        url = "https://www.googleapis.com/drive/v3/files"
        qp = httpx.QueryParams(params)
        return await self._authorized_get(f"{url}?{str(qp)}")

    async def list_with_refresh(
        self,
        client_id: str,
        client_secret: str,
        q: Optional[str] = None,
        page_size: int = 50,
        page_token: Optional[str] = None,
    ) -> Tuple[int, Dict[str, Any]]:
        resp = await self.list_files(q=q, page_size=page_size, page_token=page_token)
        if resp.status_code == 401 and await self._refresh_access_token(
            client_id, client_secret
        ):
            resp = await self.list_files(
                q=q, page_size=page_size, page_token=page_token
            )
        return resp.status_code, (
            resp.json() if resp.status_code == 200 else {"error": resp.text}
        )

    async def aclose(self) -> None:
        await self._client.aclose()
