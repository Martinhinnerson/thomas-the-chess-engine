import chess
import chess.engine
import chess.pgn
import time
import collections
import random
import requests
import qrcode
import qrcode.image.svg
import json

from numpy import interp
from IPython.display import display, SVG, HTML, clear_output

# ----------------------------------------------------------------------
# global stuff
# ----------------------------------------------------------------------
max_c = 3000
min_c = -max_c
mate_score = max_c

stockfish_think_time = 0.05
player_think_time = 0.05

import_game_url = "https://lichess.org/api/import"

engine = chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish")
engine2 = chess.engine.SimpleEngine.popen_uci("/usr/games/komodo-13.02-linux")

limit = chess.engine.Limit(time=stockfish_think_time)

emoji_list = [
    "&#128561",#😱
    "&#128552",#😨
    "&#128546",#😢
    "&#128531",#😓
    "&#128533",#😕
    "&#128528",#😐
    "&#128578",#🙂
    "&#128512",#😀
    "&#128513",#😁
    "&#128514",#😂	
    "&#128526",#😎
]

def clamp(num, min_val, max_val):
    """Clamp a value to a range

    Args:
        num (_type_): _description_
        min_val (_type_): _description_
        max_val (_type_): _description_

    Returns:
        _type_: _description_
    """
    return max(min(num, max_val), min_val)

def map_range(value, min_in, max_in, min_out, max_out):
    """Map a range to another range and round the result

    Args:
        value (_type_): _description_
        min_in (_type_): _description_
        max_in (_type_): _description_
        min_out (_type_): _description_
        max_out (_type_): _description_

    Returns:
        _type_: _description_
    """
    return round(min_out + (((value - min_in) / (max_in - min_in)) * (max_out - min_out)))

def to_percent(num, min_val, max_val):
    """Get the percent value based on a range

    Args:
        num (_type_): _description_
        min_val (_type_): _description_
        max_val (_type_): _description_

    Returns:
        _type_: _description_
    """
    return (num - min_val)/(max_val - min_val)*100


def get_emoji_from_evaluation(evaluation):
    """Get a emoji based on evaluation

    Args:
        evaluation (_type_): _description_

    Returns:
        _type_: _description_
    """
    value = evaluation.score(mate_score=mate_score)

    if value > mate_score:
        return emoji_list[0]
    elif value < -mate_score:
        return emoji_list[-1]
    else:
        return emoji_list[map_range(value, min_c, max_c, 0, len(emoji_list)-1)]


def get_move(prompt):
    """Get a move to that a human player should play

    Args:
        prompt (_type_): _description_

    Raises:
        KeyboardInterrupt: _description_

    Returns:
        _type_: _description_
    """
    uci = input(prompt)
    if uci and uci[0] == "q":
        raise KeyboardInterrupt()
    try:
        chess.Move.from_uci(uci)
    except:
        uci = None
    return uci


def random_player(board):
    """A player that makes random moves

    Args:
        board (chess.Board): the current chess board

    Returns:
        _type_: _description_
    """
    move = random.choice(list(board.legal_moves))
    return move.uci()


def human_player(board):
    """A human player that moves on console input

    Args:
        board (chess.Board): the current chess board

    Returns:
        _type_: _description_
    """
    uci = get_move("%s's move [q to quit]> " % player_as_string(board.turn))
    legal_uci_moves = [move.uci() for move in board.legal_moves]
    while uci not in legal_uci_moves:
        print("Legal moves: " + (",".join(sorted(legal_uci_moves))))
        uci = get_move("%s's move[q to quit]> " % player_as_string(board.turn))
    return uci


def trigger_camera(prompt):
    """trigger the camera and look for a new move

    Args:
        prompt (_type_): _description_

    Raises:
        KeyboardInterrupt: _description_

    Returns:
        _type_: _description_
    """
    cmd = input(prompt)
    uci = None
    if cmd and cmd[0] == "q":
        raise KeyboardInterrupt()
    try:
        print("Triggering camera!")
        # TODO: trigger camera here
        # TODO: look for no move
        chess.Move.from_uci(uci)
    except:
        uci = None
    return uci


