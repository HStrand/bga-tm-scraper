"""Test script to parse sample replays and output JSON for verification."""
import json
import os
from bga_tm_scraper.parser import Parser, GameMetadata, EloData

GAMES = [
    {
        "replay": "data/sample files/replay_741102170_93234993.html",
        "output": "data/sample files/game_741102170_93234993_test.json",
        "table_id": "741102170",
        "perspective": "93234993",
        "players": {
            "93234993": EloData(
                player_name="Rutabaga00", player_id="93234993",
                arena_points=544, arena_points_change=-17,
                game_rank=0, game_rank_change=-3,
                position=2,
            ),
            "95706228": EloData(
                player_name="Flaming Pile", player_id="95706228",
                arena_points=323, arena_points_change=16,
                game_rank=3, game_rank_change=3,
                position=1,
            ),
        },
        "metadata": {
            "played_at": "2025-10-09T02:08:00",
            "map": "Hellas",
            "prelude_on": True,
            "colonies_on": False,
            "corporate_era_on": True,
            "draft_on": True,
            "beginners_corporations_on": False,
            "game_speed": "Real-time \u00b7 Normal speed",
            "game_mode": "Arena mode",
        },
    },
    {
        "replay": "data/sample files/replay_507196426_94308984.html",
        "output": "data/sample files/game_507196426_94308984_test.json",
        "table_id": "507196426",
        "perspective": "94308984",
        "players": {
            "94308984": EloData(
                player_name="JDansp", player_id="94308984",
                arena_points=500, arena_points_change=4,
                position=1,
            ),
            "90366871": EloData(
                player_name="Raduchon", player_id="90366871",
                arena_points=254, arena_points_change=-4,
                position=2,
            ),
        },
        "metadata": {
            "played_at": "2024-05-01T18:27:00",
            "map": "Tharsis",
            "prelude_on": False,
            "colonies_on": False,
            "corporate_era_on": True,
            "draft_on": True,
            "beginners_corporations_on": False,
            "game_speed": "Real-time \u00b7 Fast paced",
            "game_mode": "Normal mode",
        },
    },
    {
        "replay": "data/sample files/replay_824655675_86296239.html",
        "output": "data/sample files/game_824655675_86296239_test.json",
        "table_id": "824655675",
        "perspective": "86296239",
        "players": {
            "86296239": EloData(
                player_name="StrandedKnight", player_id="86296239",
                arena_points=1893, arena_points_change=5,
                game_rank=673, game_rank_change=2,
                position=1,
            ),
            "98490496": EloData(
                player_name="cdman234", player_id="98490496",
                arena_points=1551, arena_points_change=-5,
                game_rank=309, game_rank_change=-2,
                position=2,
            ),
        },
        "metadata": {
            "played_at": "2026-03-21T21:04:00",
            "map": "Elysium",
            "prelude_on": True,
            "colonies_on": False,
            "corporate_era_on": True,
            "draft_on": True,
            "beginners_corporations_on": False,
            "game_speed": "Real-time \u00b7 Normal speed",
            "game_mode": "Arena mode",
        },
    },
    {
        "replay": "data/sample files/replay_829956648_86296239.html",
        "output": "data/sample files/game_829956648_86296239_test.json",
        "table_id": "829956648",
        "perspective": "86296239",
        "players": {
            "86296239": EloData(
                player_name="StrandedKnight", player_id="86296239",
                arena_points=0, game_rank=0,
                position=1,
            ),
            "96958875": EloData(
                player_name="Kirbypolo", player_id="96958875",
                arena_points=0, game_rank=0,
                position=2,
            ),
        },
        "metadata": {
            "played_at": "2026-03-28T00:00:00",
            "map": "Tharsis",
            "prelude_on": True,
            "colonies_on": False,
            "corporate_era_on": True,
            "draft_on": True,
            "beginners_corporations_on": False,
            "game_speed": "Real-time · Normal speed",
            "game_mode": "Arena mode",
        },
    },
    {
        # October 2026 replay format: each move also carries private gameStateChange
        # packets naming the player who becomes active next.
        "replay": "data/sample files/86296239/replay_926358228.html",
        "output": "data/sample files/game_926358228_86296239_test.json",
        "table_id": "926358228",
        "perspective": "86296239",
        "players": {
            "86296239": EloData(
                player_name="StrandedKnight", player_id="86296239",
                arena_points=1950, arena_points_change=2,
                game_rank=682, game_rank_change=2,
                position=1,
            ),
            "91942669": EloData(
                player_name="Vero_Vendetta", player_id="91942669",
                arena_points=1454, arena_points_change=-2,
                game_rank=222, game_rank_change=-2,
                position=2,
            ),
        },
        "metadata": {
            "played_at": "2026-10-04T22:32:00",
            "map": "Tharsis",
            "prelude_on": True,
            "colonies_on": False,
            "corporate_era_on": True,
            "draft_on": True,
            "beginners_corporations_on": False,
            "game_speed": "Real-time · Normal speed",
            "game_mode": "Arena mode",
        },
    },
    {
        # Takebacks whose savepoint is the player's own previous move (a tile placement,
        # card plays, a research keep). Those moves stood; the parser must keep them.
        "replay": "data/sample files/98180562/replay_929799439.html",
        "output": "data/sample files/game_929799439_98180562_test.json",
        "table_id": "929799439",
        "perspective": "98180562",
        "players": {
            "98180562": EloData(player_name="tom37610", player_id="98180562", position=1),
            "96938426": EloData(player_name="ft029", player_id="96938426", position=2),
        },
        "metadata": {
            "played_at": "2026-10-11T00:00:00",
            "map": "Elysium",
            "prelude_on": True,
            "colonies_on": False,
            "corporate_era_on": True,
            "draft_on": True,
            "beginners_corporations_on": False,
            "game_speed": "No time limit · with friends only",
            "game_mode": "Normal mode",
        },
    },
]

