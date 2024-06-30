from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit, join_room
from uuid import uuid4

app = Flask(__name__)
socketio = SocketIO(app)

users = {}

@app.route('/')
def index():
    html_code = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Video Call</title>
        <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    </head>
    <body>
        <div>
            <input id="roomName" type="text" placeholder="Enter room name">
            <button id="createRoomBtn">Create Room</button>
            <button id="joinRoomBtn">Join Room</button>
        </div>
        <video id="localVideo" autoplay playsinline muted></video>
        <video id="remoteVideo" autoplay playsinline></video>

        <script>
            const socket = io();
            let roomId;
            const userId = Math.random().toString(36).substring(7);
            let localStream;
            let peerConnection;

            const config = {
                iceServers: [
                    { urls: 'stun:stun.l.google.com:19302' }
                ]
            };

            const localVideo = document.getElementById('localVideo');
            const remoteVideo = document.getElementById('remoteVideo');
            const roomNameInput = document.getElementById('roomName');
            const createRoomBtn = document.getElementById('createRoomBtn');
            const joinRoomBtn = document.getElementById('joinRoomBtn');

            createRoomBtn.addEventListener('click', () => {
                roomId = roomNameInput.value;
                startVideoCall();
            });

            joinRoomBtn.addEventListener('click', () => {
                roomId = roomNameInput.value;
                startVideoCall();
            });

            function startVideoCall() {
                navigator.mediaDevices.getUserMedia({ video: true, audio: true })
                    .then(stream => {
                        localVideo.srcObject = stream;
                        localStream = stream;

                        socket.emit('join', { room: roomId, user_id: userId });

                        socket.on('ready', () => {
                            peerConnection = new RTCPeerConnection(config);

                            localStream.getTracks().forEach(track => {
                                peerConnection.addTrack(track, localStream);
                            });

                            peerConnection.onicecandidate = event => {
                                if (event.candidate) {
                                    socket.emit('signal', {
                                        room: roomId,
                                        user_id: userId,
                                        signal: { 'candidate': event.candidate }
                                    });
                                }
                            };

                            peerConnection.ontrack = event => {
                                remoteVideo.srcObject = event.streams[0];
                            };

                            peerConnection.createOffer()
                                .then(offer => {
                                    return peerConnection.setLocalDescription(offer);
                                })
                                .then(() => {
                                    socket.emit('signal', {
                                        room: roomId,
                                        user_id: userId,
                                        signal: { 'sdp': peerConnection.localDescription }
                                    });
                                });
                        });

                        socket.on('signal', data => {
                            if (data.user_id === userId) return;

                            const signal = data.signal;

                            if (signal.sdp) {
                                peerConnection.setRemoteDescription(new RTCSessionDescription(signal.sdp))
                                    .then(() => {
                                        if (signal.sdp.type === 'offer') {
                                            peerConnection.createAnswer()
                                                .then(answer => {
                                                    return peerConnection.setLocalDescription(answer);
                                                })
                                                .then(() => {
                                                    socket.emit('signal', {
                                                        room: roomId,
                                                        user_id: userId,
                                                        signal: { 'sdp': peerConnection.localDescription }
                                                    });
                                                });
                                        }
                                    });
                            } else if (signal.candidate) {
                                peerConnection.addIceCandidate(new RTCIceCandidate(signal.candidate));
                            }
                        });
                    })
                    .catch(error => {
                        console.error('Error accessing media devices.', error);
                    });
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html_code)

@socketio.on('join')
def on_join(data):
    room = data['room']
    user_id = data['user_id']
    print(f'User {user_id} joined room {room}')
    join_room(room)

    if room in users:
        users[room].append(user_id)
    else:
        users[room] = [user_id]

    if len(users[room]) == 2:
        print(f'Two users in room {room}. Signaling readiness.')
        socketio.emit('ready', room=room)

@socketio.on('signal')
def on_signal(data):
    room = data['room']
    user_id = data['user_id']
    signal_data = data['signal']
    print(f'Signal received from user {user_id} in room {room}: {signal_data}')
    other_user = [user for user in users[room] if user != user_id][0]
    emit('signal', {'user_id': other_user, 'signal': signal_data}, room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)
