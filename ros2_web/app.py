import os
import pty
import subprocess
import select
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- TERMINAL İÇİN GLOBAL DEĞİŞKENLER ---
fd = None
child_pid = None
path = ""
toggle = ""

def terminal_ciktilarini_oku():
    global fd
    max_read_bytes = 1024 * 20
    while True:
        socketio.sleep(0.01)
        if fd:
            timeout_sec = 0
            (data_ready, _, _) = select.select([fd], [], [], timeout_sec)
            if data_ready:
                try:
                    out = os.read(fd, max_read_bytes).decode('utf-8', errors='replace')
                    socketio.emit('terminal-cikti', {'output': out})
                except OSError:
                    pass



# Arayüzden gelen global değişkenler
kayitli_path = ""
kayitli_toggle = "OFF"


@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")

# 1. AŞAMA: OK Butonuna basma
@app.route('/ayarlari-kaydet', methods=['POST'])
def save_settings():
    global kayitli_path, kayitli_toggle
    
    data = request.get_json()
    kayitli_path = data.get("path", "")
    kayitli_toggle = data.get("toggle", "OFF").upper()
    
    return jsonify({"durum": "basarili", "mesaj": f"Settings saved! (Toggle: {kayitli_toggle})"})

# 2. AŞAMA: Çalıştır Butonuna basma
@app.route('/script-calistir', methods=['POST'])
def run_script():
    global fd, kayitli_path, kayitli_toggle
    
    try:
        if not kayitli_path:
            return jsonify({"durum": "hata", "mesaj": "First save a file path!"}), 400
        
        final_path = "/".join(kayitli_path.split("/")[:-1])
        file_name = kayitli_path.split("/")[-1]

        if kayitli_toggle == "OFF":
            # Yeni terminal penceresinde aç (Gnome Terminal)
            komut = ['gnome-terminal', '--', 'bash', '-c', f'cd {final_path} && python3 {file_name}; exec bash']
            subprocess.Popen(komut, cwd=final_path)
            mesaj = "Script has started on a new GNOME terminal"
            
        else:
            # Web arayüzündeki terminalde aç
            if fd is None:
                return jsonify({"durum": "hata", "mesaj": "Web terminal is not initialized!"}), 400
                
            komut_str = f"cd {final_path} && python3 {file_name}\n"
            os.write(fd, komut_str.encode('utf-8'))
            mesaj = "Script has started on the web terminal"
            
        return jsonify({"durum": "basarili", "mesaj": mesaj})
        
    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

# --- 2. WEBSOCKET ROTALARI ---
@socketio.on('connect')
def baglanti_kuruldu():
    global fd, child_pid
    if child_pid is None:
        (child_pid, fd) = pty.fork()
        if child_pid == 0:
            os.environ['TERM'] = 'xterm-256color'
            subprocess.run(['bash'])
        else:
            socketio.start_background_task(target=terminal_ciktilarini_oku)

@socketio.on('terminal-girdi')
def terminal_girdi(data):
    global fd
    if fd:
        os.write(fd, data['input'].encode('utf-8'))



if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)