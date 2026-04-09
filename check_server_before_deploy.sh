#!/bin/bash
# Safe Server Diagnostic Script - READ ONLY
# This script checks your existing setup WITHOUT making any changes
# Run on server: bash check_server_before_deploy.sh

echo "============================================="
echo "🔍 SERVER DIAGNOSTIC - READ ONLY CHECK"
echo "============================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. Check existing projects in /var/www/
echo -e "${BLUE}📁 1. Existing Projects in /var/www/${NC}"
echo "---------------------------------------------"
ls -la /var/www/
echo ""

# 2. Check Nginx status and configuration
echo -e "${BLUE}🌐 2. Nginx Status${NC}"
echo "---------------------------------------------"
systemctl status nginx --no-pager | head -n 5
echo ""

# 3. List all Nginx sites
echo -e "${BLUE}📋 3. Nginx Enabled Sites${NC}"
echo "---------------------------------------------"
echo "Sites available:"
ls /etc/nginx/sites-available/
echo ""
echo "Sites enabled:"
ls /etc/nginx/sites-enabled/
echo ""

# 4. Check which ports Nginx is using
echo -e "${BLUE}🔌 4. Nginx Port Configuration${NC}"
echo "---------------------------------------------"
grep -r "listen" /etc/nginx/sites-enabled/ 2>/dev/null | grep -v "#"
echo ""

# 5. Check PostgreSQL status
echo -e "${BLUE}🗄️  5. PostgreSQL Status${NC}"
echo "---------------------------------------------"
systemctl status postgresql --no-pager | head -n 5
echo ""

# 6. List existing databases
echo -e "${BLUE}📊 6. Existing PostgreSQL Databases${NC}"
echo "---------------------------------------------"
sudo -u postgres psql -c "\l" | grep -v "template"
echo ""

# 7. List PostgreSQL users
echo -e "${BLUE}👥 7. Existing PostgreSQL Users${NC}"
echo "---------------------------------------------"
sudo -u postgres psql -c "\du"
echo ""

# 8. Check what's running on common ports
echo -e "${BLUE}🚪 8. Ports Currently in Use${NC}"
echo "---------------------------------------------"
echo "Port 80 (HTTP):"
netstat -tuln | grep ":80 " || echo "  Not in use"
echo "Port 443 (HTTPS):"
netstat -tuln | grep ":443 " || echo "  Not in use"
echo "Port 8000 (Common Django port):"
netstat -tuln | grep ":8000 " || echo "  Not in use"
echo "Port 8001 (Our target port):"
netstat -tuln | grep ":8001 " || echo "  Not in use"
echo "Port 8080 (Alternative HTTP):"
netstat -tuln | grep ":8080 " || echo "  Not in use"
echo ""

# 9. Check running Python/Django services
echo -e "${BLUE}🐍 9. Running Python/Gunicorn Services${NC}"
echo "---------------------------------------------"
ps aux | grep -E "gunicorn|python.*manage.py" | grep -v grep || echo "  No Python/Gunicorn processes found"
echo ""

# 10. List systemd services for Django apps
echo -e "${BLUE}⚙️  10. Systemd Services (Django apps)${NC}"
echo "---------------------------------------------"
systemctl list-units --type=service | grep -E "gunicorn|django|restaurant|worker" || echo "  No Django-related services found"
echo ""

# 11. Check available disk space
echo -e "${BLUE}💾 11. Disk Space${NC}"
echo "---------------------------------------------"
df -h /var/www/
echo ""

# 12. Check Python version
echo -e "${BLUE}🐍 12. Python Version${NC}"
echo "---------------------------------------------"
python3 --version
echo ""

# 13. Check if git is installed
echo -e "${BLUE}📦 13. Git Installation${NC}"
echo "---------------------------------------------"
git --version
echo ""

# 14. Summary and Recommendations
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}✅ DIAGNOSTIC COMPLETE${NC}"
echo -e "${GREEN}=============================================${NC}"
echo ""
echo -e "${YELLOW}📝 NEXT STEPS:${NC}"
echo "1. Review the output above carefully"
echo "2. Note which ports are in use"
echo "3. Check if 'worker_connect_db' database already exists"
echo "4. Verify port 8001 is available for Worker Connect"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT CHECKS:${NC}"
echo "- If port 80 is used by restaurant, Worker Connect will use port 8080"
echo "- If 'worker_connect_db' exists, choose a different database name"
echo "- Make sure you have enough disk space (need ~500MB minimum)"
echo ""
echo "Safe to proceed with deployment if:"
echo "  ✅ Port 8001 is NOT in use (for Gunicorn)"
echo "  ✅ Database 'worker_connect_db' does NOT exist"
echo "  ✅ /var/www/ has available space"
echo ""
