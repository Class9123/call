html ="""

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
    socketio.run(app)
