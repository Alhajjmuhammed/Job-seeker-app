# 📋 Service Request Workflow - Complete Guide

## Overview
This document explains how service requests flow from creation to completion, and how all parties (Client, Admin, Worker) stay informed.

---

## 🔄 The Complete Flow

### Step 1: Client Creates Service Request
**Status:** `pending` (Yellow badge)

**What Happens:**
- Client fills out the service request form
- Selects category (Cleaning, Plumbing, Electrical, etc.)
- Chooses duration (Daily, Monthly, Custom dates)
- System calculates price based on duration
- Client pays for the service
- Request is created with status: **PENDING**

**Notifications:**
- ✅ All **Admins** get notified: "New Service Request 📋"
- ✅ Admin sees: Category, Urgency, Location, Client name

**Client Sees:**
- Request appears in "My Requests" with status: **Pending**
- Message: "Waiting for admin to assign a worker"

---

### Step 2: Admin Assigns Worker
**Status:** `assigned` (Blue badge)

**What Happens:**
- Admin reviews pending requests
- Admin finds available, verified worker with matching skills
- Admin assigns worker to the request
- Status changes to: **ASSIGNED**

**Notifications:**
- ✅ **Worker** gets notified: "🎯 New Service Assigned!"
- ✅ **Client** gets notified: "✅ Worker Assigned to Your Request"
- Both see worker/client details and location

**What Client Sees:**
- Status changes to: **Assigned**
- Shows worker name and phone number
- Message: "Worker assigned! They will contact you soon"

---

### Step 3: Worker Accepts/Rejects Assignment
**Status:** Stays `assigned` if accepted, back to `pending` if rejected

**What Happens - If Worker ACCEPTS:**
- Worker clicks "Accept Assignment" button
- Worker sees job details and client contact info
- Status remains: **ASSIGNED** (ready to start)

**Notifications if ACCEPTED:**
- ✅ **Client** gets notified: "👍 Worker Accepted Your Request"
- Client sees: "Worker is coming soon!"

**What Happens - If Worker REJECTS:**
- Worker provides rejection reason
- Status goes back to: **PENDING**
- Worker assignment is cleared

**Notifications if REJECTED:**
- ✅ **Admin** gets notified: "⚠️ Worker Rejected Assignment"
- Admin needs to reassign different worker

---

### Step 4: Worker Arrives & Clocks In 🕐
**Status:** `in_progress` (Primary blue badge)

**What "Clock In" Means:**
- Worker arrives at the job site
- Worker clicks "Clock In" button
- System starts tracking work time for billing
- First clock-in changes status to: **IN PROGRESS**

**Why Clock In/Out?**
- Accurate time tracking
- Fair payment calculation
- Proof of work hours for disputes
- Worker can take breaks (clock out, then clock in again)

**Notifications:**
- ✅ **Client** gets notified: "🚀 Work Started on Your Request"
- Client sees: "Worker is now actively working"

**What Client Sees:**
- Status changes to: **In Progress**
- Shows "Work Started" timestamp
- Can see worker is actively working

---

### Step 5: Worker Works & Takes Breaks
**Status:** Stays `in_progress`

**Clock In/Out During Work:**
- Worker can **Clock Out** for lunch break
- Worker can **Clock In** again to resume
- Each clock-in/out creates a time log
- System tracks total hours worked

**Worker Sees in App:**
- Active timer showing elapsed time (00:00:00)
- Current assignment details
- Client contact information

**Client Sees:**
- Status: **In Progress**
- Can contact worker if needed
- Knows work is actively happening

---

### Step 6: Worker Completes Work ✅
**Status:** `completed` (Green badge)

**What "Mark as Completed" Means:**
- Worker finishes all work
- Worker must Clock Out first (no active timers)
- Worker clicks "Mark as Completed" button
- Worker adds completion notes
- System calculates: Total Hours × Hourly Rate = Total Amount

**Notifications:**
- ✅ **Client** gets notified: "✨ Service Completed!"
- Client sees: Total hours worked, completion notes
- Client is asked to rate the worker

**What Client Sees:**
- Status changes to: **Completed**
- Shows "Work Completed" timestamp
- **"Rate Worker" button appears** ⭐
- Shows total hours worked and amount

