# Mirror Puzzle 

A fully hands-free photobooth. Use hand gestures to pick a capture region, get photographed after a 3-2-1 countdown, then unscramble a grayscale puzzle of yourself using pinch gestures — no mouse, no keyboard required for the core experience. Do this 3 times and get a compact photo strip result at the end. Built with OpenCV and MediaPipe.

## How it works

1. **Select your capture region (two-hand gesture)** — hold one hand near each corner of the area you want to capture. A live yellow box follows both fingertips. Pinch **both hands** at once and hold briefly to lock the region in (box turns red, then confirms).
2. **Countdown** — a `3... 2... 1...` countdown appears over your selected region.
3. **Capture + grayscale** — a photo is taken from that exact region and converted to black & white.
4. **Puzzle time** — the photo is sliced into a grid (default 3x3) and shuffled.
5. **Solve with pinch gestures** — pinch a tile to select it (red border), pinch a second tile to swap them. Repeat until every tile is back in place.
6. **Sidebar preview** — while playing rounds 2 and 3, thumbnails of your already-solved photos appear along the side of the puzzle screen, like a running photobooth strip building up.
7. **Repeat for 3 rounds** — region select → countdown → puzzle → solve, three times total. The webcam and hand tracking stay running the whole time — no windows close/reopen between rounds.
8. **Final result screen** — all 3 solved photos are shown stacked in a compact strip, sized to always fit your screen. Two icon buttons sit at the bottom: a **download** icon (yellow circle, down arrow) to save the strip, and a **delete** icon (dark circle, X) to close without saving.

## Demo flow

```
Two-hand pinch region select → 3-2-1 countdown → Capture + Grayscale
        ↓
Slice into grid → Shuffle → Pinch to select/swap tiles → Solved
        ↓
Repeat 3x (sidebar shows progress) 
        ↓
Final compact result strip → Download or Delete
```

## Requirements

- Python **3.11** (MediaPipe does not yet support 3.13+/3.14 on Windows)
- A working webcam
- Windows (screen size auto-detection uses the Windows API; falls back to a default resolution on other platforms)

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
python mirror_puzzle.py
```

### Gestures & controls

| Action | Input |
|---|---|
| Select capture region | Hold one hand at each corner (open hands), then pinch **both hands** together and hold ~0.8s to lock |
| Redo region selection | Just open your hands again before locking |
| Cancel at any screen | `ESC` |
| Move puzzle cursor | Move index finger |
| Select / swap puzzle tile | Pinch (thumb + index finger together) |
| Save final result strip | `D` |
| Close without saving | `C` |

## Project structure

```
Mirror_Puzzle/
├── mirror_puzzle.py         # Full script: region select, countdown, puzzle, rounds, result screen
├── photo_strip_*.jpg        # Saved result strips (timestamped, generated at runtime)
└── venv/                     # Virtual environment (not committed to git)
```

## How the logic fits together

- **Region selection**: both hands' index fingertips define opposite corners of a rectangle. Pinching (thumb + index close together, checked via normalized landmark distance) on *both* hands simultaneously, held briefly, locks the box in.
- **Same coordinate space trick**: the puzzle board is drawn directly onto the webcam frame instead of a separate window, so fingertip pixel positions map straight onto tile grid cells with simple division — no coordinate translation needed.
- **Tiles remember two things**: their `correct_index` (where they belong) and their current position in the shuffled list (where they are now). Swapping just swaps list positions; solving is just checking if every tile's position matches its `correct_index`.
- **Result strip sizing**: instead of a fixed size that gets scaled down after the fact, `build_photobooth_strip()` detects the screen resolution first and works backward — it computes the largest photo size that will still fit everything (photos + captions + button bar + padding) within the screen bounds, so it can never overflow.

## Configuration

Inside `mirror_puzzle.py`, you can tweak:

- `grid_size` (in `play_one_round`) — number of rows/columns for the puzzle (default `3`)
- `countdown_seconds` (in `countdown_and_capture`) — length of the 3-2-1 countdown
- Pinch thresholds — `is_pinching()` (region select, normalized distance) and the `distance < 40` check inside `solve_puzzle_loop` (pixel distance) — adjust if pinches feel too sensitive or unresponsive
- `stop_hold_duration` — how long both hands must stay pinched to lock in the region
- `max_width` / `max_height` in `show_final_strip_and_wait` — bounds used to size the final result strip

## Notes

- If MediaPipe fails to import (`AttributeError: module 'mediapipe' has no attribute 'solutions'`), it almost always means you're on an unsupported Python version (e.g. 3.13/3.14 on Windows). Use Python 3.11 or 3.12 in a dedicated virtual environment.
- Screen recording tools that rely on window/app detection (like Windows Game Bar) often don't pick up OpenCV windows properly. Use a raw display-capture tool (OBS with "Display Capture," or the Windows 11 Snipping Tool's video mode) if you want to record a session.

## Possible next steps

- Make the download/delete icons pinch-clickable, so the entire flow — including the final screen — is fully hands-free
- Support different grid sizes via a menu or config
- Add a move counter / solve timer per round
- Cross-platform screen size detection (currently Windows-only via `ctypes`)

## License

MIT — do whatever you want with it.
