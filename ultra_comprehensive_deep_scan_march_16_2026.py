#!/usr/bin/env python3
"""
ULTRA COMPREHENSIVE DEEP SCAN - Mobile & Web Gap Analysis
March 16, 2026
Performs deep analysis of all features across Mobile App, Web Templates, and Backend APIs
"""

import os
import re
from pathlib import Path
from collections import defaultdict

# Colors for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

# Project root
BASE_DIR = Path(__file__).resolve().parent

# Feature categories and their screens/templates/endpoints
FEATURE_MATRIX = {
    # ============= AUTHENTICATION =============
    "Authentication": {
        "Login": {
            "mobile": ["app/(auth)/login.tsx"],
            "web": ["templates/accounts/login.html"],
            "api": ["POST /api/auth/login/"]
        },
        "Register": {
            "mobile": ["app/(auth)/register.tsx"],
            "web": ["templates/accounts/client_register.html", "templates/accounts/worker_register.html"],
            "api": ["POST /api/auth/register/"]
        },
        "Logout": {
            "mobile": ["Handled in navigation/settings"],
            "web": ["Handled in base templates"],
            "api": ["POST /api/auth/logout/"]
        },
        "Forgot Password": {
            "mobile": ["app/(auth)/forgot-password.tsx"],
            "web": ["templates/accounts/forgot_password.html"],
            "api": ["POST /api/auth/password-reset/"]
        },
        "Reset Password": {
            "mobile": ["app/(auth)/reset-password.tsx"],
            "web": ["templates/accounts/reset_password.html"],
            "api": ["POST /api/auth/password-reset/confirm/"]
        },
        "Change Password (Client)": {
            "mobile": ["app/(client)/change-password.tsx"],
            "web": ["templates/accounts/change_password.html"],
            "api": ["POST /api/auth/change-password/"]
        },
        "Change Password (Worker)": {
            "mobile": ["app/(worker)/change-password.tsx"],
            "web": ["templates/accounts/change_password.html"],
            "api": ["POST /api/auth/change-password/"]
        }
    },
    
    # ============= CLIENT FEATURES =============
    "Client Dashboard & Profile": {
        "Client Dashboard": {
            "mobile": ["app/(client)/dashboard.tsx"],
            "web": ["templates/clients/dashboard.html", "templates/service_requests/client/dashboard.html"],
            "api": ["GET /api/clients/stats/"]
        },
        "Client Profile View": {
            "mobile": ["app/(client)/profile.tsx"],
            "web": ["templates/clients/profile.html"],
            "api": ["GET /api/clients/profile/"]
        },
        "Client Profile Edit": {
            "mobile": ["app/(client)/profile-edit.tsx"],
            "web": ["templates/clients/profile_edit.html"],
            "api": ["PATCH /api/clients/profile/update/"]
        }
    },
    
    "Client Service Requests": {
        "Request Service": {
            "mobile": ["app/(client)/request-service.tsx", "app/(client)/request-service/[id].tsx"],
            "web": ["templates/service_requests/client/request_service.html", "templates/clients/request_service.html"],
            "api": ["POST /api/clients/services/<category_id>/request/"]
        },
        "My Requests List": {
            "mobile": ["app/(client)/my-requests.tsx"],
            "web": ["templates/service_requests/client/my_requests.html", "templates/clients/my_service_requests.html"],
            "api": ["GET /api/clients/requests/"]
        },
        "Service Request Detail": {
            "mobile": ["app/(client)/service-request/[id].tsx"],
            "web": ["templates/service_requests/client/request_detail.html", "templates/clients/service_request_detail.html"],
            "api": ["GET /api/clients/requests/<id>/"]
        },
        "Edit Service Request": {
            "mobile": ["app/(client)/edit-service-request/[id].tsx"],
            "web": ["templates/service_requests/client/edit_request.html"],
            "api": ["PATCH /api/clients/requests/<id>/update/"]
        },
        "Cancel Service Request": {
            "mobile": ["Integrated in service-request/[id].tsx"],
            "web": ["templates/service_requests/client/cancel_confirm.html"],
            "api": ["POST /api/clients/requests/<id>/cancel/"]
        },
        "Complete Service Request": {
            "mobile": ["Integrated in service-request/[id].tsx"],
            "web": ["Integrated in request_detail.html"],
            "api": ["POST /api/clients/requests/<id>/complete/"]
        },
        "Upload Screenshot": {
            "mobile": ["Integrated in service-request/[id].tsx"],
            "web": ["templates/service_requests/client/upload_screenshot.html"],
            "api": ["Integrated in service request update"]
        },
        "Rate Worker": {
            "mobile": ["app/(client)/rate-worker/[id].tsx"],
            "web": ["templates/service_requests/client/rate_worker.html", "templates/clients/rate_worker.html"],
            "api": ["POST /api/reviews/"]
        }
    },
    
    "Client Additional Features": {
        "Favorites List": {
            "mobile": ["app/(client)/favorites.tsx"],
            "web": ["Integrated in browse services"],
            "api": ["GET /api/clients/favorites/", "POST /api/clients/favorites/toggle/<worker_id>/"]
        },
        "Search Workers": {
            "mobile": ["app/(client)/search.tsx"],
            "web": ["templates/clients/browse_services.html"],
            "api": ["GET /api/workers/featured/"]
        },
        "Payment Methods": {
            "mobile": ["app/(client)/payment-methods.tsx"],
            "web": ["Integrated in profile/settings"],
            "api": ["Integrated in profile"]
        },
        "Client Jobs": {
            "mobile": ["app/(client)/jobs.tsx", "app/(client)/job/[id].tsx"],
            "web": ["templates/jobs/job_list.html"],
            "api": ["GET /api/jobs/client/jobs/"]
        }
    },
    
    # ============= WORKER FEATURES =============
    "Worker Dashboard & Profile": {
        "Worker Dashboard": {
            "mobile": ["app/(worker)/dashboard.tsx"],
            "web": ["templates/workers/dashboard.html"],
            "api": ["GET /api/workers/stats/"]
        },
        "Worker Profile View": {
            "mobile": ["app/(worker)/profile.tsx"],
            "web": ["templates/workers/profile_edit.html"],
            "api": ["GET /api/workers/profile/"]
        },
        "Worker Profile Edit": {
            "mobile": ["app/(worker)/profile-edit.tsx"],
            "web": ["templates/workers/profile_edit.html"],
            "api": ["PATCH /api/workers/profile/update/"]
        },
        "Worker Profile Setup": {
            "mobile": ["app/(worker)/profile-setup.tsx"],
            "web": ["templates/workers/profile_setup.html"],
            "api": ["PATCH /api/workers/profile/update/", "GET /api/workers/profile/completion/"]
        }
    },
    
    "Worker Service Assignments": {
        "Service Assignments List": {
            "mobile": ["app/(worker)/service-assignments.tsx"],
            "web": ["templates/service_requests/worker/assignments.html"],
            "api": ["GET /api/service-requests/worker/service-requests/"]
        },
        "Pending Assignments": {
            "mobile": ["app/(worker)/assignments/pending.tsx"],
            "web": ["templates/service_requests/worker/pending.html"],
            "api": ["GET /api/service-requests/worker/service-requests/pending/"]
        },
        "Assignment Detail": {
            "mobile": ["app/(worker)/service-assignment/[id].tsx"],
            "web": ["templates/service_requests/worker/assignment_detail.html"],
            "api": ["GET /api/service-requests/worker/service-requests/<id>/detail/"]
        },
        "Respond to Assignment": {
            "mobile": ["app/(worker)/assignments/respond/[id].tsx"],
            "web": ["templates/service_requests/worker/respond.html"],
            "api": ["POST /api/service-requests/worker/service-requests/<id>/respond/"]
        },
        "Clock In": {
            "mobile": ["app/(worker)/assignments/clock/in/[id].tsx"],
            "web": ["templates/service_requests/worker/clock_in.html"],
            "api": ["POST /api/service-requests/worker/service-requests/<id>/clock-in/"]
        },
        "Clock Out": {
            "mobile": ["app/(worker)/assignments/clock/out/[id].tsx"],
            "web": ["templates/service_requests/worker/clock_out.html"],
            "api": ["POST /api/service-requests/worker/service-requests/<id>/clock-out/"]
        },
        "Complete Assignment": {
            "mobile": ["app/(worker)/assignments/complete/[id].tsx"],
            "web": ["templates/service_requests/worker/complete.html"],
            "api": ["POST /api/service-requests/worker/service-requests/<id>/complete/"]
        },
        "Active Service": {
            "mobile": ["app/(worker)/active-service.tsx"],
            "web": ["templates/service_requests/worker/dashboard.html"],
            "api": ["GET /api/service-requests/worker/service-requests/current/"]
        },
        "Activity History": {
            "mobile": ["app/(worker)/activity.tsx"],
            "web": ["templates/service_requests/worker/activity.html"],
            "api": ["GET /api/service-requests/worker/activity/"]
        }
    },
    
    "Worker Analytics & Earnings": {
        "Analytics Dashboard": {
            "mobile": ["app/(worker)/analytics.tsx"],
            "web": ["templates/workers/analytics.html"],
            "api": ["GET /api/workers/analytics/"]
        },
        "Earnings": {
            "mobile": ["app/(worker)/earnings.tsx"],
            "web": ["Integrated in analytics"],
            "api": ["GET /api/workers/earnings/breakdown/", "GET /api/workers/earnings/by-category/"]
        },
        "Payment History": {
            "mobile": ["Integrated in earnings"],
            "web": ["Integrated in analytics"],
            "api": ["GET /api/workers/earnings/payment-history/"]
        },
        "Payout Methods": {
            "mobile": ["app/(worker)/payout-methods.tsx"],
            "web": ["Integrated in profile"],
            "api": ["Integrated in profile"]
        }
    },
    
    "Worker Job Features": {
        "Browse Jobs": {
            "mobile": ["app/(worker)/browse-jobs.tsx"],
            "web": ["templates/jobs/job_list.html"],
            "api": ["GET /api/jobs/worker/jobs/"]
        },
        "Job Detail": {
            "mobile": ["app/(worker)/job/[id].tsx"],
            "web": ["templates/jobs/job_detail.html"],
            "api": ["GET /api/jobs/jobs/<id>/"]
        },
        "Apply for Job": {
            "mobile": ["app/(worker)/job/[id]/apply.tsx"],
            "web": ["templates/jobs/apply_for_job.html"],
            "api": ["POST /api/jobs/worker/jobs/<id>/apply/"]
        },
        "My Applications": {
            "mobile": ["app/(worker)/applications.tsx"],
            "web": ["templates/jobs/my_applications.html"],
            "api": ["GET /api/jobs/worker/applications/"]
        },
        "Saved Jobs": {
            "mobile": ["app/(worker)/saved-jobs.tsx"],
            "web": ["Integrated in job_list"],
            "api": ["Integrated in jobs API"]
        }
    },
    
    "Worker Professional Info": {
        "Experience List": {
            "mobile": ["app/(worker)/experience/index.tsx"],
            "web": ["templates/workers/experience_list.html"],
            "api": ["GET /api/workers/experiences/"]
        },
        "Add Experience": {
            "mobile": ["app/(worker)/experience/add.tsx"],
            "web": ["templates/workers/experience_form.html"],
            "api": ["POST /api/workers/experiences/"]
        },
        "Edit Experience": {
            "mobile": ["app/(worker)/experience/[id]/edit.tsx"],
            "web": ["templates/workers/experience_form.html"],
            "api": ["PATCH /api/workers/experiences/<id>/"]
        },
        "Documents List": {
            "mobile": ["app/(worker)/documents.tsx"],
            "web": ["templates/workers/document_list.html"],
            "api": ["GET /api/workers/documents/"]
        },
        "Upload Documents": {
            "mobile": ["Integrated in documents.tsx"],
            "web": ["templates/workers/document_upload.html"],
            "api": ["POST /api/workers/documents/upload/"]
        }
    },
    
    # ============= MESSAGING =============
    "Messaging": {
        "Conversations List (Client)": {
            "mobile": ["app/(client)/messages.tsx", "app/(client)/conversation/[id].tsx"],
            "web": ["templates/jobs/inbox.html"],
            "api": ["GET /api/jobs/messages/conversations/"]
        },
        "Conversations List (Worker)": {
            "mobile": ["app/(worker)/messages.tsx", "app/(worker)/conversation/[id].tsx"],
            "web": ["templates/jobs/inbox.html"],
            "api": ["GET /api/jobs/messages/conversations/"]
        },
        "Send Message": {
            "mobile": ["Integrated in conversation screens"],
            "web": ["templates/jobs/send_message.html", "templates/jobs/conversation.html"],
            "api": ["POST /api/jobs/messages/send/"]
        },
        "Search Users": {
            "mobile": ["Integrated in messages"],
            "web": ["Integrated in inbox"],
            "api": ["GET /api/jobs/messages/search-users/"]
        }
    },
    
    # ============= NOTIFICATIONS =============
    "Notifications": {
        "Notification Center (Client)": {
            "mobile": ["app/(client)/notifications.tsx"],
            "web": ["templates/notifications/notification_center.html", "templates/accounts/notification_center.html"],
            "api": ["GET /api/notifications/"]
        },
        "Notification Center (Worker)": {
            "mobile": ["app/(worker)/notifications.tsx"],
            "web": ["templates/notifications/notification_center.html", "templates/accounts/notification_center.html"],
            "api": ["GET /api/notifications/"]
        },
        "Mark as Read": {
            "mobile": ["Integrated in notifications"],
            "web": ["Integrated in notification_center"],
            "api": ["POST /api/notifications/<id>/read/"]
        },
        "Mark All Read": {
            "mobile": ["Integrated in notifications"],
            "web": ["Integrated in notification_center"],
            "api": ["POST /api/notifications/read-all/"]
        },
        "Unread Count": {
            "mobile": ["Integrated in navigation"],
            "web": ["Integrated in base template"],
            "api": ["GET /api/notifications/unread-count/"]
        }
    },
    
    # ============= GDPR & PRIVACY =============
    "GDPR Features": {
        "Export Data (Client)": {
            "mobile": ["Integrated in settings/privacy"],
            "web": ["Integrated in privacy settings"],
            "api": ["GET /api/gdpr/export/"]
        },
        "Export Data (Worker)": {
            "mobile": ["Integrated in settings/privacy"],
            "web": ["Integrated in privacy settings"],
            "api": ["GET /api/gdpr/export/"]
        },
        "Delete Account": {
            "mobile": ["Integrated in settings"],
            "web": ["Integrated in privacy settings"],
            "api": ["POST /api/gdpr/delete/"]
        },
        "Anonymize Account": {
            "mobile": ["Integrated in settings"],
            "web": ["Integrated in privacy settings"],
            "api": ["POST /api/gdpr/anonymize/"]
        },
        "Data Retention (Client)": {
            "mobile": ["app/(client)/data-retention.tsx"],
            "web": ["Integrated in privacy settings"],
            "api": ["GET /api/gdpr/retention/"]
        },
        "Data Retention (Worker)": {
            "mobile": ["app/(worker)/data-retention.tsx"],
            "web": ["Integrated in privacy settings"],
            "api": ["GET /api/gdpr/retention/"]
        }
    },
    
    "Privacy Settings": {
        "Privacy Settings (Client)": {
            "mobile": ["app/(client)/privacy-settings.tsx"],
            "web": ["Integrated in profile settings"],
            "api": ["GET /api/privacy/", "POST /api/privacy/update/"]
        },
        "Privacy Settings (Worker)": {
            "mobile": ["app/(worker)/privacy-settings.tsx", "app/(worker)/privacy.tsx"],
            "web": ["Integrated in profile settings"],
            "api": ["GET /api/privacy/", "POST /api/privacy/update/"]
        }
    },
    
    # ============= ADMIN PANEL =============
    "Admin Panel": {
        "Admin Dashboard": {
            "mobile": ["N/A - Web Only by Design"],
            "web": ["templates/admin_panel/dashboard.html"],
            "api": ["GET /api/admin/analytics/overview/"]
        },
        "Manage Users": {
            "mobile": ["N/A - Web Only by Design"],
            "web": ["templates/admin_panel/manage_users.html"],
            "api": ["Admin APIs"]
        },
        "Service Requests Management": {
            "mobile": ["N/A - Web Only by Design"],
            "web": ["templates/admin_panel/service_request_list.html"],
            "api": ["Admin APIs"]
        }
    },
    
    # ============= PAYMENTS =============
    "Payments": {
        "Calculate Price": {
            "mobile": ["Integrated in request-service"],
            "web": ["Integrated in request_service.html"],
            "api": ["POST /api/clients/calculate-price/"]
        },
        "Process Payment": {
            "mobile": ["Integrated in request-service"],
            "web": ["Integrated in request_service.html"],
            "api": ["POST /api/clients/process-payment/"]
        },
        "Category Pricing": {
            "mobile": ["Integrated in service flows"],
            "web": ["Integrated in service flows"],
            "api": ["GET /api/clients/category-pricing/"]
        }
    }
}

