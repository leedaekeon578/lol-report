import logging
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.api import get_riot_client, get_sleep
from app.config import ApiKey, load_api_key
from app.errors import AppError
from app.main import app
from tests import DUMMY_KEY, FakeRiot, make_match

MESSAGES = {
    "ACCOUNT_NOT_FOUND": "해당 닉네임#태그의 계정을 찾을 수 없습니다.",
    "RATE_LIMITED": "Riot API 호출 한도를 넘어 조회를 멈췄습니다. 잠시 후 다시 시도해 주세요.",
    "KEY_EXPIRED": "Riot API 키가 만료되었거나 유효하지 않습니다. 서버 키를 갱신해야 합니다.",
    "OTHER_ERROR": "조회 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    "INVALID_INPUT": "닉네임#태그 형식으로 입력해 주세요.",
}


class ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.lines: list[str] = []

    def emit(self, record):
        self.lines.append(self.format(record))


class ApiTestBase(unittest.TestCase):
    def setUp(self):
        self.sleeps: list[float] = []
        self.client = TestClient(app, raise_server_exceptions=False)
        app.dependency_overrides[get_sleep] = lambda: self.sleeps.append
        self.log_handler = ListHandler()
        self.root = logging.getLogger()
        self.old_level = self.root.level
        self.root.setLevel(logging.DEBUG)
        self.root.addHandler(self.log_handler)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.root.removeHandler(self.log_handler)
        self.root.setLevel(self.old_level)

    def use(self, fake: FakeRiot):
        app.dependency_overrides[get_riot_client] = fake.client

    def post(self, riot_id="Name#KR1"):
        return self.client.post("/api/report", json={"riot_id": riot_id})

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status)
        self.assertEqual(
            response.json(), {"error": {"code": code, "message": MESSAGES[code]}}
        )


class SuccessTest(ApiTestBase):
    def test_response_shape(self):
        ids = ["KR_1", "KR_2", "KR_3"]
        self.use(
            FakeRiot(
                ids=ids,
                matches={
                    "KR_1": make_match(win=True, champion="Ahri"),
                    "KR_2": make_match(win=False, champion="Zed"),
                    "KR_3": make_match(first_blood=False),
                },
            )
        )
        response = self.post()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            set(body),
            {
                "summary",
                "games",
                "searched_matches",
                "rift_matches",
                "incomplete",
                "incomplete_message",
            },
        )
        self.assertEqual(
            body["summary"], {"games": 2, "wins": 1, "losses": 1, "win_rate": 50.0}
        )
        self.assertEqual(
            body["games"][0],
            {
                "match_id": "KR_1",
                "champion": "Ahri",
                "win": True,
                "started_at": "2023-11-14T22:13:20Z",
            },
        )
        self.assertEqual(body["searched_matches"], 3)
        self.assertEqual(body["rift_matches"], 3)
        self.assertTrue(body["incomplete"])


class ErrorTest(ApiTestBase):
    def test_account_not_found(self):
        self.use(FakeRiot(account=404))
        self.assert_error(self.post(), 404, "ACCOUNT_NOT_FOUND")

    def test_rate_limited(self):
        self.use(FakeRiot(account=429))
        self.assert_error(self.post(), 429, "RATE_LIMITED")

    def test_rate_limited_on_detail(self):
        self.use(FakeRiot(ids=["KR_1"], matches={"KR_1": 429}))
        self.assert_error(self.post(), 429, "RATE_LIMITED")

    def test_key_expired(self):
        for status in (401, 403):
            with self.subTest(status=status):
                self.use(FakeRiot(account=status))
                self.assert_error(self.post(), 502, "KEY_EXPIRED")

    def test_other_error(self):
        self.use(FakeRiot(account=500))
        self.assert_error(self.post(), 502, "OTHER_ERROR")
        self.use(FakeRiot(ids=["KR_1"], matches={"KR_1": 404}))
        self.assert_error(self.post(), 502, "OTHER_ERROR")

    def test_invalid_input(self):
        self.use(FakeRiot())
        for raw in ["Name", "#KR1", "Name#", "   "]:
            with self.subTest(raw=raw):
                self.assert_error(self.post(raw), 400, "INVALID_INPUT")

    def test_missing_or_wrong_body_is_invalid_input(self):
        self.use(FakeRiot())
        for payload in [{}, {"riot_id": 123}]:
            with self.subTest(payload=payload):
                response = self.client.post("/api/report", json=payload)
                self.assert_error(response, 400, "INVALID_INPUT")

    def test_unexpected_exception_is_other_error_500(self):
        def broken():
            raise RuntimeError(f"boom {DUMMY_KEY}")

        app.dependency_overrides[get_riot_client] = broken
        self.assert_error(self.post(), 500, "OTHER_ERROR")


class KeyLeakTest(ApiTestBase):
    def collect_responses(self):
        scenarios = [
            FakeRiot(ids=["KR_1"], matches={"KR_1": make_match()}),
            FakeRiot(account=404),
            FakeRiot(account=429),
            FakeRiot(account=401),
            FakeRiot(account=500),
            FakeRiot(ids=["KR_1"], matches={"KR_1": 404}),
        ]
        texts = []
        for fake in scenarios:
            self.use(fake)
            response = self.post()
            texts.append(response.text + str(dict(response.headers)))

        def leaky():
            raise RuntimeError(f"boom {DUMMY_KEY}")

        app.dependency_overrides[get_riot_client] = leaky
        response = self.post()
        texts.append(response.text + str(dict(response.headers)))
        return texts

    def test_key_not_in_responses_or_logs(self):
        for text in self.collect_responses():
            self.assertNotIn(DUMMY_KEY, text)
        # 로그에는 예외 원문이 남을 수 있어도, 우리 코드가 키를 직접 찍지는 않는다:
        # RuntimeError 로 일부러 넣은 경우를 제외한 시나리오만 검사한다.
        self.log_handler.lines.clear()
        for fake in [
            FakeRiot(account=404),
            FakeRiot(account=429),
            FakeRiot(account=401),
            FakeRiot(account=500),
            FakeRiot(ids=["KR_1"], matches={"KR_1": make_match()}),
        ]:
            self.use(fake)
            self.post()
        for line in self.log_handler.lines:
            self.assertNotIn(DUMMY_KEY, line)

    def test_api_key_object_hides_value(self):
        key = ApiKey(DUMMY_KEY)
        self.assertNotIn(DUMMY_KEY, repr(key))
        self.assertNotIn(DUMMY_KEY, str(key))
        self.assertNotIn(DUMMY_KEY, f"{key}")
        self.assertNotIn(DUMMY_KEY, repr({"key": key}))
        self.assertEqual(key.reveal(), DUMMY_KEY)


class ConfigTest(unittest.TestCase):
    def test_reads_key_from_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(f"RIOT_API_KEY={DUMMY_KEY}\n", encoding="utf-8")
            self.assertEqual(load_api_key(path).reveal(), DUMMY_KEY)

    def test_missing_file_or_value_is_other_error_500(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "none.env"
            empty = Path(directory) / "empty.env"
            empty.write_text("RIOT_API_KEY=\n", encoding="utf-8")
            for path in (missing, empty):
                with self.subTest(path=path.name):
                    with self.assertRaises(AppError) as context:
                        load_api_key(path)
                    self.assertEqual(context.exception.status_code, 500)
                    self.assertEqual(context.exception.code, "OTHER_ERROR")


if __name__ == "__main__":
    unittest.main()
