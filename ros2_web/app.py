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

import threading
import time
import os
import pty
import subprocess
import select
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import cv2
from flask import Response

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- TERMINAL İÇİN GLOBAL DEĞİŞKENLER (2 ADET) ---
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
            
            kill_cmd = "pkill -f 'ros2 run' ; pkill -f 'uzaktan_kumanda' ; pkill -f 'ffmpeg' ; pkill -f 'mediamtx'"
            if file_name:
                kill_cmd += f" ; pkill -f '{file_name}'"
            
            komut = f"echo '\n🛑 SISTEM DURDURULUYOR...' && {kill_cmd} && echo '✅ Arka plan islemleri temizlendi.'\r\n"
            
            # Acil stop komutunu 1. terminalde çalıştır
            os.write(fd1, komut.encode('utf-8'))
            os.write(fd2, komut.encode('utf-8'))
            
            
            
            return jsonify({"durum": "basarili", "mesaj": "Tüm arka plan işlemleri durduruldu!"})
        else:
            return jsonify({"durum": "hata", "mesaj": "Terminal henüz hazır değil."}), 500
            
    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500

#kumanda komut (uzaktan kumanda) -> YUKARIDAKİ (1.) TERMİNALDE ÇALIŞIR
@app.route('/kumanda-komut', methods=['POST'])
def kumanda_komut_calistir():
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





# --- KAMERA YAYINI İÇİN GLOBAL DEĞİŞKENLER ---
guncel_kare = None
kamera_kilidi = threading.Lock()

def kamerayi_arkaplanda_oku():
    global guncel_kare
    rtsp_url = "rtsp://192.168.88.20:8554/realsense"
    
    import os
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    
    # Bağlantı kurmaya çalışır
    while True:
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        
        # Eğer Jetson'da ffmpeg henüz başlatılmadıysa
        if not cap.isOpened():
            time.sleep(2)
            continue
            
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Bağlantı kurulduğunda kareleri okur
        while True:
            success, frame = cap.read()
            if success:
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ret:
                    with kamera_kilidi:
                        guncel_kare = buffer.tobytes()
            else:
                break
            
            time.sleep(0.01)
        
        cap.release()
        time.sleep(1)

threading.Thread(target=kamerayi_arkaplanda_oku, daemon=True).start()

# --- WEB ARAYÜZÜNE YAYIN GÖNDERME ---
def kamera_karelerini_al():
    global guncel_kare
    while True:
        kare = None
        with kamera_kilidi:
            if guncel_kare is not None:
                kare = guncel_kare
        
        if kare:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + kare + b'\r\n')
        
        socketio.sleep(0.03) 

@app.route('/kamera-yayini')
def video_feed():
    return Response(kamera_karelerini_al(), mimetype='multipart/x-mixed-replace; boundary=frame')


# --- KAMERAYI BAŞLAT (AÇIK OLAN SSH ÜZERİNDEN) ---
@app.route('/ssh-kamera-baslat', methods=['POST'])
def ssh_kamera_baslat():
    global fd2 #2. terminalde calistir
    try:
        if fd2:
            # 1. Mediamtx'i arka planda başlat (çıktıları çöpe at)
            # 2. 2 saniye bekle 
            # 3. ffmpeg komutunu arka planda başlat
            komut = (
                "echo '\n🚀 MediaMTX ve Kamera arka planda baslatiliyor...'\r\n"
                "nohup ./mediamtx > /dev/null 2>&1 &\r\n"
                "sleep 2\r\n"
                "nohup ffmpeg -f v4l2 -input_format yuyv422 -video_size 640x480 -framerate 15 "
                "-thread_queue_size 512 -i /dev/video4 -vf format=yuv420p -c:v libx264 "
                "-preset ultrafast -tune zerolatency -b:v 1M -bufsize 500k -g 15 -keyint_min 15 "
                "-sc_threshold 0 -fflags nobuffer -flags low_delay -avioflags direct "
                "-flush_packets 1 -max_delay 0 -f rtsp -rtsp_transport tcp "
                "rtsp://localhost:8554/realsense > /dev/null 2>&1 &\r\n"
                "echo '✅ Yayin basladi! Terminali kullanmaya devam edebilirsiniz.'\r\n"
            )
            
            os.write(fd2, komut.encode('utf-8'))
            return jsonify({"durum": "basarili", "mesaj": "Kamera komutları Terminal 2'ye yazdırıldı!"})
        else:
            return jsonify({"durum": "hata", "mesaj": "Terminal 2 henüz hazır değil."}), 500
            
    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500



if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
