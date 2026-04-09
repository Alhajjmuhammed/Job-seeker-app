# 🚀 Worker Connect - Web-Only Deployment Guide

Complete deployment guide for deploying Worker Connect web application to your server at **72.62.51.225**.

---

## 📋 Prerequisites

Your server already has:
- ✅ Ubuntu/Debian Linux
- ✅ SSH access (root@72.62.51.225)
- ✅ Another Django project running (/var/www/restaurant)

---

## 🔧 STEP 1: Prepare Web-Only Branch (On Local Machine)

```bash
# Navigate to project directory
cd "c:\Users\alhaj\OneDrive\Documents\Projects\Job-seeker-app"

# Create and switch to web-only branch
git checkout -b web-deployment

# Remove mobile app folder from this branch
git rm -r React-native-app
git commit -m "Remove mobile app for web-only deployment"

# Remove unnecessary test/verification scripts (optional)
git rm *.py  # Remove root-level Python scripts
git add manage.py worker_connect/ accounts/ workers/ clients/ jobs/ admin_panel/ agents/  # Re-add essential files
git commit -m "Clean up deployment branch"

# Push to your repository
git push origin web-deployment
```

---

## 🖥️ STEP 2: Server Preparation (On Server)

```bash
# SSH into your server
ssh root@72.62.51.225

# Update system packages
apt update && apt upgrade -y

# Install required packages
apt install -y python3 python3-pip python3-venv \
    nginx postgresql postgresql-contrib \
    redis-server git supervisor

# Install certbot for SSL (optional, for later)
apt install -y certbot python3-certbot-nginx

# Create database user and database
sudo -u postgres psql <<EOF
CREATE DATABASE worker_connect_db;
CREATE USER worker_connect_user WITH PASSWORD 'STRONG_PASSWORD_HERE';
ALTER ROLE worker_connect_user SET client_encoding TO 'utf8';
ALTER ROLE worker_connect_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE worker_connect_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE worker_connect_db TO worker_connect_user;
\q
EOF

# Create project directory
mkdir -p /var/www/worker-connect
cd /var/www/worker-connect
```

---

## 📦 STEP 3: Clone and Setup Project

```bash
# Clone your repository (replace with your actual repo URL)
git clone -b web-deployment https://github.com/YOUR_USERNAME/worker-connect.git .

# OR if using different git hosting:
# git clone -b web-deployment YOUR_GIT_REPO_URL .

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install additional production packages
pip install gunicorn psycopg2-binary
```

---

## ⚙️ STEP 4: Configure Environment

```bash
# Create .env file from template
cp deploy/.env.production .env

# Edit .env file with your settings
nano .env
```

**Important: Update these values in .env:**
```bash
# Generate new SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# Copy output and paste into .env

# Update these settings:
SECRET_KEY=paste-generated-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,72.62.51.225
DATABASE_URL=postgresql://worker_connect_user:STRONG_PASSWORD_HERE@localhost:5432/worker_connect_db
```

---

## 🗄️ STEP 5: Setup Database

```bash
# Run migrations
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Create logs directory
mkdir -p /var/www/worker-connect/logs
touch /var/www/worker-connect/logs/gunicorn-access.log
touch /var/www/worker-connect/logs/gunicorn-error.log
touch /var/www/worker-connect/logs/nginx-access.log
touch /var/www/worker-connect/logs/nginx-error.log

# Set proper permissions
chown -R www-data:www-data /var/www/worker-connect
chmod -R 755 /var/www/worker-connect
chmod -R 775 /var/www/worker-connect/media
chmod -R 775 /var/www/worker-connect/logs
```

---

## 🔧 STEP 6: Configure Nginx

```bash
# Copy nginx configuration
cp /var/www/worker-connect/deploy/nginx_worker_connect.conf /etc/nginx/sites-available/worker-connect

# Edit configuration to update domain name
nano /etc/nginx/sites-available/worker-connect
# Change: server_name your-domain.com www.your-domain.com;
# To your actual domain or IP: server_name 72.62.51.225;

# Create symbolic link
ln -s /etc/nginx/sites-available/worker-connect /etc/nginx/sites-enabled/

# Test nginx configuration
nginx -t

# If test passes, reload nginx
systemctl reload nginx
```

---

## 🏃 STEP 7: Setup Systemd Service

```bash
# Copy systemd service file
cp /var/www/worker-connect/deploy/worker-connect.service /etc/systemd/system/

# Reload systemd daemon
systemctl daemon-reload

# Enable service to start on boot
systemctl enable worker-connect

# Start the service
systemctl start worker-connect

# Check status
systemctl status worker-connect
```

---

## 🔒 STEP 8: Setup SSL Certificate (Optional but Recommended)

```bash
# Install SSL certificate using Let's Encrypt
certbot --nginx -d your-domain.com -d www.your-domain.com

# Follow prompts and select redirect HTTP to HTTPS

# Auto-renewal is automatic, test it:
certbot renew --dry-run
```

