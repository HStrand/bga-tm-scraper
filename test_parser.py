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
            "93234993": EloData(player_name="Rutabaga00", player_id="93234993"),
            "95706228": EloData(player_name="Flaming Pile", player_id="95706228"),
        },
    },
    {
        "replay": "data/sample files/replay_507196426_94308984.html",
        "output": "data/sample files/game_507196426_94308984_test.json",
        "table_id": "507196426",
        "perspective": "94308984",
        "players": {
            "94308984": EloData(player_name="JDansp", player_id="94308984"),
            "90366871": EloData(player_name="Raduchon", player_id="90366871"),
        },
    },
    {
        "replay": "data/sample files/replay_824655675_86296239.html",
        "output": "data/sample files/game_824655675_86296239_test.json",
        "table_id": "824655675",
        "perspective": "86296239",
        "players": {
            "86296239": EloData(player_name="StrandedKnight", player_id="86296239"),
            "98490496": EloData(player_name="cdman234", player_id="98490496"),
        },
        "map": "Elysium"
    },
]

parser = Parser()

for game in GAMES:
    print(f"\n=== {game['table_id']} ===")
    with open(game["replay"], "r", encoding="utf-8") as f:
        html = f.read()

    metadata = GameMetadata()
    metadata.players = game["players"]

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
        if move.cards_sold:
            print(f"Move {move.move_number}: cards_sold={move.cards_sold}")
