from flask import Flask, render_template, Response, jsonify
import cv2
import mediapipe as mp
import numpy as np
import math
import time
from collections import deque

from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

app = Flask(__name__)

# ================= AUDIO =================
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))
min_vol, max_vol = volume.GetVolumeRange()[:2]

# ================= CAMERA =================
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
cap.set(cv2.CAP_PROP_BUFFERSIZE,1)

camera_running = True

# ================= MEDIAPIPE =================
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=0,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.5
)

# ================= DATA =================
prev_volume = 0
smooth_factor = 0.2
p_time = 0

volume_history = deque(maxlen=40)
distance_history = deque(maxlen=40)

metrics = {
    "volume":0,
    "distance":0,
    "fps":0,
    "hands":0,
    "gesture":"None",
    "gesture_recognition":"None",
    "volume_history":[],
    "distance_history":[]
}

# ================= FINGER DETECTION =================
def detect_fingers(hand):

    fingers=[]

    if hand.landmark[4].x > hand.landmark[3].x:
        fingers.append(1)
    else:
        fingers.append(0)

    if hand.landmark[8].y < hand.landmark[6].y:
        fingers.append(1)
    else:
        fingers.append(0)

    if hand.landmark[12].y < hand.landmark[10].y:
        fingers.append(1)
    else:
        fingers.append(0)

    if hand.landmark[16].y < hand.landmark[14].y:
        fingers.append(1)
    else:
        fingers.append(0)

    if hand.landmark[20].y < hand.landmark[18].y:
        fingers.append(1)
    else:
        fingers.append(0)

    return fingers

# ================= DISTANCE GESTURE =================
def distance_gesture(distance):

    if distance > 80:
        return "Open Hand"

    elif distance > 20:
        return "Pinch"

    elif distance > 0:
        return "Closed"

    return "None"

# ================= VIDEO STREAM =================
def generate_frames():

    global prev_volume, p_time, camera_running

    while True:

        if not camera_running:
            time.sleep(0.1)
            continue

        success, frame = cap.read()

        if not success:
            continue

        frame = cv2.flip(frame,1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = hands.process(rgb)

        distance = 0
        volume_percent = 0
        hand_count = 0
        gesture = "None"

        if results.multi_hand_landmarks:

            hand_count = len(results.multi_hand_landmarks)

            hand = results.multi_hand_landmarks[0]

            mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)

            fingers = detect_fingers(hand)

            h,w,_ = frame.shape

            thumb = hand.landmark[4]
            index = hand.landmark[8]

            x1,y1 = int(thumb.x*w), int(thumb.y*h)
            x2,y2 = int(index.x*w), int(index.y*h)

            distance = math.hypot(x2-x1,y2-y1)

            cv2.circle(frame,(x1,y1),8,(255,0,255),-1)
            cv2.circle(frame,(x2,y2),8,(255,0,255),-1)
            cv2.line(frame,(x1,y1),(x2,y2),(0,255,0),3)

            # ✋ Open Palm → Mute
            if fingers == [1,1,1,1,1]:

                volume.SetMute(1,None)
                gesture = "Mute"

            # ✊ Closed Fist → Unmute
            elif fingers == [0,0,0,0,0]:

                volume.SetMute(0,None)
                gesture = "Unmute"

            # 🤏 Thumb + Index → Volume Control
            elif fingers[0] == 1 and fingers[1] == 1:

                vol = np.interp(distance,[20,200],[min_vol,max_vol])

                vol_smoothed = prev_volume + smooth_factor*(vol-prev_volume)
                prev_volume = vol_smoothed

                volume.SetMasterVolumeLevel(vol_smoothed,None)

                volume_percent = int(np.interp(vol_smoothed,[min_vol,max_vol],[0,100]))

                gesture = "Volume Control"

            # Volume Bar
            bar = np.interp(volume_percent,[0,100],[400,150])

            cv2.rectangle(frame,(50,150),(85,400),(255,255,255),3)
            cv2.rectangle(frame,(50,int(bar)),(85,400),(0,255,0),-1)

            cv2.putText(frame,f'{volume_percent} %',(40,430),
                        cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,0),3)

            cv2.putText(frame,f'Gesture: {gesture}',(300,50),
                        cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,255),3)

        gesture_recognition = distance_gesture(distance)

        # FPS
        c_time = time.time()
        fps = int(1/(c_time-p_time)) if p_time!=0 else 0
        p_time = c_time

        cv2.putText(frame,f'FPS: {fps}',(10,30),
                    cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,0),2)

        volume_history.append(volume_percent)
        distance_history.append(int(distance))

        metrics["volume"] = volume_percent
        metrics["distance"] = int(distance)
        metrics["fps"] = fps
        metrics["hands"] = hand_count
        metrics["gesture"] = gesture
        metrics["gesture_recognition"] = gesture_recognition
        metrics["volume_history"] = list(volume_history)
        metrics["distance_history"] = list(distance_history)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n'+frame+b'\r\n')

# ================= ROUTES =================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video')
def video():
    return Response(generate_frames(),
    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/metrics')
def get_metrics():
    return jsonify(metrics)

@app.route('/start_camera')
def start_camera():
    global camera_running
    camera_running = True
    return jsonify({"status":"started"})

@app.route('/stop_camera')
def stop_camera():
    global camera_running
    camera_running = False
    return jsonify({"status":"stopped"})

from waitress import serve

if __name__ == "__main__":

    print("Server started")
    print("Open: http://127.0.0.1:5000")

    serve(app, host="127.0.0.1", port=5000)
