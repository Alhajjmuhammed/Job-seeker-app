# 🏗️ WORKER CONNECT - SYSTEM ARCHITECTURE

## 📊 System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     WORKER CONNECT PLATFORM                  │
│                  (Mobile-First Web Application)              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │         USER TYPES (3 Roles)           │
        ├────────────────┬──────────────┬────────┤
        │    WORKERS     │   CLIENTS    │ ADMINS │
        └────────────────┴──────────────┴────────┘
```

---

## 🔄 User Flow Diagram

### Worker Journey
```
Register → Complete Profile → Upload Documents → Wait Verification
    ↓
Verified → Browse Jobs → Apply → Get Hired → Complete Job → Get Rated
```

### Client Journey
```
Register → Search Workers → View Profiles → Save Favorites
    ↓
Post Job → Review Applications → Hire Worker → Rate Worker
```

### Admin Journey
```
Login → Dashboard → Verify Workers → Approve Documents → Manage System
```

---

## 🗃️ Database Schema

```
┌─────────────┐
│    User     │ (Custom Authentication)
├─────────────┤
│ - id        │
│ - username  │
│ - email     │
│ - user_type │◄────┐
│ - phone     │     │
└─────────────┘     │
       │            │
       ├────────────┼───────────────┐
       │            │               │
       ▼            ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────┐
│WorkerProfile │ │ClientProfile │ │  Admin   │
├──────────────┤ ├──────────────┤ └──────────┘
│- bio         │ │- company     │
│- location    │ │- location    │
│- experience  │ │- jobs_posted │
│- rating      │ │- total_spent │
│- availability│ └──────────────┘
│- verification│       │
└──────────────┘       │
       │               │
       ├───────────────┴────────┐
       │                        │
       ▼                        ▼
┌──────────────┐         ┌────────────┐
│WorkerDocument│         │  Favorite  │
├──────────────┤         ├────────────┤
│- type        │         │- worker_id │
│- file        │         │- client_id │
│- verified    │         └────────────┘
└──────────────┘                │
       │                        │
       │                        ▼
       │                 ┌────────────┐
       │                 │   Rating   │
       │                 ├────────────┤
       │                 │- stars     │
       │                 │- review    │
       │                 └────────────┘
       ▼
┌──────────────┐
│ Experience   │
├──────────────┤
│- job_title   │
│- company     │
│- duration    │
└──────────────┘
       │
       ▼
┌──────────────┐
│  Category    │◄──────┐
├──────────────┤       │
│- name        │       │
│- icon        │       │
└──────────────┘       │
       │               │
       ▼               │
┌──────────────┐       │
│    Skill     │       │
└──────────────┘       │
                       │
                       │
                ┌──────────────┐
                │  JobRequest  │
                ├──────────────┤
                │- title       │
                │- description │
                │- budget      │
                │- status      │
                │- category_id │
                └──────────────┘
                       │
                       ▼
                ┌──────────────┐
                │JobApplication│
                ├──────────────┤
                │- job_id      │
                │- worker_id   │
                │- status      │
                └──────────────┘
                       │
                       ▼
                ┌──────────────┐
                │   Message    │
                ├──────────────┤
                │- sender_id   │
                │- recipient_id│
                │- content     │
                │- read_status │
                └──────────────┘