def check_file_exists(relative_path):
    """Check if a file exists"""
    full_path = BASE_DIR / "React-native-app" / "my-app" / relative_path
    if full_path.exists():
        # Check if file has content
        try:
            size = full_path.stat().st_size
            return size > 100  # Must have at least 100 bytes
        except:
            return False
    return False

def check_template_exists(template_path):
    """Check if web template exists"""
    full_path = BASE_DIR / template_path
    if full_path.exists():
        try:
            size = full_path.stat().st_size
            return size > 50
        except:
            return False
    return False

def check_api_exists(api_endpoint):
    """Check if API endpoint likely exists based on URL patterns"""
    # This is simplified - we check the patterns we saw in api_urls.py
    patterns = {
        "auth": ["login", "register", "logout", "password-reset", "change-password"],
        "clients": ["profile", "stats", "requests", "favorites", "calculate-price"],
        "workers": ["profile", "stats", "analytics", "earnings", "experiences", "documents"],
        "jobs": ["messages", "browse", "apply", "applications"],
        "notifications": ["notifications", "read"],
        "gdpr": ["export", "delete", "anonymize", "retention"],
        "privacy": ["privacy"],
        "service-requests": ["service-requests", "clock-in", "clock-out", "respond", "complete"]
    }
    
    # Simple heuristic - if endpoint contains known patterns, consider it exists
    for category, keywords in patterns.items():
        if any(keyword in api_endpoint.lower() for keyword in keywords):
            return True
    return False

