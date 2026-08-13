# 🚀 COMPLETE DEPLOYMENT COMMAND LIST

## All commands needed to deploy Worker Connect web app to root@72.62.51.225

---

## 📍 PHASE 1: LOCAL MACHINE (Windows PowerShell)

```powershell
# Navigate to project
cd "c:\Users\alhaj\OneDrive\Documents\Projects\Job-seeker-app"

# Create web-only branch
git checkout -b web-deployment

# Remove mobile app
git rm -r React-native-app

# Commit changes
git commit -m "Web-only deployment branch - removed mobile app"

# Push to repository (replace with your repo URL)
git push origin web-deployment
```

---

## 📍 PHASE 2: SERVER - INITIAL SETUP (First Time Only)

```bash
# === CONNECTION ===
ssh root@72.62.51.225

# === SYSTEM UPDATE ===
apt update && apt upgrade -y

# === INSTALL REQUIRED PACKAGES ===
apt install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib redis-server git

# === CREATE DATABASE ===
sudo -u postgres psql -c "CREATE DATABASE worker_connect_db;"
sudo -u postgres psql -c "CREATE USER worker_connect_user WITH PASSWORD 'YourStrongPassword123!';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE worker_connect_db TO worker_connect_user;"

# === CREATE PROJECT DIRECTORY ===
mkdir -p /var/www/worker-connect
cd /var/www/worker-connect

# === CLONE REPOSITORY (replace YOUR_REPO_URL with actual URL) ===
git clone -b web-deployment YOUR_REPO_URL .
# Example: git clone -b web-deployment https://github.com/username/worker-connect.git .

# === CREATE VIRTUAL ENVIRONMENT ===
python3 -m venv venv
source venv/bin/activate

# === INSTALL DEPENDENCIES ===
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

# === GENERATE SECRET KEY ===
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# Copy the output!

# === CREATE .ENV FILE ===
nano .env
```

**Paste this into .env (update values):**
```ini
SECRET_KEY=paste-the-generated-key-here
DEBUG=False
ALLOWED_HOSTS=72.62.51.225,your-domain.com
DATABASE_URL=postgresql://worker_connect_user:YourStrongPassword123!@localhost:5432/worker_connect_db
CORS_ALLOWED_ORIGINS=http://72.62.51.225
CORS_ALLOW_ALL_ORIGINS=False
```

**Save and exit** (Ctrl+X, then Y, then Enter)

```bash
# === RUN MIGRATIONS ===
python manage.py migrate

# === CREATE SUPERUSER ===
python manage.py createsuperuser
# Enter: username, email, password

# === COLLECT STATIC FILES ===
python manage.py collectstatic --noinput

# === CREATE LOG DIRECTORY ===
mkdir -p logs
touch logs/gunicorn-access.log logs/gunicorn-error.log logs/nginx-access.log logs/nginx-error.log

# === SET PERMISSIONS ===
chown -R www-data:www-data /var/www/worker-connect
chmod -R 755 /var/www/worker-connect
chmod -R 775 /var/www/worker-connect/media
chmod -R 775 /var/www/worker-connect/logs

# === CONFIGURE NGINX ===
nano /etc/nginx/sites-available/worker-connect
```

**Paste this Nginx config:**
```nginx
upstream worker_connect_app {
    server 127.0.0.1:8003 fail_timeout=0;
}

server {
    listen 80;
    server_name 72.62.51.225;
    
    client_max_body_size 20M;
    
    access_log /var/www/worker-connect/logs/nginx-access.log;
    error_log /var/www/worker-connect/logs/nginx-error.log;

    location /static/ {
        alias /var/www/worker-connect/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /var/www/worker-connect/media/;
        expires 30d;
    }

    location / {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_pass http://worker_connect_app;
    }
}
```

**Save and exit**

```bash
# === ENABLE NGINX SITE ===
ln -s /etc/nginx/sites-available/worker-connect /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

# === CREATE SYSTEMD SERVICE ===
nano /etc/systemd/system/worker-connect.service
```

**Paste this systemd config:**
```ini
[Unit]
Description=Worker Connect Django Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/worker-connect
Environment="PATH=/var/www/worker-connect/venv/bin"
ExecStart=/var/www/worker-connect/venv/bin/gunicorn --config /var/www/worker-connect/gunicorn_config.py worker_connect.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Save and exit**

```bash
# === START SERVICE ===
systemctl daemon-reload
systemctl enable worker-connect
systemctl start worker-connect

# === CHECK STATUS ===
systemctl status worker-connect

# === TEST WEBSITE ===
curl http://72.62.51.225
```

✅ **Your site should now be live at:** `http://72.62.51.225`

