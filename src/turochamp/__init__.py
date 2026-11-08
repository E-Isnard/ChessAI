"""Turochamp: a small alpha-beta chess engine and Lichess bot."""

from .evaluation import eval_board
from .search import compute_best_move

__version__ = "0.1.0"
__all__ = ["compute_best_move", "eval_board", "__version__"]
