# 🧪 Translation Testing Guide

## Quick Test Checklist

### ✅ Web App Testing (5 minutes)

1. **Start Django Server:**
   ```bash
   cd c:\Users\alhaj\OneDrive\Documents\Projects\Job-seeker-app
   python manage.py runserver 8080
   ```

2. **Test Language Switching:**
   - Open http://127.0.0.1:8080/
   - Click language dropdown in navbar
   - Switch to: Swahili → French → Italian → English
   - Verify all visible text changes language

3. **Check Key Pages:**
   - Landing page (/)
   - Login page (/accounts/login/)
   - Navbar and footer
   - Trust bar descriptions
   - "How It Works" section

### ✅ Mobile App Testing (10 minutes)

1. **Start Expo:**
   ```bash
   cd React-native-app\my-app
   npx expo start
   ```

2. **Test Core Screens:**
   - Open app on device/emulator
   - **Auth Flow:**
     - Login screen → Switch language → Verify translations
     - Register screen → Check form labels
   - **Worker Flow:**
     - Dashboard → Verify stats, navigation
     - Profile → Check all labels
     - Assignments → Test assignment cards
     - Settings → Try language picker
   - **Client Flow:**
     - Dashboard → Verify requests
     - My Requests → Check status labels
     - Settings → Test language switcher

3. **Language Switching Test:**
   - Go to Settings
   - Tap "Language"
   - Select each language:
     - ✅ English (default)
     - ✅ Kiswahili (Swahili)
     - ✅ Français (French)
     - ✅ Italiano (Italian)
   - Navigate to different screens
   - Verify common UI elements translate correctly

### ✅ Translation Coverage Test

**Run Verification Script:**
```bash
cd React-native-app\my-app
python verify_translation_coverage.py
```

**Expected Results:**
- ✅ Fully translated: 27 screens
- ⚠️ Partially translated: 34 screens
- 📈 Translation coverage: **81.5%**
- 📊 Total t() calls: **1,046**

### ✅ What to Look For

**Good Signs:**
- ✅ Navigation labels change language
- ✅ Button text translates ("Save" → "Hifadhi" in Swahili)
- ✅ Common phrases translate ("Loading..." → "Inapakia...")
- ✅ Alert messages show in selected language
- ✅ Form placeholders translate

**Expected Behavior (Not Bugs):**
- ⚠️ Some complex text stays in English (18.5% not yet translated)
- ⚠️ User-generated content stays in original language (jobs, messages)
- ⚠️ Numbers and dates may show in English format (localization not implemented)

**Actual Bugs (Report These):**
- ❌ Translation key shows instead of text (e.g., "auth.login" displayed)
- ❌ App crashes when switching language
- ❌ Translation shows `undefined` or `null`
- ❌ Layout breaks with longer translated text

## 🐛 Troubleshooting

### Issue: Translation keys show instead of text
**Solution:** Missing translation key in JSON file
```bash
# Check if key exists:
cd React-native-app\my-app
python find_hardcoded_strings.py
```

### Issue: App crashes on language switch
**Solution:** Restart Expo bundler
```bash
# Stop Expo (Ctrl+C)
# Clear cache and restart:
npx expo start -c
```

### Issue: Old translations still showing
**Solution:** Clear app cache
- Android: Settings → Apps → Expo Go → Clear Cache
- iOS: Delete and reinstall app

## 📝 Reporting Issues

When reporting translation issues, include:
1. **Screen name:** (e.g., "Worker Profile" or "Client Dashboard")
2. **Language selected:** (EN/SW/FR/IT)
3. **What you see:** Screenshot or exact text
4. **What you expected:** Correct translation
5. **Steps to reproduce:**
   - Go to Settings
   - Change language to Swahili
   - Navigate to Profile
   - See "Edit Profile" not translated

## 🎯 Priority Testing Areas

### High Priority (Core Flows):
1. ✅ Auth: Login, Register
2. ✅ Dashboard: Worker/Client dashboards
3. ✅ Profile: View and edit profile
4. ✅ Settings: Language picker
5. ✅ Assignments: Complete service flow

### Medium Priority:
1. ⚠️ Messages: Conversation screens
2. ⚠️ Jobs: Browse and apply
3. ⚠️ Notifications: Notification list
4. ⚠️ Documents: Upload documents

### Low Priority:
1. ⏳ Analytics: Stats dashboard
2. ⏳ Help: Help center
3. ⏳ Terms: Terms and conditions

---

**Happy Testing! 🚀**

If you find issues, use `find_hardcoded_strings.py` to locate the exact line numbers for fixes.
