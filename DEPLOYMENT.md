# Worker Connect Deployment Guide

This guide covers deploying the Worker Connect Django application to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Docker Deployment](#docker-deployment)
3. [Manual Server Deployment](#manual-server-deployment)
4. [Environment Configuration](#environment-configuration)
5. [Database Setup](#database-setup)
6. [Static Files & Media](#static-files--media)
7. [SSL/TLS Configuration](#ssltls-configuration)
8. [Monitoring & Logging](#monitoring--logging)
9. [Backup & Recovery](#backup--recovery)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Redis (for caching/sessions)
- Nginx or similar reverse proxy
- Domain name with SSL certificate
- At least 2GB RAM, 2 CPU cores

---

## Docker Deployment

### Docker Compose Setup

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
    command: gunicorn worker_connect.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120
    volumes:
      - static_volume:/app/static
      - media_volume:/app/media
    environment:
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=postgres://postgres:${DB_PASSWORD}@db:5432/workerconnect
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - CSRF_TRUSTED_ORIGINS=${CSRF_TRUSTED_ORIGINS}
    depends_on:
      - db
      - redis
    restart: unless-stopped
    networks:
      - worker_connect_network

  db:
    image: postgres:14-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=workerconnect
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    restart: unless-stopped
    networks:
      - worker_connect_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - worker_connect_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - static_volume:/app/static:ro
      - media_volume:/app/media:ro
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - web
    restart: unless-stopped
    networks:
      - worker_connect_network

  celery:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A worker_connect worker -l info
    environment:
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=postgres://postgres:${DB_PASSWORD}@db:5432/workerconnect
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped
    networks:
      - worker_connect_network

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:

networks:
  worker_connect_network:
    driver: bridge
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "worker_connect.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### Nginx Configuration

Create `nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    include mime.types;
    default_type application/octet-stream;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;
    
    upstream django {
        server web:8000;
    }
    
    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }
    
    server {
        listen 443 ssl http2;
        server_name your-domain.com;
        
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        ssl_prefer_server_ciphers off;
        
        client_max_body_size 10M;
        
        location /static/ {
            alias /app/static/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
        
        location /media/ {
            alias /app/media/;
            expires 7d;
        }
        
        location /api/auth/login/ {
            limit_req zone=login_limit burst=5 nodelay;
            proxy_pass http://django;
            include proxy_params;
        }
        
        location /api/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://django;
            include proxy_params;
        }
        
        location / {
            proxy_pass http://django;
            include proxy_params;
        }
    }
}
```

### Deploy Commands

```bash
# 1. Clone repository
git clone https://github.com/your-org/worker-connect.git
cd worker-connect

# 2. Create production .env file
cp .env.example .env
nano .env  # Edit with production values

# 3. Build and start containers
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# 4. Run migrations
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

# 5. Create superuser
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# 6. Check logs
docker-compose -f docker-compose.prod.yml logs -f web
```

---

## Manual Server Deployment

### System Setup (Ubuntu 22.04)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip \
    postgresql postgresql-contrib nginx redis-server \
    libpq-dev libmagic1 supervisor certbot python3-certbot-nginx

# Create application user
sudo useradd -m -s /bin/bash workerconnect
sudo su - workerconnect
```

### Application Setup

```bash
# Clone and setup
git clone https://github.com/your-org/worker-connect.git
cd worker-connect

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

# Setup environment
cp .env.example .env
nano .env
```

### Gunicorn Service

Create `/etc/systemd/system/workerconnect.service`:

```ini
[Unit]
Description=Worker Connect Gunicorn Daemon
After=network.target

[Service]
User=workerconnect
Group=www-data
WorkingDirectory=/home/workerconnect/worker-connect
ExecStart=/home/workerconnect/worker-connect/venv/bin/gunicorn \
    --workers 4 \
    --bind unix:/home/workerconnect/worker-connect/gunicorn.sock \
    --timeout 120 \
    --access-logfile /var/log/workerconnect/access.log \
    --error-logfile /var/log/workerconnect/error.log \
    worker_connect.wsgi:application

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable workerconnect
sudo systemctl start workerconnect
```

---

## Environment Configuration

### Required Environment Variables

```bash
# Security
SECRET_KEY=your-super-secret-key-at-least-50-chars
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Database
DATABASE_URL=postgres://user:password@localhost:5432/workerconnect

# Email (for password reset, notifications)
EMAIL_HOST=smtp.your-provider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=noreply@your-domain.com

# Frontend URL (for password reset links)
FRONTEND_URL=https://your-domain.com

# Redis (optional, for caching)
REDIS_URL=redis://localhost:6379/0
```

### Generate Secret Key

```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

---

## Database Setup

### PostgreSQL Setup

```bash
# Create database and user
sudo -u postgres psql

CREATE DATABASE workerconnect;
CREATE USER workerconnect_user WITH PASSWORD 'secure_password';
ALTER ROLE workerconnect_user SET client_encoding TO 'utf8';
ALTER ROLE workerconnect_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE workerconnect_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE workerconnect TO workerconnect_user;
\q
```

### Run Migrations

```bash
source venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

---

## Static Files & Media

### Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### Media File Permissions

```bash
# Create media directories
mkdir -p media/worker_profiles media/worker_documents
chmod 755 media media/worker_profiles media/worker_documents
chown -R workerconnect:www-data media/
```

---

## SSL/TLS Configuration

### Using Certbot (Let's Encrypt)

```bash
# Obtain certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal (certbot adds cron job automatically)
sudo certbot renew --dry-run
```

---

## Monitoring & Logging

### Log Locations

- Application logs: `/var/log/workerconnect/`
- Nginx logs: `/var/log/nginx/`
- PostgreSQL logs: `/var/log/postgresql/`

### Health Check Endpoint

The application provides health check endpoints:

- `/api/health/` - Basic health check
- `/api/health/detailed/` - Detailed system status (authenticated)

### Monitoring with Prometheus (Optional)

Add to `requirements.txt`:
```
django-prometheus
```

Configure in `settings.py` and add metrics endpoint.

---

## Backup & Recovery

### Database Backup Script

Create `/home/workerconnect/scripts/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/home/workerconnect/backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="workerconnect_backup_$DATE.sql.gz"

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
PGPASSWORD="your_password" pg_dump -h localhost -U workerconnect_user workerconnect | gzip > "$BACKUP_DIR/$FILENAME"

# Media backup
tar -czf "$BACKUP_DIR/media_$DATE.tar.gz" /home/workerconnect/worker-connect/media/

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed: $FILENAME"
```

### Cron Job for Backups

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /home/workerconnect/scripts/backup.sh >> /var/log/workerconnect/backup.log 2>&1
```

### Restore from Backup

```bash
# Restore database
gunzip -c backup_file.sql.gz | psql -h localhost -U workerconnect_user workerconnect

# Restore media
tar -xzf media_backup.tar.gz -C /
```

---

## Troubleshooting

### Common Issues

**1. 502 Bad Gateway**
```bash
# Check if Gunicorn is running
sudo systemctl status workerconnect

# Check Gunicorn logs
tail -f /var/log/workerconnect/error.log
```

**2. Static files not loading**
```bash
# Re-collect static files
python manage.py collectstatic --clear --noinput

# Check Nginx configuration
sudo nginx -t
```

**3. Database connection errors**
```bash
# Test database connection
psql -h localhost -U workerconnect_user -d workerconnect

# Check PostgreSQL is running
sudo systemctl status postgresql
```

**4. Permission errors**
```bash
# Fix ownership
sudo chown -R workerconnect:www-data /home/workerconnect/worker-connect/

# Fix permissions
chmod -R 755 /home/workerconnect/worker-connect/
```

### Performance Tuning

**Gunicorn Workers**
```
workers = (2 * CPU cores) + 1
```

**PostgreSQL Tuning**
```
shared_buffers = 256MB
effective_cache_size = 768MB
work_mem = 64MB
```

---

## Security Checklist

- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` (50+ characters)
- [ ] HTTPS enabled with valid certificate
- [ ] Database credentials secured
- [ ] File upload validation enabled
- [ ] Rate limiting configured
- [ ] Regular security updates applied
- [ ] Automated backups running
- [ ] Monitoring and alerting setup
- [ ] Access logs reviewed regularly
