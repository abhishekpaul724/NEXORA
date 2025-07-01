from flask import Flask, render_template, session, request, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room,emit,send
from datetime import datetime
import os

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY_NEXORA","4i*V;MrT6,17V*")
socketio = SocketIO(app,manage_session=False)

instances=[]
LOG_FILE='nexora.log'

def log(msg):
    with open(LOG_FILE,'a') as f:
        f.write(msg)

@app.route('/')
def access(error=""):
    return render_template('link.html',error=error)

@app.route('/initiate', methods=['POST'])
def retrieve_data():
    global instances
    handle=request.form.get('handle')
    instance=request.form.get('instance')
    action=request.form.get('action')
    if not handle or not instance or not action:
        return render_template('link.html', error="System doesn’t run on ghosts. Fill every field.")
    if action == "deploy":
        if instance not in instances:
            instances.append(instance)
        else:
            return render_template('link.html', error="Instance ID already exists. Existing instances cannot be deployed.")
    elif action == "join":
        if instance not in instances:
            return render_template('link.html', error="Instance ID non-existent.")
    else:
        return render_template('link.html', error="Invalid action, operator.")
    session['handle']=handle
    session['instance']=instance
    return redirect(url_for('room',instance=instance))

@app.route('/instance/<instance>')
def room(instance):
    if 'instance' not in session or session['instance']!=instance:
        return render_template('link.html', error="Entry denied. Authenticate before proceeding.")
    handle=session.get('handle')
    return render_template('instance.html',instance=instance,handle=handle)

@socketio.on('join')
def on_join(data):
    instance=data.get('instance')
    handle=data.get('handle')
    if instance==session['instance'] and handle==session['handle']:
        join_room(instance)
        emit('ack_join',{'msg':f"{handle} has connected to the instance",'time':f"{datetime.now().strftime('%H:%M')}"},to=instance)
    else:
        return

@socketio.on('exit_instance')
def exit_instance(data):
    instance=data.get('instance')
    handle=data.get('handle')
    if instance==session['instance'] and handle==session['handle']:
        leave_room(instance)
        emit("exit_ack",to=request.sid)
        emit("exit_msg",{'handle':f"{handle}",'time':f"{datetime.now().strftime('%H:%M')}"},to=instance)
        session.clear()
    return

@socketio.on('send_message')
def send_message(data):
    instance=data.get('instance')
    handle=data.get('handle')
    msg=data.get('msg')
    if not instance or not handle or not msg:
        return
    elif instance!=session.get('instance') or handle!=session.get('handle'):
        log(f"Unauthenticated packet sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nCredentials: User Handle = {handle} , Instance ID = {instance}\n")
        emit('intrusion', {'msg': 'ALERT: Packet tampering detected. Intruder message request denied.'}, room=request.sid)
        return
    else:
        emit('send_ack',{'handle':f"{handle}", 'msg': f"{msg} ",'time': f"{datetime.now().strftime('%H:%M')}"},to=instance)

if __name__ == '__main__':
    socketio.run(app,host='0.0.0.0',debug=True)