from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app)


html = """
<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <meta http-equiv='X-UA-Compatible' content='IE=edge'>
  <title>WebRTC 1</title>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
  <style>
    body {
      font-family: Arial, sans-serif;
      background-color: #f0f0f0;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
    }
    #videos {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 20px;
    }
    .video-container {
      border: 2px solid #333;
      border-radius: 8px;
      overflow: hidden;
    }
    .video-container video {
      width: 300px;
      height: 225px;
      object-fit: cover;
    }
  </style>
</head>
<body>

  <div id="videos">
    <div class="video-container">
      <video class="video-player" id="local-video" autoplay playsinline muted></video>
      <p>Your Video</p>
    </div>
    <div class="video-container">
      <video class="video-player" id="remote-video" autoplay playsinline></video>
      <p>Your Friend's Video</p>
    </div>
  </div>

  <div class="step">
    <p>
      <strong>Step 1:</strong> Click "Call" to start the video call.
    </p>
    <button id="call-button">Call</button>
  </div>

<script>
  const socket = io();
  let peerConnection = new RTCPeerConnection();
  let localStream;
  let remoteStream = new MediaStream();

  let init = async () => {
    localStream = await navigator.mediaDevices.getUserMedia({
      video: true, audio: false
    });
    document.getElementById('local-video').srcObject = localStream;

    localStream.getTracks().forEach((track) => {
      peerConnection.addTrack(track, localStream);
    });

    peerConnection.ontrack = (event) => {
      event.streams[0].getTracks().forEach((track) => {
        remoteStream.addTrack(track);
      });
      document.getElementById('remote-video').srcObject = remoteStream;
    };
  }

  let createOffer = async () => {
    peerConnection.onicecandidate = async (event) => {
      if (event.candidate) {
        socket.emit('create_offer', peerConnection.localDescription);
      }
    };

    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);
  }

  let createAnswer = async (offer) => {
    peerConnection.onicecandidate = async (event) => {
      if (event.candidate) {
        socket.emit('create_answer', peerConnection.localDescription);
      }
    };

    await peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
    const answer = await peerConnection.createAnswer();
    await peerConnection.setLocalDescription(answer);
  }

  let addAnswer = async (answer) => {
    if (!peerConnection.currentRemoteDescription) {
      await peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
    }
  }

  socket.on('offer_created', async (data) => {
    if (!peerConnection.currentRemoteDescription) {
      await createAnswer(data);
    }
  });

  socket.on('answer_created', async (data) => {
    await addAnswer(data);
  });

  let call = async () => {
    await createOffer();
  }

  document.getElementById('call-button').addEventListener('click', call);

  init();
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(html)

@socketio.on('create_offer')
def handle_create_offer(data):
    emit('offer_created', data, broadcast=True)

@socketio.on('create_answer')
def handle_create_answer(data):
    emit('answer_created', data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