def camera_player(board):
    """A player that plays on a real board and the move is detected by a camera

    Args:
        board (chess.Board): the current chess board

    Returns:
        _type_: _description_
    """
    prompt = "%s's move. Type x to trigger. [q to quit]> " % player_as_string(
        board.turn)
    uci = trigger_camera(prompt)
    legal_uci_moves = [move.uci() for move in board.legal_moves]
    while uci not in legal_uci_moves:
        print("An illegal move was made!")
        print("Please move back and make another move.")
        print("Legal moves: " + (",".join(sorted(legal_uci_moves))))
        uci = trigger_camera(prompt)
    return uci


def player_as_string(player):
    """Get the player as a string

    Args:
        player (_type_): _description_

    Returns:
        _type_: _description_
    """
    return "White" if player == chess.WHITE else "Black"


def display_board(board, use_svg):
    """return a display of the board depending on mode

    Args:
        board (chess.Board): the current chess board
        use_svg (_type_): _description_

    Returns:
        _type_: _description_
    """
    if use_svg:
        return board._repr_svg_()
    else:
        return "<pre>" + str(board) + "</pre>"


def get_valuation(board):
    """Get the current board evaluation from an engine

    Args:
        board (chess.Board): the current chess board

    Returns:
        _type_: _description_
    """
    return engine.analyse(board, limit)


def create_pgn_from_board(board):
    """Create a pgn representation of the played game on a board

    Args:
        board (chess.Board): the current chess board

    Returns:
        _type_: _description_
    """
    game = chess.pgn.Game()

    # Undo all moves
    switchyard = collections.deque()
    while board.move_stack:
        switchyard.append(board.pop())

    game.setup(board)
    node = game

    # Replay all moves
    while switchyard:
        move = switchyard.pop()
        node = node.add_variation(move)
        board.push(move)

    game.headers["Result"] = board.result()
    return game


def create_html(num_moves, name, uci, evaluation, black_status, board_stop, white_status, valuation_percent=50, lichess_link="", qrcode=""):
    """Create and style a html representation of the board

    Args:
        num_moves (_type_): _description_
        name (_type_): _description_
        uci (_type_): _description_
        evaluation (_type_): _description_
        black_status (_type_): _description_
        board_stop (_type_): _description_
        white_status (_type_): _description_
        valuation_percent (int, optional): _description_. Defaults to 50.
        lichess_link (str, optional): _description_. Defaults to "".
        qrcode (str, optional): _description_. Defaults to "".

    Returns:
        _type_: _description_
    """

    return """
          <b>
          Move: %s %s
          </br>Play %s
          </br>Evaluation: %s
          </br><p style="font-size:60px;margin:-4px 0 -4px 0px">Black: %s</p>
          </br>%s
          </br><p><meter min="0" max="100" low="45" high="55" optimum="50" value="%s" style="width:390px;height:40px;margin:-10px 0px -30px 0px"/></p>
          </br><p style="font-size:60px;margin:-4px 0 -4px 0px">White: %s</p>
          </br><a>%s</a><br/><img src="%s"/>
          </b>
          """ % (
        num_moves, name, uci, evaluation, black_status, board_stop, valuation_percent, white_status, lichess_link, qrcode
    )


def write_board_html(html):
    with open('board.html', 'w') as file:
        file.write(html)


