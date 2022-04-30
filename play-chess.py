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
import math

from numpy import interp
from IPython.display import display, SVG, HTML, clear_output

import_game_url = "https://lichess.org/api/import"

# Globals
max_c = 3000
min_c = -max_c
mate_score = max_c

stockfish_think_time = 0.2
player_think_time = 0.2

engine = chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish")
limit = chess.engine.Limit(time=stockfish_think_time)


def clamp(num, min_val, max_val):
    return max(min(num, max_val), min_val)

def to_percent(num, min_val, max_val):
    return (num - min_val)/(max_val - min_val)*100

emoji_list = [
                "&#128561",
                "&#128552",
                "&#128546",
                "&#128534",
                "&#128533",
                "&#128528",
                "&#128578",
                "&#128512", 
                "&#128513",
                "&#128514",
                "&#128526",
            ]

def get_emoji_from_valuation(valuation):
  value = valuation.score(mate_score=mate_score)

  if value > 2000:
    return emoji_list[0]
  if value > 1000:
    return emoji_list[1]
  if value > 500:
    return emoji_list[2]
  if value > 200:
    return emoji_list[3]
  if value > 99:
    return emoji_list[5]
  elif value < -2000:
    return emoji_list[-1]
  elif value < -1000:
    return emoji_list[-2]
  elif value < -500:
    return emoji_list[-3]
  elif value < -200:
    return emoji_list[-4]
  elif value < -99:
    return emoji_list[-5]
  else:
    return emoji_list[5]


def random_player(board):
  move = random.choice(list(board.legal_moves))
  return move.uci()

def get_move(prompt):
    uci = input(prompt)
    if uci and uci[0] == "q":
        raise KeyboardInterrupt()
    try:
        chess.Move.from_uci(uci)
    except:
        uci = None
    return uci

def human_player(board):
    uci = get_move("%s's move [q to quit]> " % who(board.turn))
    legal_uci_moves = [move.uci() for move in board.legal_moves]
    while uci not in legal_uci_moves:
        print("Legal moves: " + (",".join(sorted(legal_uci_moves))))
        uci = get_move("%s's move[q to quit]> " % who(board.turn))
    return uci

def trigger_camera(prompt):
  cmd = input(prompt)
  uci = None
  if cmd and cmd[0] == "q":
    raise KeyboardInterrupt()
  try:
    print("Triggering camera!")
    #TODO: trigger camera here
    chess.Move.from_uci(uci)
  except:
    uci = None
  return uci


def inspector_player(board):
    prompt = "%s's move. Type x to trigger. [q to quit]> " % who(board.turn)
    uci = trigger_camera(prompt)
    legal_uci_moves = [move.uci() for move in board.legal_moves]
    while uci not in legal_uci_moves:
        print("An illegal move was made!")
        print("Please move back and make another move.")
        print("Legal moves: " + (",".join(sorted(legal_uci_moves))))
        uci = trigger_camera(prompt)
    return uci

def who(player):
  return "White" if player == chess.WHITE else "Black"

def display_board(board, use_svg):
    if use_svg:
      return board._repr_svg_()
    else:
      return "<pre>" + str(board) + "</pre>"

def get_valuation(board):
  return engine.analyse(board, limit)

def create_pgn_from_board(board):
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

def create_html(num_moves, name, uci, valuation, black_status, board_stop, white_status, valuation_percent=50, lichess_link="", qrcode=""):
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
        num_moves, name, uci, valuation, black_status, board_stop, valuation_percent, white_status, lichess_link, qrcode
      )

def play_game(player1, player2, visual="svg", pause=0.1):
    use_svg = (visual == "svg")
    board = chess.Board()
    num_moves = 0
    name = ''
    html = ''
    uci = ''
    valuation = ''
    valuation_percent = 50
    black_status = ''
    white_status = ''
    board_stop = ''

    try:
        while not board.is_game_over(claim_draw=True):
            if board.turn == chess.WHITE:
                uci = player1(board)
            else:
                uci = player2(board)
            name = who(board.turn)
            raw_valuation = get_valuation(board)
            valuation = raw_valuation['score'].pov(chess.WHITE)
            valuation_percent = to_percent(clamp(raw_valuation['score'].pov(chess.WHITE).score(mate_score=mate_score), min_c, max_c), min_c, max_c)
            # valuation_percent = 20
            board.push_uci(uci)
            board_stop = display_board(board, use_svg=True)
            num_moves = len(board.move_stack)
            
            black_status = get_emoji_from_valuation(raw_valuation['score'].pov(chess.WHITE))
            white_status = get_emoji_from_valuation(raw_valuation['score'].pov(chess.BLACK))

            html = create_html(num_moves, name, uci, valuation, black_status, board_stop, white_status, valuation_percent)

            with open('index.html', 'w') as file:
                file.write(html)
            
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
        msg = "Checkmate: " + who(not board.turn) + " win!"
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

    pgn = create_pgn_from_board(board)

    lichess_link = ""
    lichess_content_json = ""
    try:
        data = {'pgn': pgn}
        r = requests.post(import_game_url, data=data)
        lichess_content_json = r.content.decode("utf-8")
    except:
        print("Failed to import game to lichess")
        

    json_obj = json.loads(lichess_content_json)
    lichess_link = json_obj['url']
    # print(lichess_link)

    qr_code = qrcode.make(lichess_link, image_factory=qrcode.image.svg.SvgImage)
    qr_code.save("generated/qrcode.svg")
    # display(SVG("generated/qrcode.svg"))

    html = create_html(num_moves, name, uci, valuation, black_status, board_stop, white_status, valuation_percent, lichess_link, "generated/qrcode.svg")
  
    with open('index.html', 'w') as file:
        file.write(html)

    if visual is not None:
        clear_output(wait=True)
        display(HTML(html))

    return (result, msg, board)
    # return 0

def staticAnalysis(board, move, my_color):
    score = random.random()
    ## Check some things about this move:
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

def player1(board):
    moves = list(board.legal_moves)
    for move in moves:
        newboard = board.copy()
        # go through board and return a score
        move.score = staticAnalysis(newboard, move, board.turn)
    moves.sort(key=lambda move: move.score, reverse=True) # sort on score
    time.sleep(player_think_time)
    return moves[0].uci()

def engine_player(board):
  result = engine.play(board, limit)
  return result.move.uci()


if __name__ == "__main__":
    play_game(engine_player, player1, visual=None)


