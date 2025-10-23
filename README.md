# Worker Connect

A professional mobile-first platform connecting clients with workers from various fields (plumbers, electricians, houseworkers, waiters, etc.).

## Features

### Worker Features
- Registration and profile management
- Document uploads (CV, ID, certificates)
- Category and skill selection
- Job application and acceptance
- Availability status management
- Earnings history

### Client Features
- Advanced search and filter dashboard
- Worker profile viewing with attachments
- Job request posting
- In-app messaging system
- Rating and feedback system

### Admin Features
- Worker verification and approval
- Category management
- System monitoring and analytics
- Report generation

## Tech Stack
- **Backend**: Django 4.2
- **Frontend**: Bootstrap 5
- **Database**: SQLite3
- **UI/UX**: Responsive, mobile-first design

## Installation

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   - Copy `.env.example` to `.env`
   - Update the values in `.env`

4. **Run migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a superuser:**
   ```bash
   python manage.py createsuperuser
   ```

6. **Load initial data (optional):**
   ```bash
   python manage.py loaddata initial_categories
   ```

7. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

8. **Access the application:**
   - Main site: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/

## Project Structure

```
JobSeeker/
├── worker_connect/          # Main project settings
├── accounts/                # User authentication and profiles
├── workers/                 # Worker-specific features
├── clients/                 # Client-specific features
├── jobs/                    # Job requests and applications
├── admin_panel/             # Admin dashboard
├── static/                  # Static files (CSS, JS, images)
├── media/                   # User uploads
└── templates/               # Global templates
```

## Default Credentials

After creating a superuser, you can:
- Access admin panel with superuser credentials
- Register as Worker or Client through the registration pages

## License

Proprietary - All rights reserved