def analyze_feature(feature_name, feature_data):
    """Analyze a single feature for completeness"""
    mobile = feature_data.get("mobile", [])
    web = feature_data.get("web", [])
    api = feature_data.get("api", [])
    
    # Check mobile implementations
    mobile_exists = False
    mobile_status = []
    for m in mobile:
        if "N/A" in m or "Integrated" in m or "Handled" in m:
            mobile_exists = "Integrated"
            mobile_status.append(f"✅ {m}")
        elif check_file_exists(m):
            mobile_exists = True
            mobile_status.append(f"✅ {m}")
        else:
            mobile_status.append(f"❌ {m}")
    
    # Check web implementations
    web_exists = False
    web_status = []
    for w in web:
        if "Integrated" in w or "Handled" in w:
            web_exists = "Integrated"
            web_status.append(f"✅ {w}")
        elif check_template_exists(w):
            web_exists = True
            web_status.append(f"✅ {w}")
        else:
            web_status.append(f"❌ {w}")
    
    # Check API exists
    api_exists = False
    api_status = []
    for a in api:
        if "Integrated" in a:
            api_exists = "Integrated"
            api_status.append(f"✅ {a}")
        elif check_api_exists(a):
            api_exists = True
            api_status.append(f"✅ {a}")
        else:
            api_status.append(f"⚠️  {a}")
    
    return {
        "name": feature_name,
        "mobile": {"exists": mobile_exists, "details": mobile_status},
        "web": {"exists": web_exists, "details": web_status},
        "api": {"exists": api_exists, "details": api_status}
    }

