from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit, join_room, disconnect
from flask_cors import CORS
import secrets  # For generating secure tokens

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app)

# Dictionary to store client tokens
client_tokens = {}

html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset='utf-8'>
  <meta http-equiv='X-UA-Compatible' content='IE=edge'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>Unique Token Video Calling</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background-color: #f0f0f0;
      display: flex;
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
      position: absolute;
      top: 20px;
      right: 20px;
      z-index: 10;
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

  <button id="call-button">Call</button>

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

<script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
<script>
  const socket = io();
  let peerConnection = new RTCPeerConnection();
  let localStream;
  let remoteStream = new MediaStream();
  let clientToken = "{{ client_token }}";  // Token passed from server

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
        socket.emit('create_offer', { offer: peerConnection.localDescription, token: clientToken });
      }
    };

    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);
  }

  let createAnswer = async (offer) => {
    peerConnection.onicecandidate = async (event) => {
      if (event.candidate) {
        socket.emit('create_answer', { answer: peerConnection.localDescription, token: clientToken });
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
    if (!peerConnection.currentRemoteDescription && data.sender !== socket.id && data.token === clientToken) {
      showIncomingCallModal(data.sender);
    }
  });

  socket.on('answer_created', async (data) => {
    if (data.token === clientToken) {
      await addAnswer(data.answer);
    }
  });

  socket.on('call_accepted', async (data) => {
    if (data.token === clientToken) {
      await createAnswer(data.offer);
    }
  });

  let call = async () => {
    await createOffer();
  }

  document.getElementById('call-button').addEventListener('click', call);

  init();

  function showIncomingCallModal(senderId) {
    const modal = document.getElementById('incoming-call-overlay');
    modal.style.display = 'flex';

    const acceptButton = document.getElementById('accept-call-button');
    acceptButton.onclick = async () => {
      modal.style.display = 'none';
      socket.emit('accept_call', { sender: senderId, offer: peerConnection.localDescription, token: clientToken });
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

def generate_client_token():
    """Generate a secure token for the client."""
    return secrets.token_urlsafe(8)  # Generate an 8-character token

@socketio.on('connect')
def handle_connect():
    client_token = generate_client_token()
    client_tokens[request.sid] = client_token
    emit('client_token', {'token': client_token}, room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in client_tokens:
        del client_tokens[request.sid]

@app.route('/')
def index():
    client_token = client_tokens.get(request.sid)
    if not client_token:
        return "Error: Unauthorized access"  # Handle unauthorized access
    return render_template_string(html, client_token=client_token)

@socketio.on('create_offer')
def handle_create_offer(data):
    emit('offer_created', {'offer': data['offer'], 'sender': request.sid, 'token': data['token']}, room=data['token'])

@socketio.on('create_answer')
def handle_create_answer(data):
    emit('answer_created', {'answer': data['answer'], 'sender': request.sid, 'token': data['token']}, room=data['token'])

@socketio.on('accept_call')
def handle_accept_call(data):
    emit('call_accepted', {'offer': data['offer'], 'sender': request.sid, 'token': data['token']}, room=data['sender'])

if __name__ == '__main__':
    socketio.run(app, debug=True)
