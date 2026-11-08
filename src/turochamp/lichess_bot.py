"""Lichess Bot API integration."""

import os
import sys

import berserk
import chess

from .search import Searcher, compute_best_move


def play_game(client: berserk.Client, game_id: str, depth: int) -> None:
    """Manages an active game stream and issues moves."""
    print(f"Starting game: {game_id}", flush=True)
    stream = client.bots.stream_game_state(game_id)
    b = chess.Board()
    my_color = None
    searcher = Searcher()  # keeps the transposition table across the whole game

    for event in stream:
        event_type = event.get("type")

        if event_type == "gameFull":
            my_id = client.account.get()["id"].lower()
            white_id = event["white"].get("id", "").lower()
            my_color = chess.WHITE if white_id == my_id else chess.BLACK
            print(f"Playing as {'WHITE' if my_color == chess.WHITE else 'BLACK'}", flush=True)

            moves_str = event["state"].get("moves", "").strip()
            b.reset()
            if moves_str:
                for m in moves_str.split():
                    b.push_uci(m)

        elif event_type == "gameState":
            moves_str = event.get("moves", "").strip()
            b.reset()
            if moves_str:
                for m in moves_str.split():
                    b.push_uci(m)

            if event.get("status") not in (None, "started"):
                print(f"Game finished with status: {event.get('status')}", flush=True)
                break

        elif event_type == "chatLine":
            continue

        if b.is_game_over():
            print(f"Game over. Result: {b.result()}", flush=True)
            break

        if b.turn == my_color and not b.is_game_over():
            best_move = compute_best_move(b, depth=depth, searcher=searcher)
            if best_move:
                try:
                    client.bots.make_move(game_id, best_move.uci())
                except berserk.exceptions.ResponseError as err:
                    print(f"Error making move {best_move.uci()}: {err}", flush=True)


def run_bot(depth: int = 3) -> None:
    """Main event loop: accepts challenges and starts games."""
    token = os.environ.get("LICHESS_TOKEN")
    if not token:
        print("Error: LICHESS_TOKEN not set in environment or .env file.", file=sys.stderr, flush=True)
        return

    session = berserk.session.TokenSession(token)
    client = berserk.Client(session)

    try:
        user_info = client.account.get()
        print(f"Connected to Lichess as: {user_info.get('username')}", flush=True)
    except Exception as e:
        print(f"Authentication failed: {e}", file=sys.stderr, flush=True)
        return

    print(f"Bot listening for incoming Lichess challenges and games (depth={depth})...", flush=True)
    for event in client.bots.stream_incoming_events():
        event_type = event.get("type")

        if event_type == "challenge":
            challenge_id = event["challenge"]["id"]
            # Auto-accept standard chess challenges
            variant = event["challenge"]["variant"]["key"]
            challenger = event["challenge"]["challenger"]["name"]
            if variant == "standard":
                print(f"Accepting challenge {challenge_id} from {challenger}", flush=True)
                client.bots.accept_challenge(challenge_id)
            else:
                print(f"Declining non-standard challenge ({variant}) from {challenger}", flush=True)
                client.bots.decline_challenge(challenge_id)

        elif event_type == "gameStart":
            game_id = event["game"]["id"]
            try:
                play_game(client, game_id, depth)
            except Exception as e:
                print(f"Error during game {game_id}: {e}", file=sys.stderr, flush=True)
