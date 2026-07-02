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
from dotenv import load_dotenv
load_dotenv()
JETSON_IP = os.getenv("JETSON_IP", "192.168.88.20")

import threading
import time
import os
import pty
import subprocess
import select
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO


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
    global fd1, child_pid1
    max_read_bytes = 1024 * 20
    while True:
        socketio.sleep(0.01)
        if fd1:
            timeout_sec = 0
            (data_ready, _, _) = select.select([fd1], [], [], timeout_sec)
            if data_ready:
                try:
                    out = os.read(fd1, max_read_bytes).decode('utf-8', errors='replace')
                    if not out:
                        fd1 = None
                        child_pid1 = None
                        break
                    socketio.emit('terminal-cikti', {'output': out})
                except OSError:
                    fd1 = None
                    child_pid1 = None
                    break
        else:
            break

# --- 2. TERMINAL OKUMA DÖNGÜSÜ ---
def terminal_ciktilarini_oku_2():
    global fd2, child_pid2
    max_read_bytes = 1024 * 20
    while True:
        socketio.sleep(0.01)
        if fd2:
            timeout_sec = 0
            (data_ready, _, _) = select.select([fd2], [], [], timeout_sec)
            if data_ready:
                try:
                    out = os.read(fd2, max_read_bytes).decode('utf-8', errors='replace')
                    if not out:
                        fd2 = None
                        child_pid2 = None
                        break
                    socketio.emit('terminal-cikti-2', {'output': out})
                except OSError:
                    fd2 = None
                    child_pid2 = None
                    break
        else:
            break

# --- ACİL DURDURMA (EMERGENCY STOP) ---
@app.route('/acil-stop', methods=['POST'])
def acil_stop():
    global fd1, fd2, kayitli_path
    try:
        if fd1:
            file_name = ""
            if kayitli_path:
                file_name = os.path.basename(kayitli_path)
            
            kill_cmd = "pkill -f 'ros2 run' ; pkill -f 'uzaktan_kumanda' ; pkill -f 'ffmpeg' ; pkill -f 'mediamtx' ; pkill -f 'gst-launch-1.0'"
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
sensor_bg_task_started = False

@socketio.on('connect')
def baglanti_kuruldu():
    global fd1, child_pid1, fd2, child_pid2, sensor_bg_task_started
    
    if not sensor_bg_task_started:
        sensor_bg_task_started = True
        socketio.start_background_task(target=sensor_verisi_gonder_loop)

    
    # 1. Terminal PTY
    if child_pid1 is None:
        (child_pid1, fd1) = pty.fork()
        if child_pid1 == 0:
            os.environ['TERM'] = 'xterm-256color'
            os.execvp('bash', ['bash'])
        else:
            socketio.start_background_task(target=terminal_ciktilarini_oku_1)

    # 2. Terminal PTY
    if child_pid2 is None:
        (child_pid2, fd2) = pty.fork()
        if child_pid2 == 0:
            os.environ['TERM'] = 'xterm-256color'
            os.execvp('bash', ['bash'])
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




