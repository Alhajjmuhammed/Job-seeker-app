#!/bin/bash
# Quick Deployment Script - Run on Server
# Usage: bash deploy.sh

set -e  # Exit on error

echo "🚀 Starting Worker Connect Deployment..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/var/www/worker-connect"
VENV_DIR="$PROJECT_DIR/venv"
BRANCH="web-deployment"

# Check if we're in the right directory
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}Error: Project directory $PROJECT_DIR not found${NC}"
    exit 1
fi

cd $PROJECT_DIR

echo -e "${YELLOW}📥 Pulling latest changes from $BRANCH...${NC}"
git fetch origin
git checkout $BRANCH
git pull origin $BRANCH

echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
source $VENV_DIR/bin/activate

echo -e "${YELLOW}📦 Installing/updating dependencies...${NC}"
pip install -r requirements.txt --quiet

echo -e "${YELLOW}🗄️  Running database migrations...${NC}"
python manage.py migrate --noinput

echo -e "${YELLOW}📁 Collecting static files...${NC}"
python manage.py collectstatic --noinput

echo -e "${YELLOW}🔄 Restarting Gunicorn service...${NC}"
systemctl restart worker-connect

echo -e "${YELLOW}🔄 Restarting Daphne (WebSocket) service...${NC}"
# This used to be missing entirely, so the daphne service would silently
# stay dead after any manual stop/crash - every deploy "succeeded" while
# real-time notifications were quietly broken in production. Enable it too
# so it survives reboots, not just this deploy.
systemctl enable --now worker-connect-daphne >/dev/null 2>&1
systemctl restart worker-connect-daphne

echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 3

echo -e "${YELLOW}✅ Checking service status...${NC}"
DEPLOY_OK=true
if systemctl is-active --quiet worker-connect; then
    echo -e "${GREEN}✅ Gunicorn is running.${NC}"
else
    echo -e "${RED}❌ Gunicorn is not running.${NC}"
    journalctl -u worker-connect -n 20 --no-pager
    DEPLOY_OK=false
fi

if systemctl is-active --quiet worker-connect-daphne; then
    echo -e "${GREEN}✅ Daphne (WebSocket) is running.${NC}"
else
    echo -e "${RED}❌ Daphne (WebSocket) is not running.${NC}"
    journalctl -u worker-connect-daphne -n 20 --no-pager
    DEPLOY_OK=false
fi

if [ "$DEPLOY_OK" = false ]; then
    echo -e "${RED}❌ Deployment failed! See logs above.${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${GREEN}Your app is running at: http://72.62.51.225${NC}"
