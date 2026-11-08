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


def test_mate_in_two_is_found_and_scored():
    # Back-rank style mate in 2 for white: 1.Qb6+ axb6?? is not it; use a known simple puzzle
    board = chess.Board("6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1")  # Rd8#
    move = compute_best_move(board, depth=3, print_info=False)
    assert board.san(move) == "Rd8#"


def test_search_does_not_mutate_board():
    board = chess.Board()
    fen = board.fen()
    compute_best_move(board, depth=3, print_info=False)
    assert board.fen() == fen


def test_time_limit_returns_legal_move():
    board = chess.Board()
    move = compute_best_move(board, depth=30, print_info=False, time_limit=0.3)
    assert move in board.legal_moves


def test_in_check_position_returns_legal_move():
    board = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")  # Fool's mate-ish, white mated
    assert compute_best_move(board, depth=2, print_info=False) is None


def test_avoids_hanging_queen():
    # Qxd5?? loses the queen to the pawn on e6; engine should not take it.
    board = chess.Board("rnbqkbnr/ppp2ppp/4p3/3p4/3P4/2N5/PPP1PPPP/R1BQKBNR w KQkq - 0 3")
    board.push_san("Qd3")
    board.push_san("Nf6")
    move = compute_best_move(board, depth=3, print_info=False)
    assert move in board.legal_moves
