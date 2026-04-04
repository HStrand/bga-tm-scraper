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
]

parser = Parser()

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
