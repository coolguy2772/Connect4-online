from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import random
import string
from urllib.parse import parse_qs, urlparse

ROWS = 6
COLS = 7
rooms = {}


def create_room():
  code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
  rooms[code] = {
      "board": [[0 for _ in range(COLS)] for _ in range(ROWS)],
      "turn": 1,
      "winner": 0,
  }
  return code


def check_winner(b, player):
  for r in range(ROWS):
    for c in range(COLS - 3):
      if all(b[r][c + i] == player for i in range(4)):
        return True
  for r in range(ROWS - 3):
    for c in range(COLS):
      if all(b[r + i][c] == player for i in range(4)):
        return True
  for r in range(ROWS - 3):
    for c in range(COLS - 3):
      if all(b[r + i][c + i] == player for i in range(4)):
        return True
  for r in range(3, ROWS):
    for c in range(COLS - 3):
      if all(b[r - i][c + i] == player for i in range(4)):
        return True
  return False


class Connect4Handler(BaseHTTPRequestHandler):

  def log_message(self, format, *args):
    pass

  def do_GET(self):
    parsed = urlparse(self.path)
    query = parse_qs(parsed.query)
    room_code = query.get("room", [""]).upper()

    if parsed.path == "/create":
      code = create_room()
      self.send_response(200)
      self.send_header("Content-type", "application/json")
      self.end_headers()
      self.wfile.write(json.dumps({"room": code}).encode("utf-8"))
      return

    if parsed.path == "/state":
      if room_code not in rooms:
        self.send_response(404)
        self.end_headers()
        return
      self.send_response(200)
      self.send_header("Content-type", "application/json")
      self.end_headers()
      self.wfile.write(json.dumps(rooms[room_code]).encode("utf-8"))
      return

    if parsed.path == "/move":
      if room_code in rooms:
        state = rooms[room_code]
        try:
          col = int(query.get("col", [-1]))
          player = int(query.get("player",))
          if (
              state["winner"] == 0
              and player == state["turn"]
              and 0 <= col < COLS
          ):
            for r in range(ROWS - 1, -1, -1):
              if state["board"][r][col] == 0:
                state["board"][r][col] = player
                if check_winner(state["board"], player):
                  state["winner"] = player
                elif all(
                    state["board"][c] != 0 for c in range(COLS)
                ):
                  state["winner"] = 3
                else:
                  state["turn"] = 2 if player == 1 else 1
                break
        except ValueError:
          pass
      self.send_response(200)
      self.end_headers()
      return

    if parsed.path == "/reset":
      if room_code in rooms:
        rooms[room_code] = {
            "board": [[0 for _ in range(COLS)] for _ in range(ROWS)],
            "turn": 1,
            "winner": 0,
        }
      self.send_response(200)
      self.end_headers()
      return

    html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Online Connect 4</title>
            <style>
                body { font-family: sans-serif; text-align: center; background: #121212; color: #fff; margin: 0; padding: 20px; }
                input, button { font-size: 16px; padding: 10px 15px; margin: 5px; border: none; border-radius: 6px; font-weight: bold; }
                input { width: 120px; text-align: center; text-transform: uppercase; }
                button { cursor: pointer; background: #2196f3; color: #fff; }
                .p1-btn { background: #ff5252; color: #fff; }
                .p2-btn { background: #ffd740; color: #000; }
                .active-role { outline: 3px solid #fff; }
                .board { display: inline-grid; grid-template-columns: repeat(7, 42px); gap: 6px; background: #1565c0; padding: 10px; border-radius: 10px; margin-top: 10px; }
                .cell { width: 42px; height: 42px; border-radius: 50%; background: #121212; cursor: pointer; }
                .p1 { background: #ff5252; }
                .p2 { background: #ffd740; }
                .reset { background: #4caf50; color: #fff; margin-top: 15px; }
                .hidden { display: none; }
            </style>
        </head>
        <body>
            <h2>🔴 Connect 4 Online 🟡</h2>
            
            <div id="lobby">
                <button onclick="createNewRoom()">Create New Room</button>
                <p>- OR -</p>
                <input type="text" id="codeInput" placeholder="ROOM CODE" maxlength="4">
                <button onclick="joinExistingRoom()">Join Room</button>
            </div>

            <div id="gameArea" class="hidden">
                <h3>Room Code: <span id="roomDisplay" style="color:#00e676;"></span></h3>
                <div>
                    <button id="btn1" class="p1-btn" onclick="setPlayer(1)">Play as Red (P1)</button>
                    <button id="btn2" class="p2-btn" onclick="setPlayer(2)">Play as Yellow (P2)</button>
                </div>
                <h3 id="status">Pick Red or Yellow above!</h3>
                <div class="board" id="board"></div>
                <br>
                <button class="reset" onclick="resetGame()">New Round</button>
                <button onclick="location.reload()" style="background:#555;">Leave Room</button>
            </div>

            <script>
                let currentRoom = "";
                let myPlayer = 0;
                let poller = null;

                function createNewRoom() {
                    fetch('/create').then(r => r.json()).then(data => {
                        enterRoom(data.room);
                    });
                }

                function joinExistingRoom() {
                    const code = document.getElementById('codeInput').value.trim().toUpperCase();
                    if (code.length !== 4) return alert("Enter a 4-character room code.");
                    enterRoom(code);
                }

                function enterRoom(code) {
                    currentRoom = code;
                    document.getElementById('lobby').classList.add('hidden');
                    document.getElementById('gameArea').classList.remove('hidden');
                    document.getElementById('roomDisplay').innerText = code;
                    fetchState();
                    poller = setInterval(fetchState, 1000);
                }

                function setPlayer(p) {
                    myPlayer = p;
                    document.getElementById('btn1').classList.toggle('active-role', p === 1);
                    document.getElementById('btn2').classList.toggle('active-role', p === 2);
                    fetchState();
                }

                function dropPiece(col) {
                    if (myPlayer === 0) return alert("Pick Red or Yellow first!");
                    fetch(`/move?room=${currentRoom}&col=${col}&player=${myPlayer}`).then(fetchState);
                }

                function resetGame() {
                    fetch(`/reset?room=${currentRoom}`).then(fetchState);
                }

                function fetchState() {
                    if (!currentRoom) return;
                    fetch(`/state?room=${currentRoom}`).then(r => {
                        if (!r.ok) {
                            alert("Room not found!");
                            location.reload();
                            return;
                        }
                        return r.json();
                    }).then(data => {
                        if (!data) return;
                        const statusEl = document.getElementById('status');
                        if (data.winner === 1) statusEl.innerText = "🎉 Red Wins!";
                        else if (data.winner === 2) statusEl.innerText = "🎉 Yellow Wins!";
                        else if (data.winner === 3) statusEl.innerText = "🤝 Draw!";
                        else {
                            const turnName = data.turn === 1 ? "Red's" : "Yellow's";
                            statusEl.innerText = (data.turn === myPlayer) ? "Your Turn!" : `Waiting for ${turnName} move...`;
                        }

                        const boardEl = document.getElementById('board');
                        boardEl.innerHTML = '';
                        for (let r = 0; r < 6; r++) {
                            for (let c = 0; c < 7; c++) {
                                const cell = document.createElement('div');
                                cell.className = 'cell';
                                if (data.board[r][c] === 1) cell.classList.add('p1');
                                if (data.board[r][c] === 2) cell.classList.add('p2');
                                cell.onclick = () => dropPiece(c);
                                boardEl.appendChild(cell);
                            }
                        }
                    });
                }
            </script>
        </body>
        </html>
        """
    self.send_response(200)
    self.send_header("Content-type", "text/html; charset=utf-8")
    self.end_headers()
    self.wfile.write(html.encode("utf-8"))


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 8080))
  server = HTTPServer(("0.0.0.0", port), Connect4Handler)
  print(f"Server running on port {port}")
  server.serve_forever()
