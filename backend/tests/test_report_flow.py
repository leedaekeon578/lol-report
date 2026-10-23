import unittest

import httpx

from app.errors import AccountNotFound, KeyExpired, OtherError, RateLimited
from app.report import build_report
from app.riot_client import USER_AGENT
from tests import DUMMY_KEY, FakeRiot, make_match


def run(fake: FakeRiot, riot_id: str = "Name#KR1"):
    sleeps: list[float] = []
    report = build_report(fake.client(), riot_id, sleep=sleeps.append)
    return report, sleeps


class FlowTest(unittest.TestCase):
    def test_stops_after_twenty_rift_matches(self):
        ids = [f"KR_{i}" for i in range(30)]
        fake = FakeRiot(ids=ids, matches={i: make_match(team_first_blood=False) for i in ids})
        report, sleeps = run(fake)
        self.assertEqual(report["searched_matches"], 20)
        self.assertEqual(report["rift_matches"], 20)
        self.assertFalse(report["incomplete"])
        self.assertIsNone(report["incomplete_message"])
        self.assertEqual(len(fake.match_requests()), 20)
        self.assertEqual(sleeps, [0.1] * 19)  # 상세 호출 사이에만

    def test_requests_up_to_100_ids(self):
        fake = FakeRiot(ids=[])
        run(fake)
        ids_request = [r for r in fake.requests if "/by-puuid/" in r.url.path][0]
        self.assertEqual(ids_request.url.params["count"], "100")
        self.assertEqual(ids_request.url.params["start"], "0")

    def test_non_rift_matches_are_skipped_but_counted_as_searched(self):
        ids = ["KR_1", "KR_2", "KR_3", "KR_4"]
        matches = {
            "KR_1": make_match(queue_id=450),
            "KR_2": make_match(queue_id=420, team_first_blood=True, win=True),
            "KR_3": make_match(queue_id=440, team_first_blood=True, win=False),
            "KR_4": make_match(queue_id=420, team_first_blood=False),
        }
        report, _ = run(FakeRiot(ids=ids, matches=matches))
        self.assertEqual(report["searched_matches"], 4)
        self.assertEqual(report["rift_matches"], 3)
        self.assertEqual([g["match_id"] for g in report["games"]], ["KR_2", "KR_3"])
        self.assertEqual(
            report["summary"],
            {"games": 2, "wins": 1, "losses": 1, "win_rate": 50.0},
        )
        self.assertTrue(report["incomplete"])
        self.assertIn("3개", report["incomplete_message"])

    def test_shortfall_after_hundred_matches(self):
        ids = [f"KR_{i}" for i in range(100)]
        matches = {i: make_match(queue_id=450) for i in ids}
        for i in ids[:5]:
            matches[i] = make_match(queue_id=420, team_first_blood=False)
        report, sleeps = run(FakeRiot(ids=ids, matches=matches))
        self.assertEqual(report["searched_matches"], 100)
        self.assertEqual(report["rift_matches"], 5)
        self.assertTrue(report["incomplete"])
        self.assertEqual(len(sleeps), 99)

    def test_zero_games(self):
        ids = ["KR_1", "KR_2"]
        fake = FakeRiot(ids=ids, matches={i: make_match(team_first_blood=False) for i in ids})
        report, _ = run(fake)
        self.assertEqual(report["games"], [])
        self.assertEqual(
            report["summary"], {"games": 0, "wins": 0, "losses": 0, "win_rate": None}
        )
        self.assertEqual(report["rift_matches"], 2)

    def test_rate_limit_on_detail_stops_immediately(self):
        ids = [f"KR_{i}" for i in range(10)]
        matches = {i: make_match(team_first_blood=False) for i in ids}
        matches["KR_2"] = 429
        fake = FakeRiot(ids=ids, matches=matches)
        sleeps: list[float] = []
        with self.assertRaises(RateLimited):
            build_report(fake.client(), "Name#KR1", sleep=sleeps.append)
        self.assertEqual(len(fake.match_requests()), 3)  # 재시도·후속 호출 없음
        self.assertEqual(len(sleeps), 2)

    def test_other_detail_failures_stop_everything(self):
        failures = [404, 500, 503, httpx.ConnectTimeout("timeout")]
        for failure in failures:
            with self.subTest(failure=repr(failure)):
                ids = [f"KR_{i}" for i in range(5)]
                matches = {i: make_match(team_first_blood=False) for i in ids}
                matches["KR_1"] = failure
                fake = FakeRiot(ids=ids, matches=matches)
                with self.assertRaises(OtherError):
                    run(fake)
                self.assertEqual(len(fake.match_requests()), 2)

    def test_account_errors(self):
        cases = [
            (404, AccountNotFound),
            (429, RateLimited),
            (401, KeyExpired),
            (403, KeyExpired),
            (500, OtherError),
        ]
        for status, error_type in cases:
            with self.subTest(status=status):
                with self.assertRaises(error_type):
                    run(FakeRiot(account=status))

    def test_match_id_list_errors(self):
        for status, error_type in [(404, OtherError), (429, RateLimited), (403, KeyExpired)]:
            with self.subTest(status=status):
                with self.assertRaises(error_type):
                    run(FakeRiot(ids_status=status))

    def test_every_request_sends_user_agent_and_key_header_only(self):
        ids = ["KR_1", "KR_2"]
        fake = FakeRiot(ids=ids, matches={i: make_match() for i in ids})
        run(fake)
        self.assertEqual(len(fake.requests), 4)
        for request in fake.requests:
            self.assertEqual(request.headers["User-Agent"], USER_AGENT)
            self.assertEqual(request.headers["X-Riot-Token"], DUMMY_KEY)
            self.assertNotIn(DUMMY_KEY, str(request.url))

    def test_both_teams_false_counts_as_rift_but_not_as_game(self):
        ids = ["KR_1", "KR_2", "KR_3"]
        matches = {
            "KR_1": make_match(team_first_blood=False, opponent_first_blood=False),
            "KR_2": make_match(team_first_blood=True),
            "KR_3": make_match(team_first_blood=False),
        }
        report, _ = run(FakeRiot(ids=ids, matches=matches))
        self.assertEqual(report["searched_matches"], 3)
        self.assertEqual(report["rift_matches"], 3)
        self.assertEqual([g["match_id"] for g in report["games"]], ["KR_2"])

    def test_broken_team_data_stops_everything(self):
        ids = [f"KR_{i}" for i in range(5)]
        matches = {i: make_match(team_first_blood=False) for i in ids}
        del matches["KR_1"]["info"]["teams"]
        fake = FakeRiot(ids=ids, matches=matches)
        sleeps: list[float] = []
        with self.assertRaises(OtherError):
            build_report(fake.client(), "Name#KR1", sleep=sleeps.append)
        self.assertEqual(len(fake.match_requests()), 2)  # 이후 호출 없음
        self.assertEqual(len(sleeps), 1)

    def test_input_is_trimmed_and_case_kept_in_account_request(self):
        fake = FakeRiot()
        run(fake, "  NaMe#kR1  ")
        self.assertTrue(fake.requests[0].url.path.endswith("/NaMe/kR1"))


if __name__ == "__main__":
    unittest.main()
