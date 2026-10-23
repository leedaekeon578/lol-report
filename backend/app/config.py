from pathlib import Path

from dotenv import dotenv_values

from app.errors import OtherError

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class ApiKey:
    """Riot API 키를 담는 객체. 출력·문자열화에서는 값을 가린다."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "ApiKey(***)"

    __str__ = __repr__


def load_api_key(env_path: Path = ENV_PATH) -> ApiKey:
    value = (dotenv_values(env_path).get("RIOT_API_KEY") or "").strip()
    if not value:
        # 오류에는 변수 이름 외에 아무것도 담지 않는다.
        raise OtherError(status_code=500) from None
    return ApiKey(value)
