import chess

from turochamp import compute_best_move, eval_board


def test_start_position_is_balanced():
    assert eval_board(chess.Board()) == 0


def test_finds_move_from_start_position():
    board = chess.Board()
    move = compute_best_move(board, depth=2, print_info=False)
    assert move in board.legal_moves


def test_mate_in_one():
    board = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4")
    move = compute_best_move(board, depth=2, print_info=False)
    assert board.san(move) == "Qxf7#"


def test_no_move_when_game_over():
    board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")  # stalemate
    assert compute_best_move(board, depth=2, print_info=False) is None