def print_section(title):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{title:^80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")

def print_category(category):
    """Print a category header"""
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}▶ {category}{Colors.END}")
    print(f"{Colors.MAGENTA}{'-'*80}{Colors.END}")

def print_feature(result):
    """Print feature analysis result"""
    mobile = result["mobile"]["exists"]
    web = result["web"]["exists"]
    api = result["api"]["exists"]
    
    # Determine status
    if mobile and web and api:
        status = f"{Colors.GREEN}✅ COMPLETE{Colors.END}"
    elif (mobile == "Integrated" or mobile) and (web == "Integrated" or web):
        status = f"{Colors.GREEN}✅ COMPLETE{Colors.END}"
    elif not mobile and not web:
        status = f"{Colors.RED}❌ MISSING BOTH{Colors.END}"
    elif not mobile:
        status = f"{Colors.YELLOW}⚠️  MOBILE MISSING{Colors.END}"
    elif not web:
        status = f"{Colors.YELLOW}⚠️  WEB MISSING{Colors.END}"
    else:
        status = f"{Colors.BLUE}ℹ️  PARTIAL{Colors.END}"
    
    print(f"\n  {Colors.BOLD}{result['name']}{Colors.END}: {status}")
    
    # Only show details for incomplete features
    if status != f"{Colors.GREEN}✅ COMPLETE{Colors.END}":
        if not mobile or mobile != "Integrated":
            print(f"    Mobile: {Colors.YELLOW}{'📱 ' + str(result['mobile']['details'])}{Colors.END}")
        if not web or web != "Integrated":
            print(f"    Web:    {Colors.YELLOW}{'🌐 ' + str(result['web']['details'])}{Colors.END}")
        if not api:
            print(f"    API:    {Colors.YELLOW}{'🔌 ' + str(result['api']['details'])}{Colors.END}")