# --- KAMERAYI BAŞLAT (AÇIK OLAN SSH ÜZERİNDEN) ---
@app.route('/ssh-kamera-baslat', methods=['POST'])
def ssh_kamera_baslat():
    global fd2
    try:
        if fd2:
            # GStreamer pipeline'ları görüntüyü Jetson içindeki yerel sunucuya (localhost) basar.
            # Bu yüzden buradaki 'localhost:8554' adreslerini DEĞİŞTİRMİYORUZ. Doğru kurgu budur.
            komut = (
                "echo '\n🚀 MediaMTX ve Çoklu GStreamer Yayını (7 Kamera) başlatılıyor...'\r\n"
                "nohup ./mediamtx > /dev/null 2>&1 &\r\n"
                "sleep 2\r\n"
                
                # --- GÖVDE (SÜRÜŞ) KAMERALARI ---
                "nohup gst-launch-1.0 v4l2src device=/dev/video0 ! video/x-raw,width=640,height=480,framerate=30/1 ! videoconvert ! x264enc tune=zerolatency bitrate=600 speed-preset=ultrafast ! rtph264pay ! udpsink host=127.0.0.1 port=8000 > /dev/null 2>&1 &\r\n"
                "nohup gst-launch-1.0 v4l2src device=/dev/video1 ! video/x-raw,width=640,height=480,framerate=30/1 ! videoconvert ! x264enc tune=zerolatency bitrate=600 speed-preset=ultrafast ! rtph264pay ! udpsink host=127.0.0.1 port=8001 > /dev/null 2>&1 &\r\n"
                "nohup gst-launch-1.0 v4l2src device=/dev/video2 ! video/x-raw,width=640,height=480,framerate=30/1 ! videoconvert ! x264enc tune=zerolatency bitrate=600 speed-preset=ultrafast ! rtph264pay ! udpsink host=127.0.0.1 port=8002 > /dev/null 2>&1 &\r\n"
                
                # --- ROBOT KOL KAMERALARI ---
                "nohup gst-launch-1.0 v4l2src device=/dev/video3 ! video/x-raw,width=640,height=480,framerate=30/1 ! videoconvert ! x264enc tune=zerolatency bitrate=600 speed-preset=ultrafast ! rtph264pay ! udpsink host=127.0.0.1 port=8003 > /dev/null 2>&1 &\r\n"
                "nohup gst-launch-1.0 v4l2src device=/dev/video4 ! video/x-raw,width=640,height=480,framerate=30/1 ! videoconvert ! x264enc tune=zerolatency bitrate=600 speed-preset=ultrafast ! rtph264pay ! udpsink host=127.0.0.1 port=8004 > /dev/null 2>&1 &\r\n"
                "nohup gst-launch-1.0 v4l2src device=/dev/video5 ! video/x-raw,width=640,height=480,framerate=30/1 ! videoconvert ! x264enc tune=zerolatency bitrate=600 speed-preset=ultrafast ! rtph264pay ! udpsink host=127.0.0.1 port=8005 > /dev/null 2>&1 &\r\n"
                "nohup gst-launch-1.0 v4l2src device=/dev/video6 ! video/x-raw,width=640,height=480,framerate=30/1 ! videoconvert ! x264enc tune=zerolatency bitrate=600 speed-preset=ultrafast ! rtph264pay ! udpsink host=127.0.0.1 port=8006 > /dev/null 2>&1 &\r\n"
                
                "echo '✅ 3 Gövde ve 4 Robot Kol yayını başarıyla başlatıldı!'\r\n"
            )
            os.write(fd2, komut.encode('utf-8'))
            return jsonify({"durum": "basarili", "mesaj": f"7 adet kamera komutu {JETSON_IP} terminaline gönderildi!"})
        else:
            return jsonify({"durum": "hata", "mesaj": "Terminal 2 hazır değil."}), 500
    except Exception as e:
        return jsonify({"durum": "hata", "mesaj": str(e)}), 500



# --- ROS 2 SENSÖR VERİSİ DİNLEYİCİSİ ---
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json

# Thread'ler arası güvenli veri aktarımı için global değişken
guncel_sensor_verisi = None

class WebSensorSubscriber(Node):
    def __init__(self):
        super().__init__('web_sensor_subscriber')
        self.subscription = self.create_subscription(
            String,
            '/sensor_verisi',
            self.listener_callback,
            10)

    def listener_callback(self, msg):
        global guncel_sensor_verisi
        try:
            data = json.loads(msg.data)
            guncel_sensor_verisi = data
        except json.JSONDecodeError:
            pass

def ros2_thread():
    try:
        rclpy.init(args=None)
        sensor_subscriber = WebSensorSubscriber()
        rclpy.spin(sensor_subscriber)
        sensor_subscriber.destroy_node()
        rclpy.shutdown()
    except Exception as e:
        print(f"ROS 2 dinleyici baslatilamadi: {e}")

# ROS 2 node'unu her durumda sorunsuz çalışması için native thread ile başlatıyoruz
threading.Thread(target=ros2_thread, daemon=True).start()

# Arayüze veri yollama işlemini Flask-SocketIO'nun kendi güvenli thread yapısına bırakıyoruz
def sensor_verisi_gonder_loop():
    global guncel_sensor_verisi
    while True:
        socketio.sleep(0.5)
        if guncel_sensor_verisi:
            # Gelen veriyi web arayüzüne gönderiyoruz
            socketio.emit('sensor_verisi', {
                'sicaklik': guncel_sensor_verisi.get('sicaklik', '--'),
                'basinc': guncel_sensor_verisi.get('basinc', '--'),
                'mesafe': guncel_sensor_verisi.get('mesafe', '--')
            })
            guncel_sensor_verisi = None

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
