import cv2
import mediapipe as mp
import requests
import time
import os

# ESP32 server details
ESP32_IP = '192.168.182.36'

registry_folder = "registry"

if not os.path.exists(registry_folder):
    os.makedirs(registry_folder)

mp_face_detection = mp.solutions.face_detection
mp_hands = mp.solutions.hands

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

door_open = False
gesture_start_time = None
required_hold_time = 1  

# send command to ESP32
def send_command(command):
    try:
        url = f'http://{ESP32_IP}/{command}'
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"Successfully sent {command} command.")
    except requests.RequestException as e:
        print(f"Failed to send {command} command: {e}")

# save a snapshot of the person
def save_snapshot(frame, action):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"{registry_folder}/{action}_{timestamp}.jpg"
    cv2.imwrite(filename, frame)
    print(f"Snapshot saved: {filename}")

# Initial close the door
send_command("CLOSE")

# Detect gestures
with mp_face_detection.FaceDetection(min_detection_confidence=0.5) as face_detection, \
     mp_hands.Hands(model_complexity=0, min_detection_confidence=0.8, min_tracking_confidence=0.5) as hands:

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        face_results = face_detection.process(frame_rgb)
        face_visible = face_results.detections is not None

        hand_results = hands.process(frame_rgb)

        gesture_detected = None

        if face_visible and hand_results.multi_hand_landmarks:
            for hand_landmarks in hand_results.multi_hand_landmarks:
                landmarks = hand_landmarks.landmark
                
                index_diff = landmarks[mp_hands.HandLandmark.INDEX_FINGER_MCP].y - landmarks[mp_hands.HandLandmark.INDEX_FINGER_TIP].y
                middle_diff = landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y - landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y
                ring_diff = landmarks[mp_hands.HandLandmark.RING_FINGER_MCP].y - landmarks[mp_hands.HandLandmark.RING_FINGER_TIP].y
                
                threshold = 0.05

                index_up = index_diff > threshold
                middle_up = middle_diff > threshold
                ring_up = ring_diff > threshold

                raised_fingers = sum([
                    landmarks[mp_hands.HandLandmark.INDEX_FINGER_TIP].y < landmarks[mp_hands.HandLandmark.INDEX_FINGER_MCP].y,
                    landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y < landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y,
                    landmarks[mp_hands.HandLandmark.RING_FINGER_TIP].y < landmarks[mp_hands.HandLandmark.RING_FINGER_MCP].y,
                    landmarks[mp_hands.HandLandmark.PINKY_TIP].y < landmarks[mp_hands.HandLandmark.PINKY_MCP].y
                ])

                # three fingers gesture 
                if index_up and middle_up and ring_up and raised_fingers <= 3:
                    gesture_detected = "open"
                # single finger gesture
                elif index_up and not middle_up and not ring_up:
                    gesture_detected = "close"

                if gesture_detected:
                    if gesture_start_time is None:
                        gesture_start_time = time.time()
                    elif time.time() - gesture_start_time >= required_hold_time:
                        if gesture_detected == "open" and not door_open:
                            send_command("OPEN")
                            save_snapshot(frame, "open")  
                            door_open = True
                        elif gesture_detected == "close" and door_open:
                            send_command("CLOSE")
                            save_snapshot(frame, "close") 
                            door_open = False
                        gesture_start_time = None  # Reset timer after sending command
                else:
                    gesture_start_time = None  # Reset if gesture is lost

                mp.solutions.drawing_utils.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS
                )

        cv2.imshow("Dual Authentication System", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
