# Deploy Configuration Files

This directory contains all configuration files needed for deploying Worker Connect web application to a production server.

## 📁 Files

### 1. `nginx_worker_connect.conf`
Nginx reverse proxy configuration
- **Location on server:** `/etc/nginx/sites-available/worker-connect`
- **Purpose:** Routes HTTP traffic to Gunicorn, serves static/media files
- **Port:** Listens on 80 (HTTP), proxies to 127.0.0.1:8001

### 2. `worker-connect.service`
Systemd service configuration
- **Location on server:** `/etc/systemd/system/worker-connect.service`
- **Purpose:** Manages Gunicorn as a system service
- **Features:** Auto-restart, runs as www-data user

### 3. `.env.production`
Production environment variables template
- **Location on server:** `/var/www/worker-connect/.env`
- **Purpose:** Configure sensitive settings (SECRET_KEY, DATABASE_URL, etc.)
- **⚠️ NEVER commit actual .env file to git!**

### 4. `deploy.sh`
Automated deployment script
- **Purpose:** Quick deployment updates
- **Usage:** `bash deploy.sh` (run on server)
- **Actions:** Pull code, install deps, migrate, collect static, restart service

## 🚀 Quick Start

See [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md) or [DEPLOYMENT_COMMANDS.md](../DEPLOYMENT_COMMANDS.md) for full deployment instructions.

## ⚙️ Configuration Steps

1. **Copy files to server** during initial setup
2. **Edit domain names** in nginx config
3. **Set strong passwords** in .env file
4. **Enable and start** systemd service
5. **Test configuration** before going live

## 🔧 Customization

- **Change port:** Edit `bind` in `gunicorn_config.py` and upstream in nginx config
- **Add SSL:** Uncomment SSL section in nginx config after getting certificate
- **Adjust workers:** Modify `workers` in `gunicorn_config.py` based on CPU cores
- **Change user:** Update `User` and `Group` in systemd service file

## 📝 Notes

- All log files are stored in `/var/www/worker-connect/logs/`
- Gunicorn runs on port 8001 (not exposed externally)
- Nginx handles all external traffic on port 80/443
- Service auto-restarts on failure