parser = Parser()
misattributed = []
takeback_problems = []

for game in GAMES:
    print(f"\n=== {game['table_id']} ===")
    with open(game["replay"], "r", encoding="utf-8") as f:
        html = f.read()

    metadata = GameMetadata()
    metadata.players = game["players"]
    for key, value in game.get("metadata", {}).items():
        if hasattr(metadata, key):
            setattr(metadata, key, value)

    game_data = parser.parse_complete_game(html, metadata, game["table_id"], game["perspective"])
    parser.export_to_json(game_data, game["output"], player_perspective=None)
    print(f"Wrote {game['output']}")

    # Also write a compact (non-prettified) version
    compact_output = os.path.splitext(game["output"])[0] + "_compact.json"
    def convert_to_dict(obj):
        if hasattr(obj, '__dict__'):
            return {k: convert_to_dict(v) for k, v in obj.__dict__.items()}
        elif isinstance(obj, list):
            return [convert_to_dict(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: convert_to_dict(v) for k, v in obj.items()}
        return obj
    with open(compact_output, "w", encoding="utf-8") as f:
        json.dump(convert_to_dict(game_data), f, ensure_ascii=False)
    print(f"Wrote {compact_output}")

    for move in game_data.moves:
        if move.cards_discarded:
            print(f"Move {move.move_number}: cards_discarded={move.cards_discarded}")

    # A played card must be filed under the player the log line names.
    names = {elo.player_name: pid for pid, elo in game["players"].items()}
    for move in game_data.moves:
        if not move.card_played or move.action_type == "draft":
            continue
        for line in (move.description or "").split(" | "):
            for name, pid in names.items():
                if line == f"{name} plays card {move.card_played}" and str(move.player_id) != pid:
                    misattributed.append(
                        f"{game['table_id']} move {move.move_number}: {line!r} is filed under {move.player_name}"
                    )

    # An explicit reversal (a "takes back" message during a draft or research buy) undid the
    # previous move; a savepoint restore (undoRestore) did not: BGA has already dropped the
    # undone moves from the replay, and the move before the takeback stood.
    gamelogs = parser._extract_g_gamelogs(html)
    for i, move in enumerate(game_data.moves):
        if move.action_type != "takeback" or i == 0:
            continue
        prev = game_data.moves[i - 1]
        if prev.player_id != move.player_id:
            continue
        reverses = parser._takeback_reverses_previous_move(move.move_number, gamelogs)
        if prev.action_type == "cancelled" and not reverses:
            takeback_problems.append(
                f"{game['table_id']} move {prev.move_number} was cancelled by the savepoint-restore takeback after it"
            )
        if prev.action_type != "cancelled" and reverses:
            takeback_problems.append(
                f"{game['table_id']} move {prev.move_number} was reversed by the takeback after it but not cancelled"
            )
    if game["table_id"] == "929799439":
        by_number = {m.move_number: m for m in game_data.moves}
        if by_number[51].tile_location != "Olympus Mons (8,3)":
            takeback_problems.append(f"929799439 move 51: Nuclear Zone tile on Olympus Mons lost, got {by_number[51].tile_location!r}")
        if by_number[118].card_played != "Moss" or by_number[431].card_played != "Magnetic Field Generators":
            takeback_problems.append("929799439: card play before a takeback lost (moves 118, 431)")
        tiles = by_number[52].game_state.special_tiles.get("98180562", {})
        if tiles.get("Nuclear Zone") != "Olympus Mons (8,3)":
            takeback_problems.append(f"929799439 move 52: special_tiles lacks Nuclear Zone on Olympus Mons, got {tiles}")

# Dates written with slashes are month first, and never land in the future.
from datetime import datetime
from bga_tm_scraper.dates import parse_slash_date

date_problems = []
today = datetime(2026, 3, 16, 12, 0)
for text, expected in [
    ("03/04/2026 at 13:08", datetime(2026, 3, 4, 13, 8)),    # day-first would be April 3rd, after "today"
    ("02/01/2025 at 07:00", datetime(2025, 2, 1, 7, 0)),     # both readings are in the past: month first
    ("07/07/2025 at 02:29", datetime(2025, 7, 7, 2, 29)),
    ("15/06/2025 at 00:29", datetime(2025, 6, 15, 0, 29)),   # cannot be month first
    ("12/03/2026 at 09:00", datetime(2026, 3, 12, 9, 0)),    # month-first would be December, after "today"
]:
    a, b, rest = text.split("/")
    hour, minute = rest.split(" at ")[1].split(":")
    got = parse_slash_date(int(a), int(b), int(rest[:4]), int(hour), int(minute), now=today)
    if got != expected:
        date_problems.append(f"{text!r} read as {got}, expected {expected}")
parsed = parser._parse_game_datetime("01/02/2025 at 10:00")
if not parsed or parsed["parsed_datetime"] != "2025-01-02T10:00:00":
    date_problems.append(f"Parser._parse_game_datetime read 01/02/2025 as {parsed and parsed['parsed_datetime']}")
if date_problems:
    print(f"\nFAILED: {len(date_problems)} date(s) read wrongly")
    for problem in date_problems:
        print(f"  {problem}")
    raise SystemExit(1)

if takeback_problems:
    print(f"\nFAILED: {len(takeback_problems)} takeback problem(s)")
    for problem in takeback_problems:
        print(f"  {problem}")
    raise SystemExit(1)

if misattributed:
    print(f"\nFAILED: {len(misattributed)} card play(s) filed under the wrong player")
    for problem in misattributed:
        print(f"  {problem}")
    raise SystemExit(1)