```

---

## 🏛️ Application Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  (Templates + Bootstrap 5 + CSS + JavaScript)               │
├─────────────────────────────────────────────────────────────┤
│  • base.html (Layout)      • Forms (Crispy Forms)          │
│  • Home Page              • Dashboards                      │
│  • Profile Pages          • Search & Filter                 │
│  • Job Pages              • Messaging UI                    │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                     BUSINESS LOGIC LAYER                     │
│                    (Django Views + Forms)                    │
├─────────────────────────────────────────────────────────────┤
│  accounts/         workers/        clients/                  │
│  • Registration    • Profiles      • Search                 │
│  • Login/Logout    • Documents     • Ratings                │
│  • Profile Mgmt    • Experience    • Favorites              │
│                                                              │
│  jobs/             admin_panel/                              │
│  • Job CRUD        • Verification                           │
│  • Applications    • Reports                                │
│  • Messaging       • Analytics                              │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                      DATA ACCESS LAYER                       │
│                    (Django ORM + Models)                     │
├─────────────────────────────────────────────────────────────┤
│  • User Model              • Job Models                     │
│  • Worker Models           • Message Models                 │
│  • Client Models           • Category Models                │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                       DATABASE LAYER                         │
│                 (SQLite3 - Development)                      │
│              (PostgreSQL - Production Ready)                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔐 Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     SECURITY LAYERS                          │
├─────────────────────────────────────────────────────────────┤
│  1. Authentication                                           │
│     • Login Required Decorators                             │
│     • Session Management                                    │
│     • Password Hashing (PBKDF2)                            │
│                                                              │
│  2. Authorization                                            │
│     • Role-Based Access Control                            │
│     • Permission Checks                                     │
│     • User Type Verification                               │
│                                                              │
│  3. Data Protection                                          │
│     • CSRF Protection                                       │
│     • SQL Injection Prevention (ORM)                       │
│     • XSS Protection                                        │
│     • Secure File Uploads                                   │
│                                                              │
│  4. Transport Security                                       │
│     • HTTPS (Production)                                    │
│     • Secure Cookies                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 📱 Responsive Design Breakpoints

```
┌─────────────────────────────────────────────────────────────┐
│  Mobile First Approach                                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  📱 Mobile (< 768px)                                        │
│  ├─ Single column layout                                    │
│  ├─ Hamburger menu                                          │
│  ├─ Stacked cards                                           │
│  └─ Touch-friendly buttons                                  │
│                                                              │
│  📱 Tablet (768px - 1024px)                                 │
│  ├─ Two column layout                                       │
│  ├─ Expandable menu                                         │
│  └─ Grid layouts                                            │
│                                                              │
│  💻 Desktop (> 1024px)                                      │
│  ├─ Multi-column layouts                                    │
│  ├─ Full navigation                                         │
│  ├─ Sidebar layouts                                         │
│  └─ Hover effects                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Request/Response Flow

```
User Browser
    │
    │ HTTP Request
    ▼
Django URLs (urls.py)
    │
    │ Route to View
    ▼
Django View (views.py)
    │
    ├──► Check Authentication
    ├──► Check Permissions
    ├──► Process Form Data
    │
    ▼
Django ORM (models.py)
    │
    │ Query Database
    ▼
SQLite/PostgreSQL
    │
    │ Return Data
    ▼
Django View
    │
    │ Render Context
    ▼
Django Template (HTML)
    │
    │ Apply Bootstrap CSS
    ▼
User Browser
```

---

## 📊 Feature Map

```
┌─────────────────────────────────────────────────────────────┐
│                    WORKER CONNECT FEATURES                   │
└─────────────────────────────────────────────────────────────┘

CORE FEATURES
├── Authentication
│   ├── User Registration (Worker/Client)
│   ├── Login/Logout
│   ├── Password Management
│   └── Role-Based Access
│
├── Worker Features
│   ├── Profile Management
│   ├── Document Upload
│   ├── Experience Tracking
│   ├── Skills & Categories
│   ├── Availability Status
│   ├── Job Applications
│   └── Earnings Tracking
│
├── Client Features
│   ├── Worker Search & Filter
│   ├── Worker Profiles View
│   ├── Job Posting
│   ├── Application Review
│   ├── Rating & Reviews
│   ├── Favorites List
│   └── Direct Messaging
│
├── Job Management
│   ├── Job Creation
│   ├── Job Applications
│   ├── Status Tracking
│   ├── Worker Assignment
│   └── Completion Workflow
│
├── Admin Features
│   ├── Worker Verification
│   ├── Document Approval
│   ├── Category Management
│   ├── User Management
│   ├── Reports & Analytics
│   └── System Monitoring
│
└── Communication
    ├── In-App Messaging
    ├── Notifications (Ready)
    └── Email Integration (Ready)
```

---

## 🎨 UI Component Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│  base.html (Root Template)                                   │
│  ├── Navigation Bar                                          │
│  │   ├── Logo                                               │
│  │   ├── Menu Items (Dynamic by Role)                      │
│  │   └── User Dropdown                                      │
│  │                                                           │
│  ├── Main Content Area                                       │
│  │   └── {% block content %} (Child Templates)             │
│  │                                                           │
│  └── Footer                                                  │
│      ├── Links                                               │
│      └── Contact Info                                        │
└─────────────────────────────────────────────────────────────┘

