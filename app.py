from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO
import subprocess
import os
import socket

app = Flask(__name__)
socketio = SocketIO(app)

# OpenVPN'in kurulup kurulmadığını kontrol etme
def is_openvpn_installed():
    return os.path.exists('/etc/openvpn/server.conf')

# Sunucunun IP adresini almak için fonksiyon
def get_server_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # Google DNS sunucusuna bağlanarak dış IP'yi almak
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"  # Sorun olursa localhost
    finally:
        s.close()
    return ip

# Root URL için yönlendirme
@app.route('/')
def index():
    if is_openvpn_installed():
        # Eğer OpenVPN zaten kurulmuşsa yönetim arayüzüne yönlendir
        return redirect(url_for('control_panel'))
    else:
        # Eğer OpenVPN kurulmamışsa kurulum arayüzüne yönlendir
        return redirect(url_for('setup'))

# Kurulum arayüzü
@app.route('/setup')
def setup():
    server_ip = get_server_ip()  # Sunucu IP'sini al
    return render_template('setup.html', server_ip=server_ip)

# SocketIO üzerinden kurulum işlemi başlatma
@socketio.on('start_installation')
def handle_installation(data):
    try:
        # Kullanıcıdan gelen verileri al
        ip = data.get('ip')
        port = data.get('port')
        protocol = data.get('protocol')
        dns = data.get('dns')

        # OpenVPN kurulum scriptini sudo ile çalıştır
        install_script = f"sudo ./openvpn-install.sh {ip} {port} {protocol} {dns}"
        
        # Kurulum işlemini başlatıyoruz
        process = subprocess.Popen(install_script, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        # Komuttan gelen çıktıları okuyarak web arayüzüne yansıt
        for line in iter(process.stdout.readline, ''):
            socketio.emit('log', {'data': line})  # Gerçek zamanlı çıktı gönder
            socketio.sleep(0.1)  # Akışın düzgün olması için küçük bir bekleme süresi

        process.stdout.close()
        process.wait()

        # Kurulum tamamlandı
        socketio.emit('log', {'data': 'Kurulum tamamlandı!'})
        socketio.emit('redirect', {'url': '/control_panel'})  # Kurulumdan sonra yönetim paneline yönlendirme
    
    except subprocess.CalledProcessError as e:
        socketio.emit('log', {'data': f'Hata: {e}'})
    except Exception as e:
        socketio.emit('log', {'data': f'Hata: {e}'})

# Kurulum tamamlandıktan sonra kontrol paneline yönlendirme
@app.route('/control_panel')
def control_panel():
    vpn_status = check_vpn_status()
    return render_template('index.html', vpn_status=vpn_status)

# VPN durumu kontrol etme fonksiyonu
def check_vpn_status():
    try:
        result = subprocess.run(['systemctl', 'is-active', 'openvpn@server'], stdout=subprocess.PIPE)
        if result.stdout.decode('utf-8').strip() == 'active':
            return True
        else:
            return False
    except Exception as e:
        return False

# VPN başlatma fonksiyonu
@app.route('/start_vpn', methods=['POST'])
def start_vpn_route():
    if start_vpn():
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'VPN başlatılamadı.'})

def start_vpn():
    try:
        subprocess.run(['systemctl', 'start', 'openvpn@server'], check=True)
        return True
    except Exception as e:
        return False

# VPN durdurma fonksiyonu
@app.route('/stop_vpn', methods=['POST'])
def stop_vpn_route():
    if stop_vpn():
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'VPN durdurulamadı.'})

def stop_vpn():
    try:
        subprocess.run(['systemctl', 'stop', 'openvpn@server'], check=True)
        return True
    except Exception as e:
        return False

# VPN loglarını getir
@app.route('/get_logs', methods=['GET'])
def get_logs_route():
    logs = get_vpn_logs()
    if logs:
        return jsonify({'status': 'success', 'logs': logs})
    else:
        return jsonify({'status': 'error', 'message': 'Loglar alınamadı.'})

def get_vpn_logs():
    try:
        with open('/var/log/openvpn/status.log', 'r') as log_file:
            logs = log_file.read()
        return logs
    except Exception as e:
        return None

if __name__ == '__main__':
    socketio.run(app, debug=True)
