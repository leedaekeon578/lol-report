from urllib.parse import quote

import httpx

from app.config import ApiKey
from app.errors import (
    AccountNotFound,
    AppError,
    KeyExpired,
    OtherError,
    RateLimited,
)

# 경로와 호스트는 probe 에서 응답이 확인된 값이다 (공식 문서 대조 전).
HOST = "https://asia.api.riotgames.com"
USER_AGENT = "lol-report/0.1"


class RiotClient:
    """Riot API 호출 3종. 실패는 AppError 로만 밖에 알리고 원문 예외·응답 본문은 버린다."""

    def __init__(self, api_key: ApiKey, http: httpx.Client) -> None:
        self._api_key = api_key
        self._http = http

    def _get(self, path: str, not_found: AppError | None = None):
        # 키는 헤더로만 보낸다. URL 에는 넣지 않는다.
        headers = {
            "X-Riot-Token": self._api_key.reveal(),
            "User-Agent": USER_AGENT,
        }
        try:
            response = self._http.get(HOST + path, headers=headers)
        except httpx.HTTPError:
            raise OtherError() from None

        status = response.status_code
        if status == 200:
            try:
                return response.json()
            except ValueError:
                raise OtherError() from None
        if status == 429:
            raise RateLimited()
        if status in (401, 403):
            raise KeyExpired()
        if status == 404 and not_found is not None:
            raise not_found
        raise OtherError()

    def get_puuid(self, game_name: str, tag_line: str) -> str:
        data = self._get(
            "/riot/account/v1/accounts/by-riot-id/"
            f"{quote(game_name, safe='')}/{quote(tag_line, safe='')}",
            not_found=AccountNotFound(),
        )
        try:
            return data["puuid"]
        except (KeyError, TypeError):
            raise OtherError() from None

    def get_match_ids(self, puuid: str, count: int) -> list[str]:
        data = self._get(
            f"/lol/match/v5/matches/by-puuid/{quote(puuid, safe='')}/ids"
            f"?start=0&count={count}"
        )
        if not isinstance(data, list):
            raise OtherError()
        return data

    def get_match(self, match_id: str) -> dict:
        data = self._get(f"/lol/match/v5/matches/{quote(match_id, safe='')}")
        if not isinstance(data, dict):
            raise OtherError()
        return data