def play_game(basic_player, player2, visual="svg", pause=0.1):
    """Play a game of chess

    Args:
        basic_player (_type_): _description_
        player2 (_type_): _description_
        visual (str, optional): _description_. Defaults to "svg".
        pause (float, optional): _description_. Defaults to 0.1.

    Returns:
        _type_: _description_
    """
    board = chess.Board()
    num_moves = 0
    name = ''
    html = ''
    uci = ''
    evaluation = ''
    valuation_percent = 50
    black_status = ''
    white_status = ''
    board_stop = ''

    try:
        while not board.is_game_over(claim_draw=True):
            if board.turn == chess.WHITE:
                uci = basic_player(board)
            else:
                uci = player2(board)
            name = player_as_string(board.turn)
            raw_valuation = get_valuation(board)
            evaluation = raw_valuation['score'].pov(chess.WHITE)
            valuation_percent = to_percent(clamp(raw_valuation['score'].pov(
                chess.WHITE).score(mate_score=mate_score), min_c, max_c), min_c, max_c)
            # valuation_percent = 20
            board.push_uci(uci)
            board_stop = display_board(board, use_svg=True)
            num_moves = len(board.move_stack)

            black_status = get_emoji_from_evaluation(
                raw_valuation['score'].pov(chess.BLACK))
            white_status = get_emoji_from_evaluation(
                raw_valuation['score'].pov(chess.WHITE))

            html = create_html(num_moves, name, uci, evaluation,
                               black_status, board_stop, white_status, valuation_percent)

            write_board_html(html)

            if visual is not None:
                if visual == "svg":
                    clear_output(wait=True)
                display(HTML(html))
                if visual == "svg":
                    time.sleep(pause)

    except KeyboardInterrupt:
        msg = "Game interrupted!"
        return (None, msg, board)
    result = None
    if board.is_checkmate():
        msg = "Checkmate: " + player_as_string(not board.turn) + " win!"
        result = not board.turn
    elif board.is_stalemate():
        msg = "Draw: stalemate"
    elif board.is_fivefold_repetition():
        msg = "Draw: 5-fold repetition"
    elif board.is_insufficient_material():
        msg = "Draw: insufficient material"
    elif board.can_claim_draw():
        msg = "Draw: claim"
    if visual is not None:
        print(msg)

    # Create a pgn from the finished game
    pgn = create_pgn_from_board(board)

    # Send a post request to lichess to load the pgn and create a link to a analysis board
    lichess_content_json = ""
    try:
        data = {'pgn': pgn}
        r = requests.post(import_game_url, data=data)
        lichess_content_json = r.content.decode("utf-8")
    except:
        print("Failed to import game to lichess")

    json_obj = json.loads(lichess_content_json)
    lichess_link = json_obj['url']

    # Create a QR code for the lichess link
    qr_code = qrcode.make(
        lichess_link, image_factory=qrcode.image.svg.SvgImage)
    qr_code.save("generated/qrcode.svg")

    # Create the html for the final state including the qr-code
    html = create_html(num_moves, name, uci, evaluation, black_status, board_stop,
                       white_status, valuation_percent, lichess_link, "generated/qrcode.svg")

    write_board_html(html)

    if visual is not None:
        clear_output(wait=True)
        display(HTML(html))

    return (result, msg, board)


def staticAnalysis(board, move, my_color):
    """Dumb way to evaluate a chess board for the basic players

    Args:
        board (chess.Board): the current chess board
        move (_type_): _description_
        my_color (_type_): _description_

    Returns:
        _type_: _description_
    """
    score = random.random()
    # Check some things about this move:
    # score += 10 if board.is_capture(move) else 0
    # To actually make the move:
    board.push(move)
    # Now check some other things:
    for (piece, value) in [(chess.PAWN, 1),
                           (chess.BISHOP, 3),
                           (chess.KING, 0),
                           (chess.QUEEN, 9),
                           (chess.KNIGHT, 3),
                           (chess.ROOK, 5)]:
        score += len(board.pieces(piece, my_color)) * value
        score -= len(board.pieces(piece, not my_color)) * value
        # can also check things about the pieces position here
    # Check global things about the board
    score += 100 if board.is_checkmate() else 0
    return score


def basic_player(board):
    """A very basic computer player

    Args:
        board (chess.Board): the current chess board

    Returns:
        _type_: _description_
    """
    moves = list(board.legal_moves)
    for move in moves:
        newboard = board.copy()
        # go through board and return a score
        move.score = staticAnalysis(newboard, move, board.turn)
    moves.sort(key=lambda move: move.score, reverse=True)  # sort on score
    time.sleep(player_think_time)
    return moves[0].uci()


def engine_player(board):
    """A player using a chess engine, eg. stockfish

    Args:
        board (chess.Board): the current chess board

    Returns:
        _type_: _description_
    """
    result = engine.play(board, limit)
    return result.move.uci()

def engine_player_2(board):
    """A player using a chess engine, eg. stockfish

    Args:
        board (chess.Board): the current chess board

    Returns:
        _type_: _description_
    """
    result = engine2.play(board, limit)
    return result.move.uci()

if __name__ == "__main__":
    play_game(engine_player, engine_player_2, visual=None)
