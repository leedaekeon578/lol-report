import unittest

from app.errors import InvalidInput, OtherError
from app.report import parse_riot_id, read_match, win_rate
from tests import PUUID, make_match


class ParseRiotIdTest(unittest.TestCase):
    def test_strips_surrounding_whitespace_only(self):
        self.assertEqual(parse_riot_id("  Name#KR1 \n"), ("Name", "KR1"))

    def test_keeps_case(self):
        self.assertEqual(parse_riot_id("NaMe#kR1"), ("NaMe", "kR1"))

    def test_splits_on_last_hash(self):
        self.assertEqual(parse_riot_id("a#b#c"), ("a#b", "c"))

    def test_rejects_bad_format(self):
        for raw in ["", "   ", "Name", "#KR1", "Name#", "  #  "]:
            with self.subTest(raw=raw):
                with self.assertRaises(InvalidInput):
                    parse_riot_id(raw)


class WinRateTest(unittest.TestCase):
    def test_one_decimal_place(self):
        self.assertEqual(win_rate(2, 3), 66.7)
        self.assertEqual(win_rate(1, 3), 33.3)
        self.assertEqual(win_rate(1, 1), 100.0)
        self.assertEqual(win_rate(0, 4), 0.0)

    def test_rounds_half_up(self):
        self.assertEqual(win_rate(1, 16), 6.3)  # 6.25
        self.assertEqual(win_rate(1, 8), 12.5)

    def test_none_when_no_games(self):
        self.assertIsNone(win_rate(0, 0))


class ReadMatchTest(unittest.TestCase):
    def test_non_rift_queue_is_excluded(self):
        self.assertEqual(read_match(make_match(queue_id=450), PUUID, "KR_1"), (False, None))
        self.assertEqual(read_match(make_match(queue_id=400), PUUID, "KR_1"), (False, None))

    def test_rift_when_my_team_did_not_get_first_blood_is_excluded(self):
        self.assertEqual(
            read_match(make_match(queue_id=420, team_first_blood=False), PUUID, "KR_1"),
            (True, None),
        )

    def test_both_queues_count_and_game_shape(self):
        for queue_id in (420, 440):
            with self.subTest(queue_id=queue_id):
                is_rift, game = read_match(
                    make_match(queue_id=queue_id, win=False, champion="Ahri"),
                    PUUID,
                    "KR_7",
                )
                self.assertTrue(is_rift)
                self.assertEqual(
                    game,
                    {
                        "match_id": "KR_7",
                        "champion": "Ahri",
                        "win": False,
                        "started_at": "2023-11-14T22:13:20Z",
                    },
                )

    def test_team_first_blood_included_even_if_i_did_not_kill(self):
        detail = make_match(team_first_blood=True, my_first_blood_kill=False)
        is_rift, game = read_match(detail, PUUID, "KR_1")
        self.assertTrue(is_rift)
        self.assertIsNotNone(game)

    def test_personal_first_blood_kill_is_ignored(self):
        detail = make_match(team_first_blood=False, my_first_blood_kill=True)
        self.assertEqual(read_match(detail, PUUID, "KR_1"), (True, None))

    def test_team_true_without_any_personal_first_blood_kill_is_included(self):
        detail = make_match(team_first_blood=True)
        for participant in detail["info"]["participants"]:
            participant.pop("firstBloodKill", None)
        is_rift, game = read_match(detail, PUUID, "KR_1")
        self.assertTrue(is_rift)
        self.assertIsNotNone(game)

    def test_both_teams_false_is_excluded_but_counted_as_rift(self):
        detail = make_match(team_first_blood=False, opponent_first_blood=False)
        self.assertEqual(read_match(detail, PUUID, "KR_1"), (True, None))

    def test_my_team_is_found_by_team_id(self):
        mine_first = make_match(my_team_id=200, team_first_blood=True)
        theirs_first = make_match(my_team_id=200, team_first_blood=False)
        # 팀 목록의 순서를 바꿔도 내 teamId 로 찾는다.
        mine_first["info"]["teams"].reverse()
        theirs_first["info"]["teams"].reverse()
        self.assertIsNotNone(read_match(mine_first, PUUID, "KR_1")[1])
        self.assertIsNone(read_match(theirs_first, PUUID, "KR_1")[1])

    def test_unknown_participant_or_shape_is_other_error(self):
        with self.assertRaises(OtherError):
            read_match(make_match(), "someone-else", "KR_1")
        with self.assertRaises(OtherError):
            read_match({"info": {}}, PUUID, "KR_1")
        detail = make_match()
        del detail["info"]["participants"][1]["teamId"]
        with self.assertRaises(OtherError):
            read_match(detail, PUUID, "KR_1")

    def test_missing_team_data_is_other_error(self):
        def without_teams(detail):
            del detail["info"]["teams"]

        def without_my_team(detail):
            detail["info"]["teams"] = [detail["info"]["teams"][1]]

        def without_objectives(detail):
            del detail["info"]["teams"][0]["objectives"]

        def without_first(detail):
            del detail["info"]["teams"][0]["objectives"]["champion"]["first"]

        def first_is_not_bool(detail):
            detail["info"]["teams"][0]["objectives"]["champion"]["first"] = "true"

        def first_is_none(detail):
            detail["info"]["teams"][0]["objectives"]["champion"]["first"] = None

        cases = [
            without_teams,
            without_my_team,
            without_objectives,
            without_first,
            first_is_not_bool,
            first_is_none,
        ]
        for break_it in cases:
            with self.subTest(case=break_it.__name__):
                detail = make_match()
                break_it(detail)
                with self.assertRaises(OtherError):
                    read_match(detail, PUUID, "KR_1")

    def test_non_rift_queue_does_not_read_teams(self):
        detail = make_match(queue_id=450)
        del detail["info"]["teams"]
        self.assertEqual(read_match(detail, PUUID, "KR_1"), (False, None))


if __name__ == "__main__":
    unittest.main()
