"""Move ordering and alpha-beta search."""

from time import perf_counter
from typing import Optional

import chess

from .evaluation import MATE_SCORE, PIECE_VALUES, eval_board


def score_move(b: chess.Board, move: chess.Move) -> int:
    """Heuristic for move ordering: MVV-LVA for captures, checks, promotions."""
    score = 0
    if move.promotion:
        score += 800

    if b.is_capture(move):
        victim = b.piece_at(move.to_square)
        attacker = b.piece_at(move.from_square)
        victim_val = PIECE_VALUES[victim.piece_type] if victim else 100
        attacker_val = PIECE_VALUES[attacker.piece_type] if attacker else 100
        score += 1000 + victim_val - (attacker_val // 10)

    if b.gives_check(move):
        score += 50

    return score


def quiescence(b: chess.Board, alpha: int, beta: int, ply: int, max_quiesce_depth: int = 4) -> int:
    """Searches only captures at leaf nodes to mitigate the horizon effect."""
    if b.is_checkmate():
        return -MATE_SCORE + ply
    if b.is_stalemate() or b.is_insufficient_material() or b.can_claim_draw():
        return 0

    stand_pat = eval_board(b)
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat

    if max_quiesce_depth <= 0:
        return stand_pat

    # Order tactical captures
    tactical_moves = [m for m in b.legal_moves if b.is_capture(m) or m.promotion]
    tactical_moves.sort(key=lambda m: score_move(b, m), reverse=True)

    for move in tactical_moves:
        b.push(move)
        score = -quiescence(b, -beta, -alpha, ply + 1, max_quiesce_depth - 1)
        b.pop()

        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha


def negamax(b: chess.Board, depth: int, alpha: int, beta: int, ply: int = 0) -> int:
    """Negamax search with Alpha-Beta pruning, in-place push/pop, and move ordering."""
    if b.is_checkmate():
        return -MATE_SCORE + ply
    if b.is_stalemate() or b.is_insufficient_material() or b.can_claim_draw():
        return 0

    if depth <= 0:
        return quiescence(b, alpha, beta, ply)

    moves = list(b.legal_moves)
    if not moves:
        return 0

    moves.sort(key=lambda m: score_move(b, m), reverse=True)
    best_value = -float("inf")

    for move in moves:
        b.push(move)
        val = -negamax(b, depth - 1, -beta, -alpha, ply + 1)
        b.pop()

        if val > best_value:
            best_value = val
        if val > alpha:
            alpha = val
        if alpha >= beta:
            break

    return best_value


def compute_best_move(b: chess.Board, depth: int = 3, print_info: bool = True) -> Optional[chess.Move]:
    """Computes the best move for the current position using Alpha-Beta pruning at root."""
    moves = list(b.legal_moves)
    if not moves:
        return None

    # Order moves to maximize root alpha-beta cutoffs
    moves.sort(key=lambda m: score_move(b, m), reverse=True)

    start_time = perf_counter()
    alpha = -float("inf")
    beta = float("inf")
    best_move = moves[0]

    for move in moves:
        b.push(move)
        val = -negamax(b, depth - 1, -beta, -alpha, ply=1)
        b.pop()

        if val > alpha:
            alpha = val
            best_move = move

    elapsed = perf_counter() - start_time

    if print_info:
        san = b.san(best_move)
        print(f"Move: {san} ({best_move.uci()}) | Eval: {alpha / 100.0:+.2f} cp | Depth: {depth} | Time: {elapsed:.3f}s", flush=True)

    return best_move
