import cv2
import mediapipe as mp
import numpy as np
import random
import math
import time

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils


def capture_photo(save_path="captured.jpg"):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return None

    print("Press SPACE to capture, ESC to quit.")
    captured_frame = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        cv2.imshow("Webcam - Press SPACE to capture", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            break
        elif key == 32:
            captured_frame = frame.copy()
            cv2.imwrite(save_path, captured_frame)
            print(f"Photo saved as {save_path}")
            break

    cap.release()
    cv2.destroyAllWindows()
    return captured_frame


def slice_image(image_path="captured.jpg", grid_size=3, board_size=480):
    """
    Loads image, crops to square, resizes to board_size x board_size,
    then slices into grid_size x grid_size tiles.
    Fixed board_size makes fingertip-to-tile mapping simple.
    """
    img = cv2.imread(image_path)
    if img is None:
        print("Error: Could not load image.")
        return None, None

    h, w = img.shape[:2]
    side = min(h, w)
    y0 = (h - side) // 2
    x0 = (w - side) // 2
    img = img[y0:y0 + side, x0:x0 + side]
    img = cv2.resize(img, (board_size, board_size))

    tile_size = board_size // grid_size
    tiles = []
    index = 0
    for row in range(grid_size):
        for col in range(grid_size):
            y1, y2 = row * tile_size, (row + 1) * tile_size
            x1, x2 = col * tile_size, (col + 1) * tile_size
            tile_img = img[y1:y2, x1:x2].copy()
            tiles.append({"correct_index": index, "image": tile_img})
            index += 1

    return tiles, tile_size


def shuffle_tiles(tiles):
    shuffled = tiles.copy()
    random.shuffle(shuffled)
    while all(t["correct_index"] == i for i, t in enumerate(shuffled)):
        random.shuffle(shuffled)
    return shuffled


def draw_board(base_frame, tiles, grid_size, tile_size, offset, selected_pos=None):
    """
    Draws the puzzle board onto base_frame at the given (x, y) offset.
    Highlights selected_pos tile with a colored border if set.
    """
    ox, oy = offset
    for pos, tile in enumerate(tiles):
        row, col = pos // grid_size, pos % grid_size
        y1, y2 = oy + row * tile_size, oy + (row + 1) * tile_size
        x1, x2 = ox + col * tile_size, ox + (col + 1) * tile_size
        base_frame[y1:y2, x1:x2] = tile["image"]

    for i in range(1, grid_size):
        y = oy + i * tile_size
        x = ox + i * tile_size
        cv2.line(base_frame, (ox, y), (ox + grid_size * tile_size, y), (0, 0, 0), 2)
        cv2.line(base_frame, (x, oy), (x, oy + grid_size * tile_size), (0, 0, 0), 2)

    cv2.rectangle(base_frame, (ox, oy),
                  (ox + grid_size * tile_size, oy + grid_size * tile_size), (0, 0, 0), 3)

    if selected_pos is not None:
        row, col = selected_pos // grid_size, selected_pos % grid_size
        y1, y2 = oy + row * tile_size, oy + (row + 1) * tile_size
        x1, x2 = ox + col * tile_size, ox + (col + 1) * tile_size
        cv2.rectangle(base_frame, (x1, y1), (x2, y2), (0, 0, 255), 4)

    return base_frame


def get_tile_at(px, py, grid_size, tile_size, offset):
    """Returns the board position index (0..N-1) for a given pixel, or None if outside board."""
    ox, oy = offset
    if px < ox or py < oy:
        return None
    col = (px - ox) // tile_size
    row = (py - oy) // tile_size
    if 0 <= row < grid_size and 0 <= col < grid_size:
        return int(row * grid_size + col)
    return None


def is_solved(tiles):
    return all(t["correct_index"] == i for i, t in enumerate(tiles))


def run_puzzle():
    photo = capture_photo("captured.jpg")
    if photo is None:
        print("No photo captured, exiting.")
        return

    cap = cv2.VideoCapture(0)

    # Grab one frame to check actual webcam resolution
    ret, test_frame = cap.read()
    if not ret:
        print("Error: Could not read from webcam.")
        return
    frame_h, frame_w = test_frame.shape[:2]

    grid_size = 3

    # Make board fit safely within frame, with margin
    margin = 40
    board_size = min(frame_w, frame_h) - (2 * margin)
    board_size = (board_size // grid_size) * grid_size  # ensure divisible by grid_size

    tiles, tile_size = slice_image("captured.jpg", grid_size=grid_size, board_size=board_size)
    if not tiles:
        return

    tiles = shuffle_tiles(tiles)

    # Center the board on screen
    offset_x = (frame_w - board_size) // 2
    offset_y = (frame_h - board_size) // 2
    offset = (offset_x, offset_y)

    selected_pos = None
    last_pinch_time = 0
    pinch_cooldown = 0.5
    was_pinching = False

    with mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    ) as hands:

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)

            frame = draw_board(frame, tiles, grid_size, tile_size, offset, selected_pos)

            hovered_pos = None
            is_pinching = False

            if results.multi_hand_landmarks:
                hand_landmarks = results.multi_hand_landmarks[0]
                index_tip = hand_landmarks.landmark[8]
                thumb_tip = hand_landmarks.landmark[4]

                ix, iy = int(index_tip.x * w), int(index_tip.y * h)
                tx, ty = int(thumb_tip.x * w), int(thumb_tip.y * h)

                distance = math.hypot(ix - tx, iy - ty)
                is_pinching = distance < 40

                hovered_pos = get_tile_at(ix, iy, grid_size, tile_size, offset)

                cursor_color = (0, 0, 255) if is_pinching else (0, 255, 0)
                cv2.circle(frame, (ix, iy), 12, cursor_color, -1)

                if hovered_pos is not None and selected_pos is None:
                    row, col = hovered_pos // grid_size, hovered_pos % grid_size
                    ox, oy = offset
                    y1 = oy + row * tile_size
                    x1 = ox + col * tile_size
                    cv2.rectangle(frame, (x1, y1), (x1 + tile_size, y1 + tile_size), (255, 255, 0), 2)

            current_time = time.time()
            if is_pinching and not was_pinching and (current_time - last_pinch_time) > pinch_cooldown:
                if hovered_pos is not None:
                    if selected_pos is None:
                        selected_pos = hovered_pos
                    else:
                        if hovered_pos != selected_pos:
                            tiles[selected_pos], tiles[hovered_pos] = tiles[hovered_pos], tiles[selected_pos]
                        selected_pos = None
                last_pinch_time = current_time

            was_pinching = is_pinching

            if is_solved(tiles):
                cv2.putText(frame, "SOLVED! Press S to save, ESC to quit",
                            (30, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow("Puzzle - pinch to select, pinch again to swap", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                break
            elif key == ord('s') and is_solved(tiles):
                cv2.imwrite("solved_output.jpg", frame)
                print("Saved solved_output.jpg")
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run_puzzle()