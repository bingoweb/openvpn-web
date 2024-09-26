#!/bin/bash

# Kullanıcıyı root yetkisi ile çalıştırmadıysa uyarı ver
if [ "$EUID" -ne 0 ]
  then echo "Lütfen bu scripti root yetkisiyle çalıştırın (sudo ile)."
  exit
fi

echo "== OpenVPN ve Web Arayüzü Kurulumuna Hoş Geldiniz =="

# Gerekli bağımlılıkların güncellenmesi ve yüklenmesi
echo "Gerekli bağımlılıklar güncelleniyor ve yükleniyor..."
apt-get update
apt-get install -y python3-pip python3-venv python3-dev build-essential libssl-dev libffi-dev python3-setuptools nginx

# Python virtualenv oluşturma ve aktif etme
echo "Python virtual environment oluşturuluyor..."
python3 -m venv openvpn-web-env
source openvpn-web-env/bin/activate

# Flask ve SocketIO modüllerinin kurulması
echo "Flask ve SocketIO kuruluyor..."
pip install wheel
pip install flask flask-socketio eventlet

# OpenVPN kurulumu web arayüzü üzerinden yapılacağı için buradan kaldırıldı
# wget ve ./openvpn-install.sh satırları çıkarıldı.

# Web arayüzü kurulumunu ayarlama
echo "Web arayüzü için ayarlar yapılıyor..."
cp -r /path/to/your/project /var/www/openvpn-web  # Projeyi uygun dizine taşıyoruz

# Nginx ayarları yapılıyor
echo "Nginx yapılandırılıyor..."
cat > /etc/nginx/sites-available/openvpn-web <<EOL
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOL

ln -s /etc/nginx/sites-available/openvpn-web /etc/nginx/sites-enabled/
systemctl restart nginx

# Projenin başlatılması
echo "OpenVPN web arayüzü başlatılıyor..."
cd /var/www/openvpn-web
source openvpn-web-env/bin/activate
nohup python3 app.py &

echo "Kurulum tamamlandı! Web arayüzüne erişmek için tarayıcınızı açın ve sunucu IP'nizi girin."
echo "http://<server_ip> adresine gidin ve OpenVPN kurulumunu tamamlayın."

