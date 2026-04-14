import argparse
import json
from collections import Counter
from pathlib import Path


def find_conceder_id(game):
    winner = game.get("winner")
    players = game.get("players") or {}
    if winner:
        losers = [pid for pid, p in players.items()
                  if p.get("player_name") != winner]
        if len(losers) == 1:
            return losers[0]

    for m in reversed(game.get("moves") or []):
        desc = m.get("description") or ""
        if "concedes the game" in desc:
            return m.get("player_id")
    return None


def find_last_card_before_concede(game):
    conceder_id = find_conceder_id(game)
    if not conceder_id:
        return None

    for m in reversed(game.get("moves") or []):
        if str(m.get("player_id")) != str(conceder_id):
            continue
        if m.get("action_type") == "play_card" and m.get("card_played"):
            return m["card_played"]
    return None


def print_stats(counter, scanned, conceded_games, with_card):
    print(f"Scanned games: {scanned}")
    print(f"Conceded games: {conceded_games}")
    print(f"Conceded with identifiable last card: {with_card}")
    print()
    print(f"{'Count':>6}  Card")
    print("-" * 40)
    for card, count in counter.most_common():
        print(f"{count:>6}  {card}")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--num", type=int, default=None,
                    help="Max number of games to scan")
    ap.add_argument("--parsed-dir", default=str(Path(__file__).parent / "parsed"))
    args = ap.parse_args()

    parsed_dir = Path(args.parsed_dir)
    counter = Counter()
    scanned = 0
    conceded_games = 0
    with_card = 0

    for path in parsed_dir.rglob("*.json"):
        if args.num is not None and scanned >= args.num:
            break
        scanned += 1
        if scanned % 100 == 0:
            print(f"Scanned {scanned} games ({conceded_games} conceded)...")
        if scanned % 1000 == 0:
            print_stats(counter, scanned, conceded_games, with_card)
        try:
            with open(path, encoding="utf-8") as f:
                game = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        if not game.get("conceded"):
            continue
        conceded_games += 1

        card = find_last_card_before_concede(game)
        if card:
            counter[card] += 1
            with_card += 1

    print_stats(counter, scanned, conceded_games, with_card)


if __name__ == "__main__":
    main()
