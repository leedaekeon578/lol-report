"""테스트 공용 도구. 실제 Riot API와 실제 키는 쓰지 않는다."""

import httpx

from app.config import ApiKey
from app.riot_client import RiotClient

DUMMY_KEY = "TEST-DUMMY-KEY-0000"
PUUID = "fake-puuid"


def make_match(
    queue_id: int = 420,
    team_first_blood: bool = True,
    win: bool = True,
    champion: str = "Ahri",
    start_ms: int = 1_700_000_000_000,
    puuid: str = PUUID,
    my_team_id: int = 100,
    opponent_first_blood: bool | None = None,
    my_first_blood_kill: bool = False,
) -> dict:
    """team_first_blood 는 내 팀의 objectives.champion.first 값이다.

    opponent_first_blood 를 생략하면 내 팀 값의 반대로 둔다(두 팀 모두 false 는 둘 다 False 로 지정).
    my_first_blood_kill 은 내 참가자의 개인 firstBloodKill 값으로, 판정에는 쓰이지 않는다.
    """
    opponent_team_id = 200 if my_team_id == 100 else 100
    if opponent_first_blood is None:
        opponent_first_blood = not team_first_blood
    return {
        "info": {
            "queueId": queue_id,
            "gameStartTimestamp": start_ms,
            "participants": [
                {
                    "puuid": "other",
                    "teamId": opponent_team_id,
                    "championName": "Zed",
                    "win": not win,
                },
                {
                    "puuid": puuid,
                    "teamId": my_team_id,
                    "championName": champion,
                    "win": win,
                    "firstBloodKill": my_first_blood_kill,
                },
            ],
            "teams": [
                {
                    "teamId": my_team_id,
                    "objectives": {"champion": {"first": team_first_blood}},
                },
                {
                    "teamId": opponent_team_id,
                    "objectives": {"champion": {"first": opponent_first_blood}},
                },
            ],
        }
    }


class FakeRiot:
    """httpx.MockTransport 로 Riot 응답을 흉내 낸다. 값이 int 이면 그 상태 코드로 응답한다."""

    def __init__(self, ids=None, matches=None, account=200, ids_status=200):
        self.ids = ids if ids is not None else []
        self.matches = matches or {}
        self.account = account
        self.ids_status = ids_status
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path.startswith("/riot/account/"):
            if self.account != 200:
                return httpx.Response(self.account)
            return httpx.Response(200, json={"puuid": PUUID})
        if "/by-puuid/" in path:
            if self.ids_status != 200:
                return httpx.Response(self.ids_status)
            return httpx.Response(200, json=self.ids)
        match_id = path.rsplit("/", 1)[-1]
        value = self.matches.get(match_id, 404)
        if isinstance(value, Exception):
            raise value
        if isinstance(value, int):
            return httpx.Response(value)
        return httpx.Response(200, json=value)

    def match_requests(self) -> list[httpx.Request]:
        return [r for r in self.requests if "/by-puuid/" not in r.url.path
                and not r.url.path.startswith("/riot/account/")]

    def client(self) -> RiotClient:
        http = httpx.Client(transport=httpx.MockTransport(self.handler))
        return RiotClient(ApiKey(DUMMY_KEY), http)
