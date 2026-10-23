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

    def test_rift_without_first_blood_kill(self):
        self.assertEqual(
            read_match(make_match(queue_id=420, first_blood=False), PUUID, "KR_1"),
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

    def test_missing_first_blood_field_is_not_a_kill(self):
        detail = make_match()
        del detail["info"]["participants"][1]["firstBloodKill"]
        self.assertEqual(read_match(detail, PUUID, "KR_1"), (True, None))

    def test_unknown_participant_or_shape_is_other_error(self):
        with self.assertRaises(OtherError):
            read_match(make_match(), "someone-else", "KR_1")
        with self.assertRaises(OtherError):
            read_match({"info": {}}, PUUID, "KR_1")


if __name__ == "__main__":
    unittest.main()
