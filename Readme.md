# Turochamp Lichess Bot

A chess engine and automated bot capable of playing on [Lichess](https://lichess.org) via the [Lichess Bot API](https://lichess.org/api) using `berserk` and `python-chess`.

## Features
- **Search**: Negamax with Alpha-Beta pruning, in-place `push`/`pop`, and root move pruning.
- **Move Ordering**: MVV-LVA (Most Valuable Victim – Least Valuable Attacker) for captures, promotion prioritisation, and checks.
- **Quiescence Search**: Tactical capture resolution at leaf nodes to eliminate the horizon effect.
- **Positional Evaluation**: Piece-Square Tables (PST) for development, center control, and king safety.
- **Lichess Integration**: Automatic challenge acceptance for standard chess and resilient event streaming.

## Project Layout
```
src/turochamp/
    evaluation.py   # material values, piece-square tables, static eval
    search.py       # move ordering, quiescence, negamax, compute_best_move
    lichess_bot.py  # Lichess event loop and game handling
    cli.py          # command-line entry point
tests/              # pytest suite
pyproject.toml
```

## Usage

### 1. Install
```bash
pip install -e ".[dev]"
```

### 2. Configure Token
Create a `.env` file (see `.env.sample`):
```env
LICHESS_TOKEN=your_lichess_bot_token_here
```

### 3. Run Tests (Offline)
```bash
pytest
```

### 4. Run Online Lichess Bot
```bash
turochamp --depth 3
```
(or `python -m turochamp --depth 3`). The bot listens for incoming challenges, accepts standard ones, and plays moves.
