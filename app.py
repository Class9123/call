html ="""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Video calling</title>
<style>
  #call {
  display: inline-flex;
  background: linear-gradient(214.84deg, rgb(15, 9, 68) 20.52%, rgb(9, 4, 50) 89.43%);
  transition: background 1s;
  cursor: pointer;
  padding: 5px 10px;
  border-radius: 5px;
  margin-top: 5px;
  color: white;
}

#call:hover {
  background: linear-gradient(90deg, rgb(110, 42, 255) 0%, rgb(148, 98, 255) 100%);
}

.local-video {
  position: fixed;
  right: 50px;
  bottom: 50px;
}

#localVideo {
  width: 150px;
  height: 150px;
}

.remote-video {}

#remoteVideo {
  width: 250px;
  height: 250px;
}

#userId {
  display: none;
}

.user-item {
  display: inline-flex;
  cursor: pointer;
  background: transparent;
  padding: 5px 10px;
  margin-bottom: 5px;
  border-radius: 2px;
  transition: background 1s;
  border: 1px solid rgb(110, 42, 255);
}

.user-item:hover {
  background: rgb(110, 42, 255);
}

.user-item--touched {
  background: linear-gradient(90deg, rgb(110, 42, 255) 0%, rgb(148, 98, 255) 100%);
}
</style>
</head>
<body>
<div>
    <div id="userId"></div>
    <div class="remote-video">
        <div>Call:</div>
        <video id="remoteVideo" playsinline autoplay></video>
    </div>
    <div class="local-video">
        <div>Me:</div>
        <video id="localVideo" playsinline autoplay muted></video>
    </div>

    <div>
        Users:
    </div>
    <div id="usersList">
        No users connected
    </div>

    <div>
        <div id="call">Call</button>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/socket.io-client@2/dist/socket.io.js"></script>
<script>
 // Creating the peer
const peer = new RTCPeerConnection({
  iceServers: [
    {
      urls: "stun:stun.stunprotocol.org"
    }
  ]
});

// Connecting to socket
const socket = io();

const onSocketConnected = async () => {
  const constraints = {
    audio: true,
    video: true
  };
  const stream = await navigator.mediaDevices.getUserMedia(constraints);
  document.querySelector('#localVideo').srcObject = stream;
  stream.getTracks().forEach(track => peer.addTrack(track, stream));
}

let callButton = document.querySelector('#call');

// Handle call button
callButton.addEventListener('click', async () => {
  const localPeerOffer = await peer.createOffer();
  await peer.setLocalDescription(new RTCSessionDescription(localPeerOffer));
  
  sendMediaOffer(localPeerOffer);
});

// Create media offer
socket.on('mediaOffer', async (data) => {
  await peer.setRemoteDescription(new RTCSessionDescription(data.offer));
  const peerAnswer = await peer.createAnswer();
  await peer.setLocalDescription(new RTCSessionDescription(peerAnswer));

  sendMediaAnswer(peerAnswer, data);
});

// Create media answer
socket.on('mediaAnswer', async (data) => {
  await peer.setRemoteDescription(new RTCSessionDescription(data.answer));
});

// ICE layer
peer.onicecandidate = (event) => {
  sendIceCandidate(event);
}

socket.on('remotePeerIceCandidate', async (data) => {
  try {
    const candidate = new RTCIceCandidate(data.candidate);
    await peer.addIceCandidate(candidate);
  } catch (error) {
    // Handle error, this will be rejected very often
  }
})

peer.addEventListener('track', (event) => {
  const [stream] = event.streams;
  document.querySelector('#remoteVideo').srcObject = stream;
})

let selectedUser;

const sendMediaAnswer = (peerAnswer, data) => {
  socket.emit('mediaAnswer', {
    answer: peerAnswer,
    from: socket.id,
    to: data.from
  })
}

const sendMediaOffer = (localPeerOffer) => {
  socket.emit('mediaOffer', {
    offer: localPeerOffer,
    from: socket.id,
    to: selectedUser
  });
};

const sendIceCandidate = (event) => {
  socket.emit('iceCandidate', {
    to: selectedUser,
    candidate: event.candidate,
  });
}

const onUpdateUserList = ({ userIds }) => {
  const usersList = document.querySelector('#usersList');
  const usersToDisplay = userIds.filter(id => id !== socket.id);

  usersList.innerHTML = '';
  
  usersToDisplay.forEach(user => {
    const userItem = document.createElement('div');
    userItem.innerHTML = user;
    userItem.className = 'user-item';
    userItem.addEventListener('click', () => {
      const userElements = document.querySelectorAll('.user-item');
      userElements.forEach((element) => {
        element.classList.remove('user-item--touched');
      })
      userItem.classList.add('user-item--touched');
      selectedUser = user;
    });
    usersList.appendChild(userItem);
  });
};
socket.on('update-user-list', onUpdateUserList);

const handleSocketConnected = async () => {
  onSocketConnected();
  socket.emit('requestUserList');
};

socket.on('connect', handleSocketConnected);
</script>
</body>
</html>


"""

from flask import Flask, render_template_string as rs
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

connected_users = []

@app.route('/')
def index():
    return rs(html)  # You can replace this with the appropriate template.

@socketio.on('connect')
def handle_connect():
    connected_users.append(request.sid)
    emit('update-user-list', {'userIds': connected_users}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    connected_users.remove(request.sid)
    emit('update-user-list', {'userIds': connected_users}, broadcast=True)

@socketio.on('mediaOffer')
def handle_media_offer(data):
    emit('mediaOffer', {'from': data['from'], 'offer': data['offer']}, room=data['to'])

@socketio.on('mediaAnswer')
def handle_media_answer(data):
    emit('mediaAnswer', {'from': data['from'], 'answer': data['answer']}, room=data['to'])

@socketio.on('iceCandidate')
def handle_ice_candidate(data):
    emit('remotePeerIceCandidate', {'candidate': data['candidate']}, room=data['to'])

@socketio.on('requestUserList')
def handle_request_user_list():
    emit('update-user-list', {'userIds': connected_users})
    emit('update-user-list', {'userIds': connected_users}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app , debug=True)