---

## ✅ STEP 9: Verify Deployment

```bash
# Check if Gunicorn is running
systemctl status worker-connect

# Check logs if issues occur
tail -f /var/www/worker-connect/logs/gunicorn-error.log
tail -f /var/www/worker-connect/logs/nginx-error.log

# Test the website
curl http://72.62.51.225
# OR visit in browser: http://72.62.51.225

# Access admin panel
# http://72.62.51.225/admin/
```

---

## 🔄 STEP 10: Future Updates (When You Push Changes)

```bash
# SSH into server
ssh root@72.62.51.225

# Navigate to project
cd /var/www/worker-connect

# Activate virtual environment
source venv/bin/activate

# Pull latest changes
git pull origin web-deployment

# Install any new dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart application
systemctl restart worker-connect

# Check status
systemctl status worker-connect
```

---

## 📱 Useful Management Commands

```bash
# View service logs
journalctl -u worker-connect -f

# Restart service
systemctl restart worker-connect

# Stop service
systemctl stop worker-connect

# Start service
systemctl start worker-connect

# Reload nginx
systemctl reload nginx

# Restart nginx
systemctl restart nginx

# Check nginx status
systemctl status nginx

# Django shell (for database operations)
cd /var/www/worker-connect
source venv/bin/activate
python manage.py shell

# Create translations
python manage.py compilemessages
```

---

## 🐛 Troubleshooting

### Service won't start:
```bash
# Check logs
journalctl -u worker-connect -n 50
tail -f /var/www/worker-connect/logs/gunicorn-error.log

# Check if port 8001 is in use
netstat -tuln | grep 8001

# Verify Python path
which python
/var/www/worker-connect/venv/bin/python --version
```

### Static files not loading:
```bash
# Recollect static files
cd /var/www/worker-connect
source venv/bin/activate
python manage.py collectstatic --noinput --clear

# Check permissions
ls -la /var/www/worker-connect/staticfiles/
chown -R www-data:www-data /var/www/worker-connect/staticfiles
```

### Database connection issues:
```bash
# Test database connection
sudo -u postgres psql -d worker_connect_db -U worker_connect_user

# Check DATABASE_URL in .env
cat /var/www/worker-connect/.env | grep DATABASE_URL
```

### 502 Bad Gateway:
```bash
# Check if Gunicorn is running
systemctl status worker-connect

# Check nginx upstream
tail -f /var/log/nginx/error.log

# Restart both services
systemctl restart worker-connect
systemctl restart nginx
```

---

## 🌐 Multiple Projects on Same Server

Since you have `/var/www/restaurant` already running, you need:

1. **Different ports** for Gunicorn:
   - Restaurant: 8000 (or whatever it uses)
   - Worker Connect: 8001 (already configured)

2. **Different nginx server blocks**:
   - Different domain names OR
   - Different paths (not recommended)

3. **Different systemd services**:
   - restaurant.service
   - worker-connect.service ✅

Both can run simultaneously without conflicts!

---

## 📊 Performance Monitoring

```bash
# Check system resources
htop

# Check disk space
df -h

# Check memory usage
free -h

# Monitor logs in real-time
tail -f /var/www/worker-connect/logs/gunicorn-access.log

# Database size
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('worker_connect_db'));"
```

---

## 🎯 Summary - Quick Command Reference

```bash
# === ON LOCAL MACHINE ===
git checkout -b web-deployment
git rm -r React-native-app
git commit -m "Web-only deployment"
git push origin web-deployment

# === ON SERVER (Initial Setup) ===
ssh root@72.62.51.225
cd /var/www/worker-connect
git clone -b web-deployment YOUR_REPO_URL .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp deploy/.env.production .env
nano .env  # Edit settings
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
cp deploy/nginx_worker_connect.conf /etc/nginx/sites-available/worker-connect
ln -s /etc/nginx/sites-available/worker-connect /etc/nginx/sites-enabled/
cp deploy/worker-connect.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable worker-connect
systemctl start worker-connect
nginx -t && systemctl reload nginx

# === FUTURE UPDATES ===
cd /var/www/worker-connect
git pull origin web-deployment
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
systemctl restart worker-connect
```

---

## ✅ Deployment Checklist

- [ ] Created web-deployment branch
- [ ] Removed mobile app from branch
- [ ] Pushed to repository
- [ ] Created PostgreSQL database
- [ ] Cloned project to server
- [ ] Created virtual environment
- [ ] Installed dependencies
- [ ] Configured .env file
- [ ] Generated SECRET_KEY
- [ ] Ran migrations
- [ ] Created superuser
- [ ] Collected static files
- [ ] Configured Nginx
- [ ] Created systemd service
- [ ] Started service
- [ ] Tested website loads
- [ ] (Optional) Setup SSL certificate
- [ ] Tested admin panel access

---

**Your Worker Connect web app will be accessible at:** `http://72.62.51.225` or your domain name!

Good luck with deployment! 🚀
