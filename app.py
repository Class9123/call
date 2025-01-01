from flask import Flask, render_template_string as rs , request 
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS
socketio = SocketIO(app, cors_allowed_origins="*")

html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Webcam Stream</title>
  <style>
    video, img {
      width: 100vw;
    }
  </style>
</head>
<body>
  <h1>Webcam Stream</h1>
  <video id="webcam-video" autoplay muted playsinline></video>
  <canvas id="canvas" style="display:none;"></canvas>
  <img id="remote-video" src="" alt="Remote Video Stream">

  <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.5.3/socket.io.js"></script>
  <script>
    const videoElement = document.getElementById('webcam-video');
    const remoteImage = document.getElementById('remote-video');
    const canvas = document.getElementById('canvas');
    const context = canvas.getContext('2d');
    const socket = io();

    // Access the webcam feed
    navigator.mediaDevices.getUserMedia({ video: true })
      .then((stream) => {
        videoElement.srcObject = stream;

        // Capture frames from the webcam at a controlled rate
        const FRAME_INTERVAL = 1000 / 30; // 15 FPS
        setInterval(() => {
          if (!videoElement.paused && !videoElement.ended) {
            canvas.width = videoElement.videoWidth;
            canvas.height = videoElement.videoHeight;
            context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

            // Send the frame as a Blob
            canvas.toBlob((blob) => {
              socket.emit('frame', blob);
            }, 'image/jpeg');
          }
        }, FRAME_INTERVAL);
      })
      .catch((error) => {
        console.error('Error accessing the webcam:', error);
      });

    // Update the remote image with broadcasted frames
    socket.on('broadcasted_frame', (data) => {
      const blob = new Blob([data.frame], { type: 'image/jpeg' });
      remoteImage.src = URL.createObjectURL(blob);
    });
  </script>
</body>
</html>

"""

@app.route('/')
def index():
    return rs(html)


@socketio.on('frame')
def handle_video_frame(data):
    data = { "frame":data }
    emit('broadcasted_frame', data ,skip_sid = request.sid , broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