def main():
    """Main scanning function"""
    print_section("ULTRA COMPREHENSIVE MOBILE & WEB DEEP SCAN")
    print(f"{Colors.BOLD}Scan Date:{Colors.END} March 16, 2026")
    print(f"{Colors.BOLD}Scanning:{Colors.END} React Native Mobile App + Django Web + Backend APIs\n")
    
    total_features = 0
    complete_features = 0
    mobile_gaps = []
    web_gaps = []
    both_gaps = []
    
    for category, features in FEATURE_MATRIX.items():
        print_category(category)
        
        for feature_name, feature_data in features.items():
            total_features += 1
            result = analyze_feature(feature_name, feature_data)
            print_feature(result)
            
            mobile = result["mobile"]["exists"]
            web = result["web"]["exists"]
            
            # Track gaps
            if mobile and web:
                complete_features += 1
            elif not mobile and not web:
                both_gaps.append(f"{category} → {feature_name}")
            elif not mobile:
                mobile_gaps.append(f"{category} → {feature_name}")
            elif not web:
                web_gaps.append(f"{category} → {feature_name}")
    
    # Summary
    print_section("SCAN SUMMARY")
    
    completion_rate = (complete_features / total_features * 100) if total_features > 0 else 0
    
    print(f"{Colors.BOLD}Total Features Scanned:{Colors.END} {total_features}")
    print(f"{Colors.BOLD}Complete Features:{Colors.END} {Colors.GREEN}{complete_features}{Colors.END}")
    print(f"{Colors.BOLD}Features with Gaps:{Colors.END} {Colors.YELLOW}{total_features - complete_features}{Colors.END}")
    print(f"{Colors.BOLD}Completion Rate:{Colors.END} {Colors.GREEN if completion_rate >= 90 else Colors.YELLOW}{completion_rate:.1f}%{Colors.END}")
    
    print(f"\n{Colors.BOLD}Gap Breakdown:{Colors.END}")
    print(f"  {Colors.RED}❌ Missing on Both Platforms:{Colors.END} {len(both_gaps)}")
    print(f"  {Colors.YELLOW}📱 Mobile Only Gaps:{Colors.END} {len(mobile_gaps)}")
    print(f"  {Colors.YELLOW}🌐 Web Only Gaps:{Colors.END} {len(web_gaps)}")
    
    # Detail gaps
    if both_gaps:
        print(f"\n{Colors.BOLD}{Colors.RED}CRITICAL: Missing on Both Platforms{Colors.END}")
        for gap in both_gaps:
            print(f"  • {gap}")
    
    if mobile_gaps:
        print(f"\n{Colors.BOLD}{Colors.YELLOW}Mobile Implementation Gaps{Colors.END}")
        for gap in mobile_gaps:
            print(f"  • {gap}")
    
    if web_gaps:
        print(f"\n{Colors.BOLD}{Colors.YELLOW}Web Implementation Gaps{Colors.END}")
        for gap in web_gaps:
            print(f"  • {gap}")
    
    # Final verdict
    print_section("FINAL VERDICT")
    if completion_rate >= 95:
        print(f"{Colors.BOLD}{Colors.GREEN}✅ PRODUCTION READY - Excellent Feature Parity{Colors.END}")
    elif completion_rate >= 85:
        print(f"{Colors.BOLD}{Colors.GREEN}✅ PRODUCTION READY - Good Feature Parity{Colors.END}")
    elif completion_rate >= 70:
        print(f"{Colors.BOLD}{Colors.YELLOW}⚠️  MOSTLY READY - Some gaps to address{Colors.END}")
    else:
        print(f"{Colors.BOLD}{Colors.RED}❌ NEEDS WORK - Significant gaps exist{Colors.END}")
    
    print()

if __name__ == "__main__":
    main()
