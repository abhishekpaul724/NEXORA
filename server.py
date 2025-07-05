from flask import Flask, render_template, session, request, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room,emit
from datetime import datetime
from dotenv import load_dotenv
import os

LOG_FILE='nexora.log'
ENV_FILE='nexora.env'

# File Check Logic
if not os.path.isfile(LOG_FILE):
    with open(LOG_FILE,'w') as f:
        f.write(f"{datetime.now().strftime('%d-%m-%Y %H:%M')} Log File Created")
if not os.path.isfile(ENV_FILE):
    with open(ENV_FILE,'w') as f:
        f.write("SECRET_KEY_NEXORA=INJECT_YOUR_SECRET_KEY_HERE\n")

load_dotenv()

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY_NEXORA',"R9:3YaWZ/9:!BOa")
socketio = SocketIO(app,manage_session=False)

instances=[]

def log(msg):
    with open(LOG_FILE,'a') as f:
        f.write(msg)

@app.route('/')
def access(error=""):
    return render_template('link.html',error=error)

# Retrieval of data from the login page
@app.route('/initiate', methods=['POST'])
def retrieve_data():
    global instances
    handle=request.form.get('handle').strip()[:15]
    instance=request.form.get('instance').strip()[:15]
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
    if instance==session.get('instance') and handle==session.get('handle'):
        join_room(instance)
        emit('ack_join',{'msg':f"{handle} has connected to the instance",'time':f"{datetime.now().strftime('%H:%M')}"},to=instance)
    else:
        return

@socketio.on('exit_instance')
def exit_instance(data):
    instance=data.get('instance')
    handle=data.get('handle')
    if instance==session.get('instance') and handle==session.get('handle'):
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