REUSABLE COMPONENTS
├── Cards (hover-card)
├── Forms (crispy-forms)
├── Buttons (btn-*)
├── Badges (status-badge)
├── Alerts (alert-*)
├── Stats Cards (stats-card)
├── Empty States (empty-state)
└── Profile Pictures (profile-picture)
```

---

## 🚀 Deployment Architecture (Production)

```
┌─────────────────────────────────────────────────────────────┐
│                       PRODUCTION SETUP                       │
└─────────────────────────────────────────────────────────────┘

Internet
    │
    ▼
┌─────────────┐
│   CDN       │ (Static Files)
└─────────────┘
    │
    ▼
┌─────────────┐
│  Firewall   │
└─────────────┘
    │
    ▼
┌─────────────┐
│   Nginx     │ (Reverse Proxy + SSL)
└─────────────┘
    │
    ▼
┌─────────────┐
│  Gunicorn   │ (WSGI Server)
└─────────────┘
    │
    ▼
┌─────────────┐
│   Django    │ (Application)
└─────────────┘
    │
    ├────────────┐
    │            │
    ▼            ▼
┌──────────┐  ┌─────────┐
│PostgreSQL│  │  Redis  │ (Cache)
└──────────┘  └─────────┘
    │
    ▼
┌─────────────┐
│     S3      │ (Media Files)
└─────────────┘
```

---

## 📈 Scalability Plan

```
PHASE 1: MVP (Current)
• Single server
• SQLite database
• Local media storage
• Basic features

PHASE 2: Growth
• PostgreSQL database
• Redis caching
• Cloud storage (S3)
• CDN for static files
• Multiple workers

PHASE 3: Scale
• Load balancer
• Database replicas
• Message queue (Celery)
• Microservices (optional)
• Auto-scaling
```

---

## 🔄 Data Flow Examples

### Worker Registration Flow
```
User → Fill Form → Submit
    ↓
Django View → Validate Data
    ↓
Create User (accounts.User)
    ↓
Create WorkerProfile
    ↓
Send Welcome Email (optional)
    ↓
Redirect to Profile Setup
```

### Job Application Flow
```
Worker → Browse Jobs → Select Job
    ↓
Fill Application Form
    ↓
Submit Application
    ↓
Create JobApplication Record
    ↓
Notify Client (optional)
    ↓
Client Reviews Application
    ↓
Accept/Reject
    ↓
Update Job Status
    ↓
Notify Worker
```

### Document Verification Flow
```
Worker → Upload Document
    ↓
Save to Media Storage
    ↓
Create WorkerDocument Record (status: pending)
    ↓
Admin Receives Notification
    ↓
Admin Reviews Document
    ↓
Approve/Reject
    ↓
Update Document Status
    ↓
Notify Worker
    ↓
Update Worker Verification Status (if all docs approved)
```

---

## 💾 File Storage Structure

```
JobSeeker/
├── media/                          # User uploads
│   ├── profile_pictures/          # Profile images
│   │   ├── user_123.jpg
│   │   └── user_456.jpg
│   │
│   └── worker_documents/          # Documents
│       ├── cv_user_123.pdf
│       ├── id_user_123.jpg
│       └── cert_user_123.pdf
│
├── static/                         # Static files
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── custom.js (future)
│   └── images/
│       └── logo.png (future)
│
└── staticfiles/                    # Collected static (production)
```

---

## 🔧 Technology Dependencies

```
Python 3.8+
    │
    ├── Django 4.2.7
    │   ├── django.contrib.auth
    │   ├── django.contrib.admin
    │   ├── django.contrib.messages
    │   └── django.db (ORM)
    │
    ├── Pillow (Image Processing)
    ├── python-decouple (Config)
    ├── django-crispy-forms
    ├── crispy-bootstrap5
    └── django-widget-tweaks

Frontend (CDN)
    │
    ├── Bootstrap 5.3.2
    ├── Bootstrap Icons 1.11.1
    └── JavaScript (Bootstrap Bundle)
```

---

This architecture provides a **solid, scalable foundation** for your Worker Connect platform!

**Key Strengths:**
- ✅ Clean separation of concerns
- ✅ Scalable architecture
- ✅ Security-first design
- ✅ Mobile-responsive
- ✅ Easy to maintain
- ✅ Ready for growth

---

**Use this diagram to understand the system structure! 🏗️**
