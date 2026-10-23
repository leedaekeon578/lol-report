import time
from collections.abc import Callable, Iterator

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import load_api_key
from app.report import build_report
from app.riot_client import RiotClient

router = APIRouter(prefix="/api")


class ReportRequest(BaseModel):
    riot_id: str


class Summary(BaseModel):
    games: int
    wins: int
    losses: int
    win_rate: float | None


class Game(BaseModel):
    match_id: str
    champion: str
    win: bool
    started_at: str


class ReportResponse(BaseModel):
    summary: Summary
    games: list[Game]
    searched_matches: int
    rift_matches: int
    incomplete: bool
    incomplete_message: str | None


def get_riot_client() -> Iterator[RiotClient]:
    api_key = load_api_key()
    with httpx.Client(timeout=10.0) as http:
        yield RiotClient(api_key, http)


def get_sleep() -> Callable[[float], None]:
    return time.sleep


@router.post("/report", response_model=ReportResponse)
def create_report(
    body: ReportRequest,
    riot: RiotClient = Depends(get_riot_client),
    sleep: Callable[[float], None] = Depends(get_sleep),
) -> dict:
    return build_report(riot, body.riot_id, sleep=sleep)
