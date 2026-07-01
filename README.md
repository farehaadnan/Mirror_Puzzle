# Mirror Puzzle 🧩✋

Capture a photo of yourself using your webcam, watch it get scrambled into a sliding puzzle, and solve it live using **hand gestures** — no mouse, no keyboard, just your fingers. Built with OpenCV and MediaPipe.

## How it works

1. **Capture** — Opens your webcam, press `SPACE` to snap a photo.
2. **Slice & Shuffle** — The photo is cropped to a square, sliced into a grid (default 3x3), and the tiles are shuffled.
3. **Hand Tracking** — MediaPipe tracks your index fingertip in real time and overlays it as a cursor on the puzzle board.
4. **Pinch to Play** — Pinch your thumb and index finger together over a tile to select it, then pinch again over another tile to swap them.
5. **Solve & Save** — Once every tile is back in its correct position, the puzzle announces itself solved and you can save the result to disk.

## Demo flow

```
Webcam → Capture Photo → Slice into Grid → Shuffle Tiles → Live Puzzle Board
   ↓
Hand Tracking (MediaPipe) → Fingertip Cursor → Pinch Gesture
   ↓
Select Tile → Select Second Tile → Swap → Check Solved → Save
```

## Requirements

- Python **3.11** (MediaPipe does not yet support 3.13+/3.14 on Windows)
- A working webcam

## Setup

```bash
# Create a virtual environment using Python 3.11
py -3.11 -m venv venv

# Activate it
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install opencv-python mediapipe numpy
```

## Usage

```bash
python capture.py
```

- **SPACE** — capture your photo from the webcam
- **ESC** — quit at any point
- **Pinch gesture** (thumb tip + index fingertip close together) — select / swap a puzzle tile
- **S** — save the solved puzzle image once solved (`solved_output.jpg`)

## Controls Summary

| Action | Input |
|---|---|
| Take photo | `SPACE` |
| Move cursor | Move index finger |
| Select / Swap tile | Pinch (thumb + index finger together) |
| Save solved puzzle | `S` (only works once solved) |
| Quit | `ESC` |

## Project structure

```
Mirror_Puzzle/
├── capture.py          # Main script: capture, slice, shuffle, hand-tracking puzzle loop
├── captured.jpg         # Your captured webcam photo (generated at runtime)
├── solved_output.jpg    # Saved once you solve the puzzle
└── venv/                 # Virtual environment (not committed to git)
```

## Configuration

Inside `capture.py`, you can tweak:

- `grid_size` — number of rows/columns (default `3` for a 3x3 puzzle)
- `pinch_cooldown` — seconds between allowed pinch actions, prevents accidental rapid selects (default `0.5`)
- The pinch distance threshold (`distance < 40`) inside the main loop — lower it for a "tighter" pinch, raise it if pinches aren't registering

## Notes

- The puzzle board is drawn directly on top of the live webcam feed, so your fingertip position maps directly onto the tile grid — no separate windows or coordinate remapping needed.
- Each tile tracks its own `correct_index`, so the solve check simply compares current board position against original position.
- If MediaPipe fails to import (`AttributeError: module 'mediapipe' has no attribute 'solutions'`), it almost always means you're running an unsupported Python version (e.g. 3.13/3.14 on Windows). Use Python 3.11 or 3.12 in a dedicated virtual environment.

## Possible next steps

- Support different grid sizes (4x4, 5x5) via a config or command-line flag
- Add a move counter / timer
- Add a "shuffle again" gesture or keypress
- Support two-hand or multi-hand interactions
- On-screen instructions overlay for first-time users

## License

MIT — do whatever you want with it.