---

### Step 7: Client Rates Worker ⭐
**Status:** Stays `completed`

**What Happens:**
- Client clicks "Rate Worker" button
- Client gives 1-5 star rating
- Client writes review (optional)
- Rating helps other clients choose workers
- Worker's average rating updates

**Notifications:**
- ✅ **Worker** gets notified: "You received a 5-star review ⭐⭐⭐⭐⭐"
- Worker can see their updated rating

**Payment:**
- Worker gets paid based on hours worked
- Transaction is recorded in system

---

## 📱 How Notifications Work

### Client Receives Notifications When:
1. ✅ Worker is assigned (with worker contact info)
2. ✅ Worker accepts the assignment
3. ✅ Work starts (first clock-in)
4. ✅ Work is completed (ready to rate)

### Worker Receives Notifications When:
1. ✅ Admin assigns them a new service
2. ✅ Service is cancelled by client
3. ✅ Client rates them

### Admin Receives Notifications When:
1. ✅ New service request is created (needs assignment)
2. ✅ Worker rejects an assignment (needs reassignment)

---

## 🔔 How to See Notifications

### In Mobile App:
1. Look for notification bell icon (top right)
2. Badge shows unread count
3. Tap to see all notifications
4. Tap notification to go to that request

### In Web Dashboard:
1. Notification bell in header
2. Dropdown shows recent notifications
3. Click to mark as read

---

## 📊 Status Colors Explained

| Status | Color | Meaning |
|--------|-------|---------|
| **Pending** | Yellow | Waiting for admin to assign worker |
| **Assigned** | Blue | Worker assigned, waiting for acceptance |
| **In Progress** | Primary Blue | Worker actively working on site |
| **Completed** | Green | Work finished, ready for rating |
| **Cancelled** | Gray | Request was cancelled |

---

## ❓ Common Questions

### Q: Why does the worker need to "Clock In"?
**A:** Clock In/Out creates accurate time logs for billing. It ensures the worker gets paid fairly for actual hours worked, and clients can see exactly when work was being done.

### Q: Can worker clock in and out multiple times?
**A:** Yes! Worker can clock out for lunch breaks or if they need to leave temporarily, then clock back in. All time periods are tracked and summed up.

### Q: What if I don't see any notifications?
**A:** 
1. Check your notification settings in your profile
2. Make sure app has notification permissions
3. Pull to refresh the notifications page
4. Check "My Requests" page for status updates

### Q: When should I rate the worker?
**A:** Rate the worker only after they click "Mark as Completed". You'll see the status change to "Completed" and a "Rate Worker" button will appear.

### Q: What if worker doesn't accept my request?
**A:** If the worker rejects, the admin will be notified automatically and will assign a different worker. You'll get a new notification when a new worker is assigned.

---

## 🚀 Quick Reference

**For Clients:**
1. Create request → Wait for assignment notification
2. Get worker assigned → Receive acceptance notification
3. Worker clocks in → Get "work started" notification
4. Worker completes → Get "completed" notification → Rate worker

**For Workers:**
1. Get assignment notification → Review details → Accept/Reject
2. Go to job site → Clock In
3. Take break? → Clock Out → Clock In again
4. Finish work → Clock Out → Mark as Completed

**For Admins:**
1. Get new request notification → Review → Assign best worker
2. If rejected → Get notification → Reassign different worker

---

## 💡 Tips for Best Experience

**Clients:**
- Enable push notifications for real-time updates
- Add worker phone number to contacts after assignment
- Check notifications regularly for status updates
- Rate workers promptly after completion

**Workers:**
- Accept assignments quickly to avoid reassignment
- Clock in as soon as you arrive
- Clock out for all breaks
- Add detailed completion notes
- Mark as completed only when fully done

**Admins:**
- Assign workers with matching skills and location
- Check worker availability before assigning
- Respond to rejection notifications promptly
- Monitor urgent requests first

---

## 📞 Support

If notifications aren't working or you have questions:
- Check notification settings in your profile
- Ensure stable internet connection
- Contact admin via messaging system
- Check this guide for workflow understanding

---

**Last Updated:** March 5, 2026
**Version:** 1.0
