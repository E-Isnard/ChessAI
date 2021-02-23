import chess
import os
import berserk
from dotenv import load_dotenv
from random import choice
from time import sleep
load_dotenv()

PIECES_VALUES = {
    "p": -1,
    "n": -3,
    "b": -3,
    "r": -5,
    "q": -9,
    "k": 0,

    "P": 1,
    "N": 3,
    "B": 3,
    "R": 5,
    "Q": 9,
    "K": 0
}


def eval_board(b: chess.Board) -> float:
    if b.result()=="0-1":
        return float("-inf")
    if b.result()=="1-0":
        return float("inf")
    if b.result()=="1/2-1/2":
        return 0
    s = 0
    for square in b.piece_map():
        piece = b.piece_at(square)
        color_sign = (1 if piece.symbol().isupper() else -1)

        if chess.SQUARE_NAMES[square.__pos__()] in ["e4", "d4", "e5", "d5"]:
            s += 2*color_sign

        if piece.symbol() == "T" and chess.square_rank(square) == 6:
            s += 2
        if piece.symbol() == "t" and chess.square_rank(square) == 1:
            s -= 2
        
        s+=len(b.attacks(square))*color_sign*0.1
        
        s += PIECES_VALUES[piece.symbol()]
    if b.is_check() and b.turn==chess.WHITE:
        s-=2
    if b.is_check() and b.turn==chess.BLACK:
        s+=2
    return s


def min_max(b: chess.Board, depth: int) -> float:
    if depth == 0:
        return eval_board(b)
    if b.turn == chess.WHITE:
        value = float("-inf")
        for move in b.legal_moves:
            b_tmp = b.copy()
            b_tmp.push(move)
            value = max(value, min_max(b_tmp, depth-1))
        return value
    else:
        value = float("inf")
        for move in b.legal_moves:
            b_tmp = b.copy()
            b_tmp.push(move)
            value = min(value, min_max(b_tmp, depth-1))
        return value


def alpha_beta(b: chess.Board, depth: int, alpha=float("-inf"), beta=float("inf")) -> float:
    if depth == 0:
        return eval_board(b)
    if b.turn == chess.WHITE:
        value = float("-inf")
        for move in b.legal_moves:
            b_tmp = b.copy()
            b_tmp.push(move)
            value = max(value, alpha_beta(b_tmp, depth-1, alpha, beta))
            if value>beta:
                return value
            alpha = max(alpha, value)
    else:
        value = float("inf")
        for move in b.legal_moves:
            b_tmp = b.copy()
            b_tmp.push(move)
            value = min(value, alpha_beta(b_tmp, depth-1,alpha,beta))
            if value < alpha:
                return value
            beta = min(beta, value)
    return value


def compute_best_move(b: chess.Board, depth: int, print_moves=True, algo=alpha_beta,) -> str:
    values = []
    for move in b.legal_moves:
        b_copy = b.copy()
        b_copy.push(move)
        values.append(algo(b_copy,depth))
    best_value = max(values) if b.turn else min(values)
    list_legal_moves = [move.uci() for move in b.legal_moves]
    best_moves = [move for i,move in enumerate(list_legal_moves) if values[i]==best_value]
    best_move = choice(best_moves)
    if print_moves:
        print("Best move:", b.san(chess.Move.from_uci(best_move)))
        print("Value:", max(values))
        print()
    return best_move


def turochamp(depth:int) -> None:
    session = berserk.session.TokenSession(os.environ["LICHESS_TOKEN"])
    client = berserk.Client(session)
    b = chess.Board()
    for e in client.bots.stream_incoming_events():
        if e["type"] == "gameStart":
            game_id = e["game"]["id"]
            game_state_stream = client.bots.stream_game_state(game_id)
            initial_state = next(game_state_stream)
            color = chess.WHITE if "id" in initial_state["white"].keys() else chess.BLACK
            moves = initial_state["state"]["moves"]
            for m in moves.split(" "):
                if m != "":
                    b.push_uci(m)
            if b.turn==color:
                    best_move = compute_best_move(b, depth)
                    client.bots.make_move(game_id, best_move)
            for state in game_state_stream:
                last_move = state["moves"].split(" ")[-1]
                b.push_uci(last_move)
                if b.is_game_over():
                    b.reset()
                    break
                if b.turn==color:
                    best_move = compute_best_move(b, depth)
                    client.bots.make_move(game_id, best_move)
                

turochamp(2)
# b = chess.Board()
# b.push_san("e4")
# b.push_san("e5")
# b.push_san("d4")
# b.push_san("Bb4+")
# compute_best_move(b,3)
# scholar_mate = "e4 e5 Qh5 Nc6 Bc4 Nf6 Qxf7"
# fool_mate = "f3 e6 g4 Qh4"
# for move in fool_mate.split(" "):
#     b.push_san(move)
# print(b.result())


