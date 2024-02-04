from flask import Flask, render_template, Response, request, jsonify
from flask_pymongo import PyMongo
import cv2
import threading
import time
from bson import ObjectId

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017"  # Replace with your MongoDB URI
mongo = PyMongo(app)

camera = cv2.VideoCapture(0)
# replae with your RTSP link
# for using web cam set it 0
lock = threading.Lock()
paused = False

def generate_frames():
    global camera, lock, paused
    while True:
        with lock:
            if not paused:
                success, frame = camera.read()
                if not success:
                    break
                else:
                    ret, buffer = cv2.imencode('.jpg', frame)
                    frame = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                time.sleep(0.1)  # Sleep to avoid high CPU usage when paused

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pause')
def pause():
    global paused
    paused = True
    return "Stream paused"

@app.route('/resume')
def resume():
    global paused
    paused = False
    return "Stream resumed"

# CRUD API for Overlays using MongoDB
@app.route('/api/overlays', methods=['POST'])
def create_overlay():
    overlay_data = request.json
    overlay_id = mongo.db.overlays.insert_one(overlay_data).inserted_id
    overlay_data['_id'] = str(overlay_id)
    return jsonify(overlay_data)

@app.route('/api/overlays', methods=['GET'])
def get_overlays():
    overlays_data = list(mongo.db.overlays.find())
    return jsonify(overlays_data)

@app.route('/api/overlays/<overlay_id>', methods=['GET'])
def get_overlay(overlay_id):
    overlay = mongo.db.overlays.find_one({"_id": ObjectId(overlay_id)})
    return jsonify(overlay) if overlay else jsonify({'error': 'Overlay not found'}), 404

@app.route('/api/overlays/<overlay_id>', methods=['PUT'])
def update_overlay(overlay_id):
    overlay_data = request.json
    mongo.db.overlays.update_one({"_id": ObjectId(overlay_id)}, {"$set": overlay_data})
    overlay_data['_id'] = overlay_id
    return jsonify(overlay_data)

@app.route('/api/overlays/<overlay_id>', methods=['DELETE'])
def delete_overlay(overlay_id):
    mongo.db.overlays.delete_one({"_id": ObjectId(overlay_id)})
    return jsonify({'message': 'Overlay deleted successfully'})

if __name__ == '__main__':
    app.run(host='0.0.0.0')
