#!/usr/bin/env python3
"""
Comprehensive Gap Analysis - Web vs Mobile Platforms
Date: March 9, 2026
Methodology: Deep file inspection with actual code verification
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

class ComprehensiveGapScanner:
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.web_path = self.base_path
        self.mobile_path = self.base_path / "React-native-app" / "my-app"
        
        # Feature mapping with specific search patterns
        self.features = {
            # Authentication & Account
            "Login": {
                "web": ["accounts/views.py", "templates/accounts/login.html"],
                "mobile": ["app/(auth)/login.tsx"],
                "search_patterns": {"web": ["def login"], "mobile": ["handleLogin", "login("]}
            },
            "Register": {
                "web": ["accounts/views.py", "templates/accounts/register.html"],
                "mobile": ["app/(auth)/register.tsx"],
                "search_patterns": {"web": ["def register"], "mobile": ["handleRegister", "register("]}
            },
            "Password Reset": {
                "web": ["accounts/api_views.py"],
                "mobile": ["app/(auth)/forgot-password.tsx", "app/(auth)/reset-password.tsx"],
                "search_patterns": {"web": ["password_reset_request", "password_reset_confirm"], "mobile": ["requestPasswordReset", "confirmPasswordReset"]}
            },
            "Change Password": {
                "web": ["accounts/api_views.py"],
                "mobile": ["app/(worker)/change-password.tsx", "app/(client)/change-password.tsx"],
                "search_patterns": {"web": ["def change_password"], "mobile": ["changePassword"]}
            },
            "Logout": {
                "web": ["accounts/views.py"],
                "mobile": ["contexts/AuthContext.tsx"],
                "search_patterns": {"web": ["def logout"], "mobile": ["logout"]}
            },
            
            # Worker Features
            "Worker Profile": {
                "web": ["workers/views.py", "templates/workers/profile.html"],
                "mobile": ["app/(worker)/profile.tsx"],
                "search_patterns": {"web": ["worker_profile"], "mobile": ["WorkerProfile", "getWorkerProfile"]}
            },
            "Worker Dashboard": {
                "web": ["workers/views.py", "templates/workers/dashboard.html"],
                "mobile": ["app/(worker)/dashboard.tsx"],
                "search_patterns": {"web": ["worker_dashboard"], "mobile": ["WorkerDashboard"]}
            },
            "Browse Jobs": {
                "web": ["workers/views.py", "templates/workers/browse_jobs.html"],
                "mobile": ["app/(worker)/browse-jobs.tsx"],
                "search_patterns": {"web": ["browse_jobs"], "mobile": ["BrowseJobs"]}
            },
            "Job Applications": {
                "web": ["workers/views.py"],
                "mobile": ["app/(worker)/applications.tsx"],
                "search_patterns": {"web": ["applications"], "mobile": ["applications"]}
            },
            "Worker Assignments": {
                "web": ["workers/views.py"],
                "mobile": ["app/(worker)/service-assignments.tsx"],
                "search_patterns": {"web": ["assignments", "service_request"], "mobile": ["ServiceAssignment"]}
            },
            "Worker Earnings": {
                "web": ["workers/views.py", "templates/workers/earnings.html"],
                "mobile": ["app/(worker)/earnings.tsx"],
                "search_patterns": {"web": ["earnings"], "mobile": ["earnings", "EarningsScreen"]}
            },
            "Worker Analytics": {
                "web": ["workers/views.py", "templates/workers/analytics.html"],
                "mobile": ["app/(worker)/analytics.tsx"],
                "search_patterns": {"web": ["analytics"], "mobile": ["analytics", "AnalyticsScreen"]}
            },
            "Payout Methods": {
                "web": ["workers/views.py"],
                "mobile": ["app/(worker)/payout-methods.tsx"],
                "search_patterns": {"web": ["payout"], "mobile": ["PayoutMethods"]}
            },
            
            # Client Features
            "Client Profile": {
                "web": ["clients/views.py", "templates/clients/profile.html"],
                "mobile": ["app/(client)/profile.tsx"],
                "search_patterns": {"web": ["client_profile"], "mobile": ["ClientProfile"]}
            },
            "Client Dashboard": {
                "web": ["clients/views.py", "templates/clients/dashboard.html"],
                "mobile": ["app/(client)/dashboard.tsx"],
                "search_patterns": {"web": ["client_dashboard"], "mobile": ["ClientDashboard"]}
            },
            "Post Job/Service Request": {
                "web": ["clients/views.py", "templates/clients/post_job.html"],
                "mobile": ["app/(client)/request-service.tsx"],
                "search_patterns": {"web": ["post_job", "create_service_request"], "mobile": ["RequestService", "submitServiceRequest"]}
            },
            "Manage Service Requests": {
                "web": ["clients/views.py"],
                "mobile": ["app/(client)/my-requests.tsx"],
                "search_patterns": {"web": ["service_requests"], "mobile": ["MyRequests", "service-request"]}
            },
            "Search Workers": {
                "web": ["clients/views.py", "templates/clients/search_workers.html"],
                "mobile": ["app/(client)/search.tsx"],
                "search_patterns": {"web": ["search_workers"], "mobile": ["SearchScreen", "searchWorkers"]}
            },
            "Hire Worker": {
                "web": ["clients/views.py"],
                "mobile": ["app/(client)/request-service.tsx"],
                "search_patterns": {"web": ["hire_worker", "assign_worker"], "mobile": ["hireWorker", "assignWorker"]}
            },
            "Payment Methods": {
                "web": ["clients/views.py"],
                "mobile": ["app/(client)/payment-methods.tsx"],
                "search_patterns": {"web": ["payment_method"], "mobile": ["PaymentMethods"]}
            },
            "Rate Worker": {
                "web": ["clients/views.py"],
                "mobile": ["app/(client)/rate-worker"],
                "search_patterns": {"web": ["rate_worker", "rating"], "mobile": ["RateWorker", "submitRating"]}
            },
            
            # Communication
            "Messaging": {
                "web": ["workers/views.py", "clients/views.py", "templates/workers/messages.html"],
                "mobile": ["app/(worker)/messages.tsx", "app/(client)/messages.tsx"],
                "search_patterns": {"web": ["messages", "send_message"], "mobile": ["MessagesScreen", "sendMessage"]}
            },
            "Notifications": {
                "web": ["accounts/api_views.py"],
                "mobile": ["app/(worker)/notifications.tsx", "app/(client)/notifications.tsx"],
                "search_patterns": {"web": ["get_notifications"], "mobile": ["NotificationsScreen", "notifications"]}
            },
            "Real-time Chat": {
                "web": ["workers/consumers.py", "clients/consumers.py"],
                "mobile": ["app/(worker)/conversation", "app/(client)/conversation"],
                "search_patterns": {"web": ["ChatConsumer", "websocket"], "mobile": ["Conversation", "websocket"]}
            },
            
            # Payments & Transactions
            "Payment Processing": {
                "web": ["clients/views.py", "workers/views.py"],
                "mobile": ["services/api.ts"],
                "search_patterns": {"web": ["process_payment", "payment"], "mobile": ["processPayment", "payment"]}
            },
            "Invoice Generation": {
                "web": ["workers/views.py"],
                "mobile": ["services/api.ts"],
                "search_patterns": {"web": ["generate_invoice", "invoice"], "mobile": ["invoice"]}
            },
            "Transaction History": {
                "web": ["workers/views.py", "clients/views.py"],
                "mobile": ["app/(worker)/earnings.tsx", "services/api.ts"],
                "search_patterns": {"web": ["transactions"], "mobile": ["transactions", "getTransactions"]}
            },
            
            # Settings & Privacy
            "Settings": {
                "web": ["templates/workers/settings.html", "templates/clients/settings.html"],
                "mobile": ["app/(worker)/settings.tsx", "app/(client)/settings.tsx"],
                "search_patterns": {"web": ["settings"], "mobile": ["SettingsScreen", "settings"]}
            },
            "Privacy Settings": {
                "web": ["accounts/gdpr_views.py", "templates/workers/privacy_settings.html"],
                "mobile": ["app/(worker)/privacy-settings.tsx", "app/(client)/privacy-settings.tsx"],
                "search_patterns": {"web": ["privacy_settings"], "mobile": ["PrivacySettings"]}
            },
            "GDPR Consent": {
                "web": ["accounts/gdpr_views.py"],
                "mobile": ["services/api.ts"],
                "search_patterns": {"web": ["consent"], "mobile": ["getConsentStatus", "updateConsent"]}
            },
            "Data Export": {
                "web": ["accounts/gdpr_views.py"],
                "mobile": ["app/(worker)/settings.tsx", "app/(client)/settings.tsx"],
                "search_patterns": {"web": ["export_data"], "mobile": ["exportData", "handleExportData"]}
            },
            "Account Deletion": {
                "web": ["accounts/gdpr_views.py"],
                "mobile": ["app/(worker)/settings.tsx", "app/(client)/settings.tsx"],
                "search_patterns": {"web": ["delete_account"], "mobile": ["deleteAccount", "handleDeleteAccount"]}
            },
            
            # Advanced Features
            "Dark Mode": {
                "web": ["templates/workers/base_worker.html", "templates/clients/base_client.html"],
                "mobile": ["contexts/ThemeContext.tsx"],
                "search_patterns": {"web": ["theme-toggle", "dark-mode"], "mobile": ["ThemeContext", "isDark"]}
            },
            "Push Notifications": {
                "web": ["N/A - Web uses browser notifications"],
                "mobile": ["services/pushNotifications.ts"],
                "search_patterns": {"web": [], "mobile": ["registerForPushNotifications", "expo-notifications"]}
            },
            "File Upload": {
                "web": ["workers/views.py", "clients/views.py"],
                "mobile": ["services/api.ts"],
                "search_patterns": {"web": ["file_upload", "FileField"], "mobile": ["multipart/form-data", "FormData"]}
            },
            "Document Management": {
                "web": ["workers/views.py"],
                "mobile": ["app/(worker)/documents.tsx"],
                "search_patterns": {"web": ["documents"], "mobile": ["DocumentsScreen", "documents"]}
            },
            "CSV Export": {
                "web": ["workers/views.py"],
                "mobile": ["app/(worker)/analytics.tsx"],
                "search_patterns": {"web": ["export_csv", "csv"], "mobile": ["exportAnalytics"]}
            },
            "Favorites/Saved": {
                "web": ["clients/views.py"],
                "mobile": ["app/(client)/favorites.tsx", "app/(worker)/saved-jobs.tsx"],
                "search_patterns": {"web": ["favorite", "saved"], "mobile": ["Favorites", "SavedJobs"]}
            },
            
            # Help & Support
            "Help/Support": {
                "web": ["templates/workers/help.html", "templates/clients/help.html"],
                "mobile": ["app/(worker)/help.tsx", "app/(worker)/support.tsx"],
                "search_patterns": {"web": ["help", "support"], "mobile": ["HelpScreen", "SupportScreen"]}
            },
            "Terms & Conditions": {
                "web": ["templates/workers/terms.html"],
                "mobile": ["app/(worker)/terms.tsx"],
                "search_patterns": {"web": ["terms"], "mobile": ["TermsScreen"]}
            },
        }
        
        self.results = {
            "full_parity": [],
            "web_only": [],
            "mobile_only": [],
            "partial": []
        }
    
    def file_exists_and_has_content(self, file_path: str, search_patterns: List[str]) -> Tuple[bool, str]:
        """Check if file exists and contains expected patterns"""
        full_path = self.base_path / file_path
        
        if not full_path.exists():
            return False, f"File not found: {file_path}"
        
        try:
            content = full_path.read_text(encoding='utf-8', errors='ignore')
            
            if not search_patterns:
                return True, "File exists (no specific pattern required)"
            
            found_patterns = []
            for pattern in search_patterns:
                if re.search(re.escape(pattern), content, re.IGNORECASE):
                    found_patterns.append(pattern)
            
            if found_patterns:
                return True, f"Found patterns: {', '.join(found_patterns)}"
            else:
                return False, f"File exists but missing patterns: {', '.join(search_patterns)}"
        
        except Exception as e:
            return False, f"Error reading file: {str(e)}"
    
    def check_feature(self, feature_name: str, feature_data: Dict) -> Dict:
        """Check if feature exists on both platforms"""
        result = {
            "feature": feature_name,
            "web": {"exists": False, "details": []},
            "mobile": {"exists": False, "details": []},
            "status": "unknown"
        }
        
        # Check web platform
        web_files = feature_data.get("web", [])
        web_patterns = feature_data.get("search_patterns", {}).get("web", [])
        
        if web_files and web_files[0] != "N/A - Web uses browser notifications":
            web_found = False
            for file in web_files:
                exists, details = self.file_exists_and_has_content(file, web_patterns)
                result["web"]["details"].append(f"{file}: {details}")
                if exists:
                    web_found = True
            result["web"]["exists"] = web_found
        else:
            result["web"]["exists"] = True  # Platform-specific feature
            result["web"]["details"].append("Platform-specific implementation")
        
        # Check mobile platform
        mobile_files = feature_data.get("mobile", [])
        mobile_patterns = feature_data.get("search_patterns", {}).get("mobile", [])
        
        mobile_found = False
        for file in mobile_files:
            mobile_file_path = Path("React-native-app/my-app") / file
            exists, details = self.file_exists_and_has_content(str(mobile_file_path), mobile_patterns)
            result["mobile"]["details"].append(f"{file}: {details}")
            if exists:
                mobile_found = True
        result["mobile"]["exists"] = mobile_found
        
        # Determine status
        if result["web"]["exists"] and result["mobile"]["exists"]:
            result["status"] = "full_parity"
        elif result["web"]["exists"] and not result["mobile"]["exists"]:
            result["status"] = "web_only"
        elif not result["web"]["exists"] and result["mobile"]["exists"]:
            result["status"] = "mobile_only"
        else:
            result["status"] = "missing_both"
        
        return result
    
    def scan_all_features(self):
        """Scan all features and categorize results"""
        print("=" * 80)
        print("COMPREHENSIVE GAP ANALYSIS - WEB VS MOBILE")
        print("Date: March 9, 2026")
        print("=" * 80)
        print()
        
        for feature_name, feature_data in self.features.items():
            result = self.check_feature(feature_name, feature_data)
            
            if result["status"] == "full_parity":
                self.results["full_parity"].append(result)
            elif result["status"] == "web_only":
                self.results["web_only"].append(result)
            elif result["status"] == "mobile_only":
                self.results["mobile_only"].append(result)
            else:
                self.results["partial"].append(result)
    
    def generate_report(self):
        """Generate comprehensive report"""
        total_features = len(self.features)
        
        print("\n" + "=" * 80)
        print("SCAN RESULTS SUMMARY")
        print("=" * 80)
        print()
        
        print(f"Total Features Scanned: {total_features}")
        print(f"✅ Full Parity (Both Platforms): {len(self.results['full_parity'])} features")
        print(f"🌐 Web Only: {len(self.results['web_only'])} features")
        print(f"📱 Mobile Only: {len(self.results['mobile_only'])} features")
        print(f"⚠️  Missing/Partial: {len(self.results['partial'])} features")
        print()
        
        # Calculate parity percentage
        if total_features > 0:
            parity_percentage = (len(self.results['full_parity']) / total_features) * 100
            print(f"Feature Parity Score: {parity_percentage:.1f}%")
        print()
        
        # Full Parity Features
        if self.results['full_parity']:
            print("=" * 80)
            print(f"✅ FEATURES WITH FULL PARITY ({len(self.results['full_parity'])} features)")
            print("=" * 80)
            for result in self.results['full_parity']:
                print(f"\n✅ {result['feature']}")
                print(f"   Web: {result['web']['details'][0][:80]}")
                print(f"   Mobile: {result['mobile']['details'][0][:80]}")
        
        # Gaps: Web Only
        if self.results['web_only']:
            print("\n" + "=" * 80)
            print(f"❌ GAPS: FEATURES ONLY ON WEB ({len(self.results['web_only'])} features)")
            print("=" * 80)
            for result in self.results['web_only']:
                print(f"\n❌ {result['feature']} - MISSING ON MOBILE")
                print(f"   Web Implementation:")
                for detail in result['web']['details']:
                    print(f"      {detail}")
                print(f"   Mobile Status:")
                for detail in result['mobile']['details']:
                    print(f"      {detail}")
        
        # Mobile Only Features
        if self.results['mobile_only']:
            print("\n" + "=" * 80)
            print(f"📱 MOBILE-SPECIFIC FEATURES ({len(self.results['mobile_only'])} features)")
            print("=" * 80)
            for result in self.results['mobile_only']:
                print(f"\n📱 {result['feature']}")
                print(f"   Mobile Implementation:")
                for detail in result['mobile']['details']:
                    print(f"      {detail}")
        
        # Missing/Partial Features
        if self.results['partial']:
            print("\n" + "=" * 80)
            print(f"⚠️  MISSING OR INCOMPLETE ({len(self.results['partial'])} features)")
            print("=" * 80)
            for result in self.results['partial']:
                print(f"\n⚠️  {result['feature']}")
                print(f"   Web: {result['web']['exists']}")
                for detail in result['web']['details']:
                    print(f"      {detail}")
                print(f"   Mobile: {result['mobile']['exists']}")
                for detail in result['mobile']['details']:
                    print(f"      {detail}")
        
        # Final Summary
        print("\n" + "=" * 80)
        print("FINAL ASSESSMENT")
        print("=" * 80)
        
        if len(self.results['web_only']) == 0:
            print("✅ EXCELLENT: No critical gaps found! Mobile has all web features.")
        elif len(self.results['web_only']) <= 2:
            print(f"✅ GOOD: Only {len(self.results['web_only'])} minor gap(s) found.")
        else:
            print(f"⚠️  ATTENTION: {len(self.results['web_only'])} gaps need to be addressed.")
        
        print()
        print("=" * 80)
        print("Scan completed successfully!")
        print("=" * 80)

def main():
    scanner = ComprehensiveGapScanner()
    scanner.scan_all_features()
    scanner.generate_report()

if __name__ == "__main__":
    main()
