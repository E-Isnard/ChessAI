"""Move ordering and alpha-beta search.

Features: iterative deepening, transposition table, check extensions,
null-move pruning, late move reductions, killer/history move ordering,
and a quiescence search that handles positions in check.
"""

from time import perf_counter
from typing import Dict, List, Optional, Tuple

import chess
import chess.polyglot

from .evaluation import MATE_SCORE, PIECE_VALUES, evaluate

INF = 10 * MATE_SCORE
MATE_THRESHOLD = MATE_SCORE - 1000  # scores beyond this are "mate in N"
MAX_PLY = 64
MAX_TT_ENTRIES = 1_000_000

# Transposition table bound flags
EXACT, LOWER, UPPER = 0, 1, 2


class SearchTimeout(Exception):
    """Raised inside the search when the time budget is exhausted."""


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


def _has_non_pawn_material(b: chess.Board, color: chess.Color) -> bool:
    """Null-move pruning is unsafe in zugzwang-prone (pawn-only) endings."""
    return bool(b.occupied_co[color] & ~b.pawns & ~b.kings)


class Searcher:
    """Alpha-beta searcher. Reuse one instance across a game to keep the TT warm."""

    def __init__(self) -> None:
        self.tt: Dict[int, Tuple[int, int, int, Optional[chess.Move]]] = {}
        self.killers: List[List[Optional[chess.Move]]] = [[None, None] for _ in range(MAX_PLY + 1)]
        self.history: Dict[Tuple[int, int], int] = {}
        self.nodes = 0
        self._deadline: Optional[float] = None

    # --- housekeeping ---

    def new_search(self) -> None:
        self.nodes = 0
        self.killers = [[None, None] for _ in range(MAX_PLY + 1)]
        # Age history so stale information fades between moves
        self.history = {k: v // 2 for k, v in self.history.items() if v > 1}
        if len(self.tt) > MAX_TT_ENTRIES:
            self.tt.clear()

    def _check_time(self) -> None:
        if self._deadline is not None and (self.nodes & 2047) == 0 and perf_counter() > self._deadline:
            raise SearchTimeout

    # --- move ordering ---

    def _order(self, b: chess.Board, moves: List[chess.Move], tt_move: Optional[chess.Move], ply: int) -> List[chess.Move]:
        killers = self.killers[ply]
        history = self.history

        def key(m: chess.Move) -> int:
            if m == tt_move:
                return 10_000_000
            s = score_move(b, m)
            if s < 1000 and not m.promotion:  # quiet move
                if m == killers[0]:
                    return 900
                if m == killers[1]:
                    return 890
                return min(history.get((m.from_square, m.to_square), 0), 800)
            return s

        return sorted(moves, key=key, reverse=True)

    def _store_quiet_cutoff(self, move: chess.Move, depth: int, ply: int) -> None:
        k = self.killers[ply]
        if k[0] != move:
            k[1] = k[0]
            k[0] = move
        hk = (move.from_square, move.to_square)
        self.history[hk] = self.history.get(hk, 0) + depth * depth

    # --- mate-score <-> TT conversion ---

    @staticmethod
    def _to_tt(score: int, ply: int) -> int:
        if score > MATE_THRESHOLD:
            return score + ply
        if score < -MATE_THRESHOLD:
            return score - ply
        return score

    @staticmethod
    def _from_tt(score: int, ply: int) -> int:
        if score > MATE_THRESHOLD:
            return score - ply
        if score < -MATE_THRESHOLD:
            return score + ply
        return score

    # --- search ---

    def quiescence(self, b: chess.Board, alpha: int, beta: int, ply: int, qdepth: int = 8) -> int:
        """Resolves captures (and all evasions when in check) at the leaves."""
        self.nodes += 1
        self._check_time()

        in_check = b.is_check()
        if in_check:
            moves = list(b.legal_moves)
            if not moves:
                return -MATE_SCORE + ply
        else:
            stand_pat = evaluate(b)
            if stand_pat >= beta:
                return beta
            if stand_pat > alpha:
                alpha = stand_pat
            if qdepth <= 0:
                return stand_pat
            moves = [m for m in b.legal_moves if b.is_capture(m) or m.promotion]

        if qdepth <= 0 or ply >= MAX_PLY:
            return evaluate(b)

        moves.sort(key=lambda m: score_move(b, m), reverse=True)
        for move in moves:
            b.push(move)
            score = -self.quiescence(b, -beta, -alpha, ply + 1, qdepth - 1)
            b.pop()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

    def negamax(self, b: chess.Board, depth: int, alpha: int, beta: int, ply: int, allow_null: bool = True) -> int:
        self.nodes += 1
        self._check_time()

        # Draws by repetition / fifty-move rule / dead position (cheap checks only)
        if ply > 0 and (b.halfmove_clock >= 100 or b.is_insufficient_material() or b.is_repetition(2)):
            return 0

        in_check = b.is_check()
        if in_check and ply < MAX_PLY:
            depth += 1  # check extension

        if depth <= 0 or ply >= MAX_PLY:
            return self.quiescence(b, alpha, beta, ply)

        # Transposition table probe
        key = chess.polyglot.zobrist_hash(b)
        alpha_orig = alpha
        tt_move: Optional[chess.Move] = None
        entry = self.tt.get(key)
        if entry is not None:
            e_depth, e_flag, e_score, tt_move = entry
            if e_depth >= depth and ply > 0:
                e_score = self._from_tt(e_score, ply)
                if e_flag == EXACT:
                    return e_score
                if e_flag == LOWER:
                    alpha = max(alpha, e_score)
                else:
                    beta = min(beta, e_score)
                if alpha >= beta:
                    return e_score

        # Null-move pruning
        if (
            allow_null
            and not in_check
            and depth >= 3
            and beta < MATE_THRESHOLD
            and _has_non_pawn_material(b, b.turn)
        ):
            b.push(chess.Move.null())
            val = -self.negamax(b, depth - 3, -beta, -beta + 1, ply + 1, allow_null=False)
            b.pop()
            if val >= beta:
                return beta

        moves = list(b.legal_moves)
        if not moves:
            return -MATE_SCORE + ply if in_check else 0

        moves = self._order(b, moves, tt_move, ply)
        best_value = -INF
        best_move: Optional[chess.Move] = None

        for i, move in enumerate(moves):
            is_quiet = not b.is_capture(move) and not move.promotion
            gives_check = b.gives_check(move) if (is_quiet and depth >= 3 and i >= 4) else False

            b.push(move)
            if is_quiet and not in_check and not gives_check and depth >= 3 and i >= 4:
                # Late move reduction, re-search at full depth if it looks good
                val = -self.negamax(b, depth - 2, -alpha - 1, -alpha, ply + 1)
                if val > alpha:
                    val = -self.negamax(b, depth - 1, -beta, -alpha, ply + 1)
            else:
                val = -self.negamax(b, depth - 1, -beta, -alpha, ply + 1)
            b.pop()

            if val > best_value:
                best_value = val
                best_move = move
            if val > alpha:
                alpha = val
            if alpha >= beta:
                if is_quiet:
                    self._store_quiet_cutoff(move, depth, ply)
                break

        flag = EXACT
        if best_value <= alpha_orig:
            flag = UPPER
        elif best_value >= beta:
            flag = LOWER
        self.tt[key] = (depth, flag, self._to_tt(best_value, ply), best_move)

        return best_value

    def search(self, b: chess.Board, max_depth: int, time_limit: Optional[float] = None):
        """Iterative deepening. Returns (best_move, score, depth_reached).

        Searches a private copy of the board, so a timeout can never leave `b` corrupted.
        """
        board = b.copy(stack=True)
        moves = list(board.legal_moves)
        if not moves:
            return None, 0, 0

        self.new_search()
        self._deadline = perf_counter() + time_limit if time_limit else None

        best_move = max(moves, key=lambda m: score_move(board, m))
        best_score = 0
        reached = 0

        try:
            for depth in range(1, max_depth + 1):
                key = chess.polyglot.zobrist_hash(board)
                ordered = self._order(board, moves, best_move, 0)
                alpha, beta = -INF, INF
                iter_best, iter_score = ordered[0], -INF

                for move in ordered:
                    board.push(move)
                    val = -self.negamax(board, depth - 1, -beta, -alpha, ply=1)
                    board.pop()
                    if val > iter_score:
                        iter_score, iter_best = val, move
                    if val > alpha:
                        alpha = val

                # Only trust fully completed iterations
                best_move, best_score, reached = iter_best, iter_score, depth
                self.tt[key] = (depth, EXACT, self._to_tt(iter_score, 0), iter_best)

                if abs(best_score) > MATE_THRESHOLD:
                    break  # forced mate found; deeper search won't change the move
        except SearchTimeout:
            pass
        finally:
            self._deadline = None

        return best_move, best_score, reached


def compute_best_move(
    b: chess.Board,
    depth: int = 3,
    print_info: bool = True,
    time_limit: Optional[float] = None,
    searcher: Optional[Searcher] = None,
) -> Optional[chess.Move]:
    """Finds the best move using iterative-deepening alpha-beta search.

    `depth` is the maximum depth; `time_limit` (seconds) stops the search early.
    Pass a persistent `searcher` to reuse the transposition table between moves.
    """
    searcher = searcher or Searcher()
    start = perf_counter()
    move, score, reached = searcher.search(b, depth, time_limit)
    elapsed = perf_counter() - start

    if move is not None and print_info:
        nps = int(searcher.nodes / elapsed) if elapsed > 0 else 0
        if abs(score) > MATE_THRESHOLD:
            plies = MATE_SCORE - abs(score)
            shown = f"{'+' if score > 0 else '-'}M{(plies + 1) // 2}"
        else:
            shown = f"{score / 100.0:+.2f}"
        print(
            f"Move: {b.san(move)} ({move.uci()}) | Eval: {shown} pawns | Depth: {reached} "
            f"| Nodes: {searcher.nodes} ({nps} n/s) | Time: {elapsed:.3f}s",
            flush=True,
        )

    return move
