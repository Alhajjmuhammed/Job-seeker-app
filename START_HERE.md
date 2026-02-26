# 🚀 QUICK START GUIDE

## 🔐 TEST CREDENTIALS (Password: test1234)

### 1️⃣ ADMIN ACCOUNT
```
Email:    admin@test.com
Password: test1234
Access:   http://127.0.0.1:8000/admin/
```

### 2️⃣ CLIENT ACCOUNT  
```
Email:    client@test.com
Password: test1234
Access:   http://127.0.0.1:8000/accounts/login/
```

### 3️⃣ WORKER ACCOUNT
```
Email:    worker@test.com
Password: test1234
Access:   http://127.0.0.1:8000/accounts/login/
```

---

## 🎯 RUNNING COMMANDS

### ⚡ OPTION 1: START EVERYTHING (Recommended)
```bash
start-all.bat
```
This will start:
- Django Backend (Port 8000)
- React Native Mobile App (Port 8081)

---

### 🔧 OPTION 2: MANUAL START

#### Backend (Django Web)
```bash
# Terminal 1
python manage.py runserver
```
**Access:** http://127.0.0.1:8000/

#### Mobile App (React Native)
```bash
# Terminal 2
cd React-native-app/my-app
npm start
```
**Access:** http://localhost:8081/ (Expo Dev Server)

---

## 📱 SERVICE URLS

| Service | URL | Description |
|---------|-----|-------------|
| **Web Backend** | http://127.0.0.1:8000/ | Main Django application |
| **Admin Panel** | http://127.0.0.1:8000/admin/ | Django admin interface |
| **API Docs (Swagger)** | http://127.0.0.1:8000/api/docs/ | Interactive API documentation |
| **API Docs (ReDoc)** | http://127.0.0.1:8000/api/redoc/ | Alternative API documentation |
| **Mobile (Expo)** | http://localhost:8081/ | React Native Dev Server |

---

## 🧪 TESTING WORKFLOW

### 1. Test Backend (Web)
```bash
# Open browser
http://127.0.0.1:8000/

# Login as client
http://127.0.0.1:8000/accounts/login/
Email: client@test.com
Password: test1234

# Access admin panel
http://127.0.0.1:8000/admin/
Email: admin@test.com
Password: test1234
```

### 2. Test Mobile App
```bash
# Start mobile app
cd React-native-app/my-app
npm start

# Options:
# - Scan QR code with Expo Go app (iOS/Android)
# - Press 'w' to open in web browser
# - Press 'a' for Android emulator
# - Press 'i' for iOS simulator
```

### 3. Test API Endpoints
```bash
# View API documentation
http://127.0.0.1:8000/api/docs/

# Example API calls:
POST http://127.0.0.1:8000/api/v1/accounts/login/
Body: {
  "email": "worker@test.com",
  "password": "test1234"
}
```

---

## 🛠️ USEFUL COMMANDS

```bash
# Create test users (already done)
python create_test_users.py

# List all users
python list_users.py

# Change user password
python manage.py changepassword <username>

# Create new superuser
python manage.py createsuperuser

# Run migrations
python manage.py migrate

# Check system status
python manage.py check

# Run tests
python manage.py test

# Collect static files
python manage.py collectstatic
```

---

## 🎬 CURRENT STATUS

✅ **Backend Server:** Running at http://127.0.0.1:8000/
✅ **Test Users:** Created with password "test1234"
✅ **Database:** SQLite (db.sqlite3)
✅ **Mobile App:** Ready to start

---

## 📊 NEXT STEPS

1. ✅ Start backend → `python manage.py runserver` (ALREADY RUNNING)
2. ⏳ Start mobile → `cd React-native-app/my-app && npm start`
3. 🧪 Test login with credentials above
4. 📱 Test on mobile device with Expo Go app

---

## 🚨 TROUBLESHOOTING

### Backend not starting?
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill process if needed
taskkill /PID <PID> /F
```

### Mobile app issues?
```bash
# Clear cache
cd React-native-app/my-app
npm start -- --clear

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### Database issues?
```bash
# Reset database (WARNING: deletes all data)
del db.sqlite3
python manage.py migrate
python create_test_users.py
```

---

## 🎉 You're All Set!

**Backend:** Already running ✅
**Credentials:** Ready to use ✅
**Mobile:** Ready to start ✅

Happy Testing! 🚀
