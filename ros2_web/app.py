"""
===AÇIKLAMA===

-Terminalde dosyanın bulunduğu dizine git
-"python3 app.py" ile çalıştır
-Terminaldeki linke tıkla

KULLANIM:
-Sağdaki alana çalıştırmak istediğin dosyanın tam pathini yaz
-Toggle ayarla (webdeki mi yoksa lokaldeki mi terminali kullanmak istiyorsun)
-"Save" butonuna bastıktan sonra "Run" ile çalıştır

"""

import os
import pty
import subprocess
import select
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- TERMINAL İÇİN GLOBAL DEĞİŞKENLER ---
fd1 = None
child_pid1 = None

fd2 = None
child_pid2 = None

# Arayüzden gelen global değişkenler
kayitli_path = ""
kayitli_toggle = "OFF"

# --- 1. TERMINAL OKUMA DÖNGÜSÜ ---
def terminal_ciktilarini_oku_1():
    global fd1
    max_read_bytes = 1024 * 20
    while True:
        socketio.sleep(0.01)
        if fd1:
            timeout_sec = 0
            (data_ready, _, _) = select.select([fd1], [], [], timeout_sec)
            if data_ready:
                try:
                    out = os.read(fd1, max_read_bytes).decode('utf-8', errors='replace')
                    socketio.emit('terminal-cikti', {'output': out})
                except OSError:
                    pass

# --- 2. TERMINAL OKUMA DÖNGÜSÜ ---
def terminal_ciktilarini_oku_2():
    global fd2
    max_read_bytes = 1024 * 20
    while True:
        socketio.sleep(0.01)
        if fd2:
            timeout_sec = 0
            (data_ready, _, _) = select.select([fd2], [], [], timeout_sec)
            if data_ready:
                try:
                    out = os.read(fd2, max_read_bytes).decode('utf-8', errors='replace')
                    socketio.emit('terminal-cikti-2', {'output': out})
                except OSError:
                    pass

# --- ACİL DURDURMA (EMERGENCY STOP) ---
@app.route('/acil-stop', methods=['POST'])
def acil_stop():
    global fd1, fd2, kayitli_path
    try:
        if fd1:
            file_name = ""
            if kayitli_path:
                file_name = os.path.basename(kayitli_path)
            
            kill_cmd = "pkill -f 'ros2 run' ; pkill -f 'uzaktan_kumanda'"
            if file_name:
                kill_cmd += f" ; pkill -f '{file_name}'"
            
            komut = f"echo '\n🛑 SISTEM DURDURULUYOR...' && {kill_cmd} && echo '✅ Arka plan islemleri temizlendi.'\r\n"
            
            # Acil stop komutunu 1. terminalde çalıştır
            os.write(fd1, komut.encode('utf-8'))
        
            return jsonify({"durum": "basarili", "mesaj": "Tüm arka plan işlemleri durduruldu!"})
        else:
            return jsonify({"durum": "hata", "mesaj": "Terminal henüz hazır değil."}), 500
            
    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

#sabit komut (uzaktan kumanda) -> (1.) TERMİNALDE ÇALIŞIR
@app.route('/sabit-komut', methods=['POST'])
def sabit_komut_calistir():
    global fd1
    try:
        if fd1:
            sabit_kod = "echo '\n🎮 [uzaktan_kumanda] arka planda baslatildi...' && nohup ros2 run motor_kontrol uzaktan_kumanda > /dev/null 2>&1 &\r\n"
            os.write(fd1, sabit_kod.encode('utf-8'))
            
            return jsonify({"durum": "basarili", "mesaj": "Uzaktan kumanda arka planda başlatıldı (Terminal 1)!"})
        else:
            return jsonify({"durum": "hata", "mesaj": "Terminal 1 henüz hazır değil."}), 500
            
    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

#jetson kodu -> (2.) TERMINALDE CALISIR
@app.route('/jetson-kodu', methods=['POST'])
def jetson_kodu():
    global fd2
    try:
        if fd2:
            jetson_kod = "echo '\n🎮 [jetson] baslatildi...' && ros2 run motor_kontrol uzaktan_kumanda\r\n"
            os.write(fd2, jetson_kod.encode('utf-8'))
            
            return jsonify({"durum": "basarili", "mesaj": "Jetson kodu  başlatıldı (Terminal 2)!"})
        else:
            return jsonify({"durum": "hata", "mesaj": "Terminal 2 henüz hazır değil."}), 500
            
    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")

# --- WEBSOCKET ROTALARI (PTY BAŞLATMA) ---
@socketio.on('connect')
def baglanti_kuruldu():
    global fd1, child_pid1, fd2, child_pid2
    
    # 1. Terminal PTY
    if child_pid1 is None:
        (child_pid1, fd1) = pty.fork()
        if child_pid1 == 0:
            os.environ['TERM'] = 'xterm-256color'
            subprocess.run(['bash'])
        else:
            socketio.start_background_task(target=terminal_ciktilarini_oku_1)

    # 2. Terminal PTY
    if child_pid2 is None:
        (child_pid2, fd2) = pty.fork()
        if child_pid2 == 0:
            os.environ['TERM'] = 'xterm-256color'
            subprocess.run(['bash'])
        else:
            socketio.start_background_task(target=terminal_ciktilarini_oku_2)

# Terminal 1'den gelen klavye girdileri
@socketio.on('terminal-girdi')
def terminal_girdi_1(data):
    global fd1
    if fd1:
        os.write(fd1, data['input'].encode('utf-8'))

# Terminal 2'den gelen klavye girdileri
@socketio.on('terminal-girdi-2')
def terminal_girdi_2(data):
    global fd2
    if fd2:
        os.write(fd2, data['input'].encode('utf-8'))

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
