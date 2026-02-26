# 🚀 HOW TO RUN & TEST THE PROJECT

## ✅ PROJECT IS NOW RUNNING!

**Django Server:** http://127.0.0.1:8000/
**Admin Panel:** http://127.0.0.1:8000/admin/
**API Docs:** http://127.0.0.1:8000/api/docs/

---

## 📋 TEST USERS (11 Total)

### 👨‍💼 ADMIN/SUPERUSER (1)
1. **Email:** alhajj@gmail.com
   **Username:** alhajjmuhammed
   **Name:** Mohd Juma
   **Type:** Admin/Staff
   **Access:** Full admin panel access

---

### 👤 CLIENTS (3)

2. **Email:** test2@example.com
   **Username:** testclient2
   **Name:** Test Client

3. **Email:** client_1769948521@example.com
   **Username:** client_1769948521@example.com
   **Name:** Test Client
   **Phone:** +1234567890

---

### 👷 WORKERS (8)

4. **Email:** alhajjmuhammed@gmail.com
   **Username:** wissam
   **Name:** Moh'd Mgeni
   **Phone:** 0772333036
   **Status:** Available (Verification: Pending)

5. **Email:** test_nmlrcjpx@example.com
   **Username:** test_nmlrcjpx@example.com
   **Name:** Test Worker
   **Phone:** +1234567890

6. **Email:** test_zixa07hm@example.com
   **Username:** test_zixa07hm@example.com
   **Name:** Test User
   **Phone:** +1234567890

7. **Email:** test_jgqr3tnc@example.com
   **Username:** test_jgqr3tnc@example.com
   **Name:** Test User
   **Phone:** +1234567890

8. **Email:** testuser_1769948186@example.com
   **Username:** testuser_1769948186@example.com
   **Name:** Test User
   **Phone:** +1234567890

9. **Email:** testuser_1769948208@example.com
   **Username:** testuser_1769948208@example.com
   **Name:** Test User
   **Phone:** +1234567890

10. **Email:** ultimate_test_1769948354@example.com
    **Username:** ultimate_test_1769948354@example.com
    **Name:** Ultimate Tester
    **Phone:** +1234567890

11. **Email:** worker_1769948524@example.com
    **Username:** worker_1769948524@example.com
    **Name:** Test Worker
    **Phone:** +1234567891

---

## 🔐 PASSWORD NOTES
- Use the passwords you set when creating these accounts
- If you need to reset, use: `python manage.py changepassword <username>`
- For new test users, consider using "test1234" for simplicity

---

## 📱 API ENDPOINTS TO TEST

### Authentication
- POST `/api/v1/accounts/login/` - Login
- POST `/api/v1/accounts/register/` - Register
- POST `/api/v1/accounts/logout/` - Logout
- GET `/api/v1/accounts/user/` - Get current user

### Worker APIs
- GET `/api/v1/workers/profile/` - Worker profile
- PATCH `/api/v1/workers/profile/update/` - Update profile
- GET `/api/v1/workers/stats/` - Worker statistics
- GET `/api/v1/workers/assigned-jobs/` - Assigned jobs

### Client APIs
- GET `/api/v1/clients/profile/` - Client profile
- GET `/api/v1/clients/services/` - Available services
- POST `/api/v1/client/service-requests/create/` - Create service request
- GET `/api/v1/clients/stats/` - Client statistics

### Jobs APIs
- GET `/api/v1/jobs/browse/` - Browse jobs
- POST `/api/v1/jobs/worker/jobs/<id>/apply/` - Apply for job
- GET `/api/v1/jobs/client/jobs/` - Client's jobs

### Service Requests
- POST `/api/v1/client/service-requests/create/` - Client creates request
- GET `/api/v1/worker/service-requests/` - Worker's assignments
- POST `/api/v1/worker/service-requests/<id>/respond/` - Accept/Reject
- POST `/api/v1/worker/service-requests/<id>/clock-in/` - Clock in
- POST `/api/v1/worker/service-requests/<id>/complete/` - Complete work

---

## 🧪 TESTING WORKFLOW

### 1. Test as Admin
```
Login: alhajj@gmail.com
Access admin panel at: http://127.0.0.1:8000/admin/
- Verify workers
- Assign service requests
- Manage categories
```

### 2. Test as Client
```
Login with: test2@example.com
- Browse services
- Create service request
- View assigned workers
- Rate workers
```

### 3. Test as Worker
```
Login with: wissam (alhajjmuhammed@gmail.com)
- Complete profile
- Accept assignments
- Clock in/out
- Complete work
- View earnings
```

---

## 🛠️ USEFUL COMMANDS

```bash
# List all users
python list_users.py

# Create new superuser
python manage.py createsuperuser

# Reset password
python manage.py changepassword <username>

# Run migrations
python manage.py migrate

# Open Django shell
python manage.py shell

# Check system
python manage.py check

# Run tests
python manage.py test

# Stop server: CTRL+C in terminal
```

---

## 📊 SYSTEM STATUS

✅ **Database:** SQLite (db.sqlite3) - Connected
✅ **Models:** All models migrated
✅ **APIs:** Web & Mobile endpoints working
✅ **CRUD:** 100% functional
✅ **Authentication:** Token-based auth working
✅ **Service Requests:** Complete workflow implemented

---

## 🔍 API DOCUMENTATION

**Swagger UI:** http://127.0.0.1:8000/api/docs/
**ReDoc:** http://127.0.0.1:8000/api/redoc/

---

## 📱 MOBILE APP (React Native)

To test the mobile app:
```bash
cd React-native-app/my-app
npm install
npm start
```

Configure API URL in: `React-native-app/my-app/config/api.ts`

---

## 🎉 Happy Testing!

Your Worker Connect platform is fully operational and ready for comprehensive testing!
