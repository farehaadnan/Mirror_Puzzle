import cv2
import mediapipe as mp
import math

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils


def run_hand_tracking():
    cap = cv2.VideoCapture(0)

    with mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    ) as hands:

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)  # mirror for natural movement
            h, w = frame.shape[:2]

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Index fingertip = landmark 8
                    index_tip = hand_landmarks.landmark[8]
                    thumb_tip = hand_landmarks.landmark[4]

                    ix, iy = int(index_tip.x * w), int(index_tip.y * h)
                    tx, ty = int(thumb_tip.x * w), int(thumb_tip.y * h)

                    # Draw fingertip cursor
                    cv2.circle(frame, (ix, iy), 12, (0, 255, 0), -1)

                    # Calculate pinch distance (index tip to thumb tip)
                    distance = math.hypot(ix - tx, iy - ty)

                    is_pinching = distance < 40  # threshold, tweak as needed

                    if is_pinching:
                        cv2.putText(frame, "PINCH", (ix + 20, iy),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                        cv2.circle(frame, (ix, iy), 18, (0, 0, 255), 3)

                    # Optional: draw full hand skeleton (comment out if distracting)
                    mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            cv2.imshow("Hand Tracking Test", frame)

            if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run_hand_tracking()