---

## 📍 PHASE 3: FUTURE UPDATES (Anytime You Make Changes)

```bash
# === CONNECT TO SERVER ===
ssh root@72.62.51.225

# === NAVIGATE TO PROJECT ===
cd /var/www/worker-connect

# === ACTIVATE VIRTUAL ENVIRONMENT ===
source venv/bin/activate

# === PULL LATEST CODE ===
git pull origin web-deployment

# === INSTALL NEW DEPENDENCIES (if any) ===
pip install -r requirements.txt

# === RUN NEW MIGRATIONS (if any) ===
python manage.py migrate

# === COLLECT STATIC FILES ===
python manage.py collectstatic --noinput

# === RESTART SERVICE ===
systemctl restart worker-connect

# === VERIFY IT'S WORKING ===
systemctl status worker-connect
```

---

## 🔍 USEFUL MONITORING COMMANDS

```bash
# View live logs
journalctl -u worker-connect -f

# View last 50 log lines
journalctl -u worker-connect -n 50

# Check Gunicorn error log
tail -f /var/www/worker-connect/logs/gunicorn-error.log

# Check Nginx error log
tail -f /var/www/worker-connect/logs/nginx-error.log

# Check service status
systemctl status worker-connect
systemctl status nginx

# Restart services
systemctl restart worker-connect
systemctl restart nginx

# Check what's listening on port 8003
netstat -tuln | grep 8003

# Check disk space
df -h

# Check memory
free -h

# Check running processes
ps aux | grep gunicorn
```

---

## 🐛 TROUBLESHOOTING COMMANDS

```bash
# Service won't start
journalctl -u worker-connect -n 100
tail -100 /var/www/worker-connect/logs/gunicorn-error.log

# Permission issues
chown -R www-data:www-data /var/www/worker-connect
chmod -R 755 /var/www/worker-connect

# Database issues
sudo -u postgres psql -d worker_connect_db -U worker_connect_user

# Test Django directly (bypasses Gunicorn)
cd /var/www/worker-connect
source venv/bin/activate
python manage.py runserver 0.0.0.0:8002
# Then visit: http://72.62.51.225:8002

# Check Python environment
which python
python --version
pip list

# Recollect static files
python manage.py collectstatic --noinput --clear

# Check settings
python manage.py check
python manage.py check --deploy

# Database shell
python manage.py dbshell

# Django shell
python manage.py shell
```

---

## 🔒 OPTIONAL: SSL CERTIFICATE (HTTPS)

```bash
# Install certbot
apt install -y certbot python3-certbot-nginx

# Get certificate (replace with your domain)
certbot --nginx -d your-domain.com -d www.your-domain.com

# Test auto-renewal
certbot renew --dry-run

# Update .env to enable HTTPS redirect
nano /var/www/worker-connect/.env
# Add or change:
# SECURE_SSL_REDIRECT=True
# SESSION_COOKIE_SECURE=True
# CSRF_COOKIE_SECURE=True

# Restart
systemctl restart worker-connect
```

---

## 📊 DATABASE BACKUP COMMANDS

```bash
# Backup database
sudo -u postgres pg_dump worker_connect_db > /backup/worker_connect_$(date +%Y%m%d).sql

# Restore database
sudo -u postgres psql worker_connect_db < /backup/worker_connect_20260409.sql

# Backup media files
tar -czf /backup/media_$(date +%Y%m%d).tar.gz /var/www/worker-connect/media/
```

---

## 🎯 QUICK REFERENCE - COPY & PASTE ALL AT ONCE

**For initial deployment, copy everything between the lines:**

```bash
# ==================== FULL INITIAL DEPLOYMENT ====================
ssh root@72.62.51.225
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib git
sudo -u postgres psql -c "CREATE DATABASE worker_connect_db;"
sudo -u postgres psql -c "CREATE USER worker_connect_user WITH PASSWORD 'ChangeMe123!';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE worker_connect_db TO worker_connect_user;"
mkdir -p /var/www/worker-connect && cd /var/www/worker-connect
# STOP HERE - Replace YOUR_REPO_URL with your actual repository
git clone -b web-deployment YOUR_REPO_URL .
python3 -m venv venv && source venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
# STOP HERE - Create .env file manually with the configuration above
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
mkdir -p logs && chown -R www-data:www-data /var/www/worker-connect
# STOP HERE - Create Nginx and systemd configs as shown above
systemctl daemon-reload && systemctl enable worker-connect && systemctl start worker-connect
systemctl status worker-connect
# ==================== END ====================
```

---

That's it! Your Worker Connect web app is now deployed! 🎉
