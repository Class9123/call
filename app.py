from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import secrets

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app)

# Dictionary to store client rooms
client_rooms = {}

html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset='utf-8'>
  <meta http-equiv='X-UA-Compatible' content='IE=edge'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>Room-Based Video Calling</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background-color: #f0f0f0;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      height: 100vh;
      margin: 0;
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
    #call-button {
      padding: 12px 24px;
      font-size: 18px;
      background-color: #007bff;
      color: #fff;
      border: none;
      border-radius: 5px;
      cursor: pointer;
      margin-top: 20px;
    }
    #call-button:hover {
      background-color: #0056b3;
    }
    .overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0, 0, 0, 0.7);
      display: none;
      justify-content: center;
      align-items: center;
      z-index: 100;
    }
    .overlay p {
      font-size: 24px;
      color: #fff;
      text-align: center;
    }
    .modal {
      background-color: #fff;
      padding: 24px;
      border-radius: 8px;
      text-align: center;
    }
    .modal button {
      padding: 10px 20px;
      font-size: 18px;
      background-color: #007bff;
      color: #fff;
      border: none;
      border-radius: 5px;
      cursor: pointer;
      margin-top: 20px;
    }
    .modal button:hover {
      background-color: #0056b3;
    }
  </style>
</head>
<body>

  <input type="text" id="room-number" placeholder="Enter Room Number">
  <button id="join-room-button">Join Room</button>

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

  <div class="overlay" id="incoming-call-overlay">
    <div class="modal">
      <p>Incoming Call!</p>
      <button id="accept-call-button">Accept</button>
      <button id="reject-call-button">Reject</button>
    </div>
  </div>

  <button id="call-button">Call</button>

<script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
<script>
  const socket = io();
  let peerConnection = new RTCPeerConnection();
  let localStream;
  let remoteStream = new MediaStream();
  let roomNumber = '';

  let init = async () => {
    localStream = await navigator.mediaDevices.getUserMedia({
      video: true, audio: true
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
        socket.emit('create_offer', { offer: peerConnection.localDescription, room: roomNumber });
      }
    };

    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);
  }

  let createAnswer = async (offer) => {
    peerConnection.onicecandidate = async (event) => {
      if (event.candidate) {
        socket.emit('create_answer', { answer: peerConnection.localDescription, room: roomNumber });
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
    if (data.room === roomNumber && data.sender !== socket.id) {
      showIncomingCallModal(data.sender);
    }
  });

  socket.on('answer_created', async (data) => {
    if (data.room === roomNumber) {
      await addAnswer(data.answer);
    }
  });

  socket.on('call_accepted', async (data) => {
    if (data.room === roomNumber) {
      await createAnswer(data.offer);
    }
  });

  let call = async () => {
    await createOffer();
  }

  document.getElementById('call-button').addEventListener('click', call);
  document.getElementById('join-room-button').addEventListener('click', () => {
    roomNumber = document.getElementById('room-number').value;
    socket.emit('join_room', roomNumber);
  });

  init();

  function showIncomingCallModal(senderId) {
    const modal = document.getElementById('incoming-call-overlay');
    modal.style.display = 'flex';

    const acceptButton = document.getElementById('accept-call-button');
    acceptButton.onclick = async () => {
      modal.style.display = 'none';
      socket.emit('accept_call', { sender: senderId, offer: peerConnection.localDescription, room: roomNumber });
    };

    const rejectButton = document.getElementById('reject-call-button');
    rejectButton.onclick = () => {
      modal.style.display = 'none';
    };
  }
</script>
</body>
</html>
"""

def generate_client_number():
    """Generate a secure number for the client."""
    return secrets.token_hex(4)  # Generate a random 8-character hex number

@socketio.on('connect')
def handle_connect():
    client_number = generate_client_number()
    client_rooms[request.sid] = client_number
    emit('client_number', {'number': client_number}, room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in client_rooms:
        del client_rooms[request.sid]

@app.route('/')
def index():
    return render_template_string(html)

@socketio.on('create_offer')
def handle_create_offer(data):
    emit('offer_created', {'offer': data['offer'], 'sender': request.sid, 'room': data['room']}, room=data['room'])

@socketio.on('create_answer')
def handle_create_answer(data):
    emit('answer_created', {'answer': data['answer'], 'sender': request.sid, 'room': data['room']}, room=data['room'])

@socketio.on('accept_call')
def handle_accept_call(data):
    emit('call_accepted', {'offer': data['offer'], 'sender': request.sid, 'room': data['room']}, room=data['sender'])

@socketio.on('join_room')
def handle_join_room(data):
    join_room(data)
    emit('joined_room', {'room': data}, room=request.sid)

if __name__ == '__main__':
    socketio.run(app, debug=True)
