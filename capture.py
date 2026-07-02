"""
Mirror Puzzle - Gesture Photobooth
------------------------------------
Flow:
1. Pinch-select a screen region with both hands (open hands = drag, pinch both = lock).
2. 3-2-1 countdown, then capture photo from that region.
3. Convert to grayscale, slice into a puzzle, shuffle.
4. Solve by pinching to select/swap tiles. Already-solved photos show as a sidebar.
5. Repeat for 3 rounds total.
6. Show a final photobooth-style strip with all 3 photos. Press D to save, C to close.
"""

import cv2
import mediapipe as mp
import numpy as np
import random
import math
import time
from datetime import datetime

mp_hands = mp.solutions.hands


# ============================================================
# Region Selection (two-hand pinch to lock)
# ============================================================

def is_pinching(hand_landmarks):
    index_tip = hand_landmarks.landmark[8]
    thumb_tip = hand_landmarks.landmark[4]
    distance = math.hypot(index_tip.x - thumb_tip.x, index_tip.y - thumb_tip.y)
    return distance < 0.05


def select_region_two_hands(cap, hands):
    stop_gesture_start = None
    stop_hold_duration = 0.8
    confirmed_region = None

    print("Show one hand at each corner. Pinch BOTH hands to lock the region. ESC to cancel.")

    while True:
        ret, frame = cap.read()
        if not ret:
            return None
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)

        points = []
        both_pinching = False

        if results.multi_hand_landmarks and len(results.multi_hand_landmarks) == 2:
            pinch_flags = []
            for hand_landmarks in results.multi_hand_landmarks:
                index_tip = hand_landmarks.landmark[8]
                px, py = int(index_tip.x * w), int(index_tip.y * h)
                points.append((px, py))
                pinching = is_pinching(hand_landmarks)
                pinch_flags.append(pinching)
                dot_color = (0, 0, 255) if pinching else (0, 255, 0)
                cv2.circle(frame, (px, py), 10, dot_color, -1)
            both_pinching = all(pinch_flags)

        if len(points) == 2:
            x1, y1 = points[0]
            x2, y2 = points[1]
            box_color = (0, 0, 255) if both_pinching else (0, 255, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

            if both_pinching:
                if stop_gesture_start is None:
                    stop_gesture_start = time.time()
                held_for = time.time() - stop_gesture_start
                cv2.putText(frame, f"Locking in... {held_for:.1f}s",
                            (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                if held_for >= stop_hold_duration:
                    confirmed_region = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            else:
                stop_gesture_start = None
        else:
            stop_gesture_start = None
            cv2.putText(frame, "Show both hands (one per corner)",
                        (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        if confirmed_region:
            cv2.destroyWindow("Select Region")
            return confirmed_region

        cv2.imshow("Select Region", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            cv2.destroyWindow("Select Region")
            return None


# ============================================================
# Countdown + Capture
# ============================================================

def countdown_and_capture(region, cap, countdown_seconds=3):
    x1, y1, x2, y2 = region
    start_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            return None
        frame = cv2.flip(frame, 1)

        elapsed = time.time() - start_time
        remaining = countdown_seconds - int(elapsed)

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        if remaining > 0:
            text = str(remaining)
            cv2.putText(frame, text, (x1 + (x2 - x1) // 2 - 30, y1 + (y2 - y1) // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 255), 6)
            cv2.imshow("Get Ready", frame)
            cv2.waitKey(1)
        else:
            captured = frame[y1:y2, x1:x2].copy()
            cv2.destroyWindow("Get Ready")
            return captured


# ============================================================
# Puzzle logic
# ============================================================

def make_grayscale_puzzle_tiles(photo, grid_size=3, board_size=400):
    gray = cv2.cvtColor(photo, cv2.COLOR_BGR2GRAY)
    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)  # keep 3 channels for consistent drawing

    h, w = gray_bgr.shape[:2]
    side = min(h, w)
    y0, x0 = (h - side) // 2, (w - side) // 2
    cropped = gray_bgr[y0:y0 + side, x0:x0 + side]
    resized = cv2.resize(cropped, (board_size, board_size))

    tile_size = board_size // grid_size
    tiles = []
    index = 0
    for row in range(grid_size):
        for col in range(grid_size):
            y1, y2 = row * tile_size, (row + 1) * tile_size
            x1, x2 = col * tile_size, (col + 1) * tile_size
            tile_img = resized[y1:y2, x1:x2].copy()
            tiles.append({"correct_index": index, "image": tile_img})
            index += 1

    return tiles, tile_size, resized  # resized = the clean solved grayscale photo


def shuffle_tiles(tiles):
    shuffled = tiles.copy()
    random.shuffle(shuffled)
    while all(t["correct_index"] == i for i, t in enumerate(shuffled)):
        random.shuffle(shuffled)
    return shuffled


def draw_board(base_frame, tiles, grid_size, tile_size, offset, selected_pos=None):
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


# ============================================================
# Sidebar of already-solved photos
# ============================================================

def draw_sidebar_thumbnails(frame, solved_photos, thumb_size=100, margin=10):
    h, w = frame.shape[:2]
    x = w - thumb_size - margin

    for i, photo in enumerate(solved_photos):
        y = margin + i * (thumb_size + margin)
        if y + thumb_size > h:
            break

        thumb = cv2.resize(photo, (thumb_size, thumb_size))
        if len(thumb.shape) == 2:
            thumb = cv2.cvtColor(thumb, cv2.COLOR_GRAY2BGR)

        frame[y:y + thumb_size, x:x + thumb_size] = thumb
        cv2.rectangle(frame, (x, y), (x + thumb_size, y + thumb_size), (255, 255, 255), 2)

    return frame


# ============================================================
# Puzzle solving loop (with sidebar)
# ============================================================

def solve_puzzle_loop(cap, hands, tiles, grid_size, tile_size, offset, solved_photos_so_far):
    tiles = shuffle_tiles(tiles)
    selected_pos = None
    last_pinch_time = 0
    pinch_cooldown = 0.5
    was_pinching = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)

        frame = draw_board(frame, tiles, grid_size, tile_size, offset, selected_pos)
        frame = draw_sidebar_thumbnails(frame, solved_photos_so_far)

        hovered_pos = None
        is_pinch_now = False

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            index_tip = hand_landmarks.landmark[8]
            thumb_tip = hand_landmarks.landmark[4]

            ix, iy = int(index_tip.x * w), int(index_tip.y * h)
            tx, ty = int(thumb_tip.x * w), int(thumb_tip.y * h)

            distance = math.hypot(ix - tx, iy - ty)
            is_pinch_now = distance < 40

            hovered_pos = get_tile_at(ix, iy, grid_size, tile_size, offset)

            cursor_color = (0, 0, 255) if is_pinch_now else (0, 255, 0)
            cv2.circle(frame, (ix, iy), 12, cursor_color, -1)

            if hovered_pos is not None and selected_pos is None:
                row, col = hovered_pos // grid_size, hovered_pos % grid_size
                ox, oy = offset
                y1 = oy + row * tile_size
                x1 = ox + col * tile_size
                cv2.rectangle(frame, (x1, y1), (x1 + tile_size, y1 + tile_size), (255, 255, 0), 2)

        current_time = time.time()
        if is_pinch_now and not was_pinching and (current_time - last_pinch_time) > pinch_cooldown:
            if hovered_pos is not None:
                if selected_pos is None:
                    selected_pos = hovered_pos
                else:
                    if hovered_pos != selected_pos:
                        tiles[selected_pos], tiles[hovered_pos] = tiles[hovered_pos], tiles[selected_pos]
                    selected_pos = None
            last_pinch_time = current_time

        was_pinching = is_pinch_now

        if is_solved(tiles):
            cv2.putText(frame, "SOLVED!", (30, h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
            cv2.imshow("Solve the Puzzle", frame)
            cv2.waitKey(800)
            cv2.destroyWindow("Solve the Puzzle")
            return tiles

        cv2.imshow("Solve the Puzzle", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            cv2.destroyWindow("Solve the Puzzle")
            return None


# ============================================================
# One full round
# ============================================================

def play_one_round(cap, hands, solved_photos_so_far, grid_size=3, board_size=400):
    region = select_region_two_hands(cap, hands)
    if region is None:
        return None

    photo = countdown_and_capture(region, cap, countdown_seconds=3)
    if photo is None:
        return None

    tiles, tile_size, solved_photo = make_grayscale_puzzle_tiles(photo, grid_size, board_size)

    offset = (40, 40)
    solved_tiles = solve_puzzle_loop(cap, hands, tiles, grid_size, tile_size, offset, solved_photos_so_far)
    if solved_tiles is None:
        return None

    return solved_photo


# ============================================================
# Final photobooth strip
# ============================================================

def get_screen_size():
    """Best-effort screen resolution detection, with a safe fallback."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:
        return 1280, 800  # safe fallback


def build_photobooth_strip(solved_photos, max_width=320, max_height=800):
    """
    Builds a compact result strip: dark background, photos stacked vertically,
    and small download/delete icon buttons at the bottom.
    Sizes itself to always fit within (max_width, max_height).
    """
    padding = 14
    caption_height = 26
    button_bar_height = 60
    n = len(solved_photos)

    # Work out the largest photo_size that keeps everything within max_height
    available_height = max_height - button_bar_height - padding * (n + 2)
    photo_size = min(max_width - padding * 2, available_height // n)
    photo_size = max(photo_size, 60)  # never shrink to nothing

    strip_width = photo_size + padding * 2
    strip_height = (padding +
                     n * (photo_size + caption_height + padding) +
                     button_bar_height + padding)

    strip = np.zeros((strip_height, strip_width, 3), dtype=np.uint8)
    strip[:] = (20, 20, 20)  # dark background

    today_str = datetime.now().strftime("%d.%m.%Y")

    y_cursor = padding
    for i, photo in enumerate(solved_photos):
        photo_bgr = photo if len(photo.shape) == 3 else cv2.cvtColor(photo, cv2.COLOR_GRAY2BGR)
        photo_resized = cv2.resize(photo_bgr, (photo_size, photo_size))

        px1 = padding
        py1 = y_cursor
        px2 = px1 + photo_size
        py2 = py1 + photo_size

        cv2.rectangle(strip, (px1 - 4, py1 - 4), (px2 + 4, py2 + 4), (255, 255, 255), -1)
        strip[py1:py2, px1:px2] = photo_resized

        caption = f"{today_str} - #{i+1:02d}"
        text_size = cv2.getTextSize(caption, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
        text_x = px1 + (photo_size - text_size[0]) // 2
        cv2.putText(strip, caption, (text_x, py2 + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

        y_cursor = py2 + caption_height + padding

    # Icon-only buttons at the bottom: download (down arrow) and delete (trash)
    btn_y1 = strip_height - button_bar_height
    btn_y2 = strip_height - 10
    btn_size = btn_y2 - btn_y1
    btn_gap = 30

    center_x = strip_width // 2
    download_cx = center_x - btn_gap - btn_size // 2
    delete_cx = center_x + btn_gap + btn_size // 2
    btn_cy = (btn_y1 + btn_y2) // 2

    # Download button = circle + down arrow
    cv2.circle(strip, (download_cx, btn_cy), btn_size // 2, (0, 190, 255), -1)
    arrow_top = btn_cy - 10
    arrow_bottom = btn_cy + 8
    cv2.line(strip, (download_cx, arrow_top), (download_cx, arrow_bottom), (20, 20, 20), 3)
    cv2.arrowedLine(strip, (download_cx, arrow_bottom - 6), (download_cx, arrow_bottom + 1),
                     (20, 20, 20), 3, tipLength=0.9)
    cv2.line(strip, (download_cx - 8, arrow_bottom + 4), (download_cx + 8, arrow_bottom + 4), (20, 20, 20), 3)

    # Delete button = circle + trash/X icon
    cv2.circle(strip, (delete_cx, btn_cy), btn_size // 2, (60, 60, 70), -1)
    cv2.line(strip, (delete_cx - 8, btn_cy - 8), (delete_cx + 8, btn_cy + 8), (255, 255, 255), 3)
    cv2.line(strip, (delete_cx - 8, btn_cy + 8), (delete_cx + 8, btn_cy - 8), (255, 255, 255), 3)

    download_rect = (download_cx - btn_size // 2, btn_y1, download_cx + btn_size // 2, btn_y2)
    delete_rect = (delete_cx - btn_size // 2, btn_y1, delete_cx + btn_size // 2, btn_y2)

    return strip, download_rect, delete_rect


def show_final_strip_and_wait(solved_photos):
    screen_w, screen_h = get_screen_size()
    max_width = min(320, screen_w - 100)
    max_height = min(800, screen_h - 100)

    strip, download_rect, delete_rect = build_photobooth_strip(
        solved_photos, max_width=max_width, max_height=max_height
    )
    cv2.imshow("Result", strip)
    print("Press D to download/save, C to delete/close without saving.")

    while True:
        key = cv2.waitKey(0) & 0xFF
        if key == ord('d'):
            filename = f"photo_strip_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(filename, strip)
            print(f"Saved as {filename}")
            break
        elif key == ord('c') or key == 27:
            print("Closed without saving.")
            break

    cv2.destroyWindow("Result")


# ============================================================
# Main
# ============================================================

def main():
    cap = cv2.VideoCapture(0)
    solved_photos = []

    with mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7) as hands:
        for round_num in range(3):
            print(f"--- Round {round_num + 1} of 3 ---")
            result = play_one_round(cap, hands, solved_photos, grid_size=3, board_size=400)
            if result is None:
                print("Round cancelled, exiting.")
                cap.release()
                cv2.destroyAllWindows()
                return
            solved_photos.append(result)

    cap.release()
    cv2.destroyAllWindows()

    if len(solved_photos) == 3:
        show_final_strip_and_wait(solved_photos)


if __name__ == "__main__":
    main()