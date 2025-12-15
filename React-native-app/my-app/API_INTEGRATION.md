# API Integration Guide

## 🚀 Quick Setup

### 1. Configure Your API URL

Edit `config/api.ts` and update the `LOCAL_IP` with your computer's IP address:

```typescript
export const API_CONFIG = {
  LOCAL_IP: '192.168.100.111', // <- Change this to your IP
  LOCAL_PORT: '8000',
  // ...
};
```

### How to Find Your Local IP:

**Windows:**
```bash
ipconfig
# Look for "IPv4 Address" under your active network adapter
```

**Mac/Linux:**
```bash
ifconfig
# or
ip addr
# Look for "inet" address (usually starts with 192.168.x.x)
```

**For Emulators:**
- Android Emulator: Use `10.0.2.2`
- iOS Simulator: Use `localhost`

---

## 📦 Installed Packages

- **axios** - HTTP client for API requests
- **@react-native-async-storage/async-storage** - Persistent storage for tokens

---

## 🏗️ Architecture

### Services Layer (`services/`)

#### `api.ts` - Main API Service
Handles all HTTP requests to Django backend:
- Authentication (login, register, logout)
- Worker operations (profile, direct hire requests, jobs)
- Client operations (search workers, post jobs, manage applications)
- Common operations (categories, messages)

#### `auth.ts` - Authentication Service
Wrapper around API service for auth-specific operations:
- Login/Register
- Token management
- User data persistence

### Context (`contexts/`)

#### `AuthContext.tsx` - Global Auth State
React Context providing:
- `user` - Current user object
- `isAuthenticated` - Boolean auth status
- `login()` - Login function
- `register()` - Register function
- `logout()` - Logout function

---

## 🔐 Authentication Flow

### Login Process:
1. User enters email/password
2. `login()` called from AuthContext
3. API request to `/api/accounts/login/`
4. Token stored in AsyncStorage
5. User data stored locally
6. Auto-redirect to dashboard based on user type

### Register Process:
1. User fills registration form
2. Selects user type (Worker/Client)
3. `register()` called from AuthContext
4. API request to `/api/accounts/register/`
5. Token + user data stored
6. Auto-redirect to appropriate dashboard

### Token Management:
- Stored in AsyncStorage with key `@auth_token`
- Automatically added to all API requests via axios interceptor
- Cleared on logout or 401 response

---

## 🔌 Django Backend Setup

### Required Django REST API Endpoints:

#### Authentication:
```
POST /api/accounts/login/
POST /api/accounts/register/
POST /api/accounts/logout/
GET  /api/accounts/profile/
```

#### Worker Endpoints:
```
GET    /api/workers/profile/
PATCH  /api/workers/profile/
PATCH  /api/workers/availability/
GET    /api/jobs/direct-hire-requests/
POST   /api/jobs/direct-hire-requests/{id}/accept/
POST   /api/jobs/direct-hire-requests/{id}/reject/
GET    /api/jobs/worker/jobs/
GET    /api/jobs/worker/applications/
POST   /api/jobs/{id}/apply/
```

#### Client Endpoints:
```
GET    /api/clients/profile/
PATCH  /api/clients/profile/
GET    /api/workers/search/
GET    /api/workers/{id}/
POST   /api/jobs/direct-hire-request/
GET    /api/jobs/client/jobs/
POST   /api/jobs/
GET    /api/jobs/{id}/
GET    /api/jobs/{id}/applications/
POST   /api/jobs/applications/{id}/accept/
POST   /api/jobs/applications/{id}/reject/
```

#### Common Endpoints:
```
GET  /api/categories/
GET  /api/messages/
POST /api/messages/
GET  /api/messages/conversation/{userId}/
```

### Install Django REST Framework:
```bash
pip install djangorestframework
pip install django-cors-headers
```

### Update Django Settings:
```python
INSTALLED_APPS = [
    # ...
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    # ... other middleware
]

# For development only!
CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
}
```

---

## 🧪 Testing the API

### Test with Mock Data (Development):
The screens still work with mock data if API is unavailable.

### Test with Real API:
1. Start Django backend: `python manage.py runserver 0.0.0.0:8000`
2. Update `config/api.ts` with your IP
3. Restart Expo: Press `r` in terminal
4. Try login/register

### Debug API Calls:
Check Metro bundler terminal for API errors and responses.

---

## 🐛 Common Issues

### Issue: "Network Request Failed"
**Solution:** 
- Check if Django server is running
- Verify IP address in `config/api.ts`
- Ensure phone/emulator is on same WiFi network
- Check firewall settings

### Issue: "401 Unauthorized"
**Solution:**
- Token may be expired
- Logout and login again
- Check Django token authentication setup

### Issue: CORS Errors
**Solution:**
- Install `django-cors-headers`
- Add to MIDDLEWARE in settings.py
- Set `CORS_ALLOW_ALL_ORIGINS = True` for development

---

## 📱 Usage in Components

### Using Auth:
```typescript
import { useAuth } from '../contexts/AuthContext';

function MyComponent() {
  const { user, isAuthenticated, login, logout } = useAuth();
  
  // Check if user is logged in
  if (!isAuthenticated) {
    return <LoginPrompt />;
  }
  
  // Access user data
  return <Text>Welcome {user.firstName}!</Text>;
}
```

### Making API Calls:
```typescript
import apiService from '../services/api';

// Get worker profile
const profile = await apiService.getWorkerProfile();

// Search workers
const workers = await apiService.searchWorkers({
  category: 'Plumbing',
  isAvailable: true,
});

// Accept direct hire request
await apiService.acceptDirectHireRequest(requestId);
```

---

## 🎯 Next Steps

1. ✅ API service layer created
2. ✅ Authentication context setup
3. ✅ Login/Register connected
4. ⏳ Create Django REST API endpoints
5. ⏳ Connect dashboard screens to real data
6. ⏳ Add loading states and error handling
7. ⏳ Implement real-time features (messages, notifications)

---

## 📚 Additional Resources

- [Axios Documentation](https://axios-http.com/docs/intro)
- [React Navigation Auth Flow](https://reactnavigation.org/docs/auth-flow)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Expo AsyncStorage](https://docs.expo.dev/versions/latest/sdk/async-storage/)
