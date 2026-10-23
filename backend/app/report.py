import time
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from app.errors import AppError, InvalidInput, OtherError
from app.riot_client import RiotClient

RIFT_QUEUES = {420, 440}  # D-004: 랭크 솔로, 랭크 자유
TARGET_MATCHES = 20
MAX_MATCHES = 100  # D-005
DETAIL_PAUSE_SECONDS = 0.1  # D-006


def parse_riot_id(raw: str) -> tuple[str, str]:
    """D-003: 앞뒤 공백만 지우고 대소문자는 바꾸지 않는다. 마지막 # 로 나눈다."""
    text = raw.strip()
    if "#" not in text:
        raise InvalidInput()
    game_name, tag_line = text.rsplit("#", 1)
    if not game_name.strip() or not tag_line.strip():
        raise InvalidInput()
    return game_name, tag_line


def win_rate(wins: int, games: int) -> float | None:
    """D-008: 소수점 첫째 자리까지. 게임이 없으면 None."""
    if games == 0:
        return None
    rate = Decimal(wins) * 100 / Decimal(games)
    return float(rate.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _iso_utc(milliseconds: int) -> str:
    moment = datetime.fromtimestamp(milliseconds // 1000, tz=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def read_match(detail: dict, puuid: str, match_id: str) -> tuple[bool, dict | None]:
    """(협곡 큐 여부, 퍼스트블러드 킬 게임이면 목록 항목)을 돌려준다."""
    try:
        info = detail["info"]
        if info["queueId"] not in RIFT_QUEUES:
            return False, None
        me = next((p for p in info["participants"] if p["puuid"] == puuid), None)
        if me is None:
            raise OtherError()
        if me.get("firstBloodKill") is not True:  # D-007
            return True, None
        return True, {
            "match_id": match_id,
            "champion": me["championName"],
            "win": bool(me["win"]),
            "started_at": _iso_utc(info["gameStartTimestamp"]),
        }
    except AppError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError):
        raise OtherError() from None


def build_report(
    riot: RiotClient,
    riot_id: str,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    game_name, tag_line = parse_riot_id(riot_id)
    puuid = riot.get_puuid(game_name, tag_line)
    match_ids = riot.get_match_ids(puuid, MAX_MATCHES)[:MAX_MATCHES]

    games: list[dict] = []
    searched = 0
    rift = 0
    for match_id in match_ids:
        if rift >= TARGET_MATCHES:
            break
        if searched > 0:
            sleep(DETAIL_PAUSE_SECONDS)
        detail = riot.get_match(match_id)
        searched += 1
        is_rift, game = read_match(detail, puuid, match_id)
        if is_rift:
            rift += 1
        if game is not None:
            games.append(game)

    wins = sum(1 for game in games if game["win"])
    incomplete = rift < TARGET_MATCHES
    return {
        "summary": {
            "games": len(games),
            "wins": wins,
            "losses": len(games) - wins,
            "win_rate": win_rate(wins, len(games)),
        },
        "games": games,
        "searched_matches": searched,
        "rift_matches": rift,
        "incomplete": incomplete,
        "incomplete_message": (
            f"협곡 매치를 {TARGET_MATCHES}개 채우지 못했습니다. "
            f"조회한 {searched}개 중 협곡 매치는 {rift}개입니다."
            if incomplete
            else None
        ),
    }
