#!/bin/bash

echo "🔄 Redémarrage complet de l'application..."

cd /home/ubuntu/dictionnaire-kabye

# Arrêter tout
echo "🛑 Arrêt des processus existants..."
sudo pkill -f gunicorn
sudo systemctl stop nginx

# Attendre
sleep 2

# Vérifier l'environnement
echo "🐍 Vérification de l'environnement Python..."
source venv/bin/activate
python3 --version
pip list | grep -E "(Flask|gunicorn)"

# Démarrer Gunicorn
echo "🚀 Démarrage de Gunicorn..."
gunicorn --bind 0.0.0.0:5000 app:app --daemon

# Attendre le démarrage
sleep 3

# Vérifier Gunicorn
echo "🧪 Test de Gunicorn..."
if curl -s http://localhost:5000/sante > /dev/null; then
    echo "✅ Gunicorn fonctionne sur le port 5000"
else
    echo "❌ Gunicorn ne répond pas - démarrage en mode debug..."
    # Démarrer en mode foreground pour voir les erreurs
    pkill -f gunicorn
    gunicorn --bind 0.0.0.0:5000 app:app
    exit 1
fi

# Redémarrer Nginx
echo "🌐 Redémarrage de Nginx..."
sudo systemctl start nginx

# Test final
echo "🎯 Test final via Nginx..."
sleep 2
if curl -s http://localhost/sante > /dev/null; then
    echo "✅ SUCCÈS! L'application fonctionne correctement"
    echo "🌐 Votre application est accessible sur: http://54.88.199.213"
else
    echo "❌ Nginx ne proxy pas correctement vers Gunicorn"
    echo "📋 Vérification des logs..."
    sudo tail -10 /var/log/nginx/error.log
fi

# Statut final
echo ""
echo "📊 STATUT FINAL:"
ps aux | grep gunicorn | grep -v grep
sudo systemctl status nginx --no-pager | head -5
