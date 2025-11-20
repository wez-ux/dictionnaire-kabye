#!/bin/bash

# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer Python et pip
sudo apt install -y python3 python3-pip python3-venv nginx

# Créer le dossier de l'application
mkdir -p /home/ubuntu/dictionnaire-kabye
cd /home/ubuntu/dictionnaire-kabye

# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Donner les permissions au script
chmod +x run.sh

# Configurer Nginx
sudo tee /etc/nginx/sites-available/dictionnaire-kabye > /dev/null <<EOF

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
EOF

# Activer le site Nginx
sudo ln -sf /etc/nginx/sites-available/dictionnaire-kabye /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Redémarrer Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx

# Démarrer l'application
./run.sh

echo "✅ Installation terminée !"
echo "🌐 Votre application est accessible sur: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
