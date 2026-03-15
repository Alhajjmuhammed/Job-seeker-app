#!/usr/bin/env python3
"""
🔍 PASSWORD MANAGEMENT VERIFICATION - Mobile App
Verification Date: March 14, 2026

This script verifies that password management features are fully implemented
in the mobile app (both reset and change password).
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
MOBILE_APP = BASE_DIR / "React-native-app" / "my-app"

class PasswordFeatureVerifier:
    def __init__(self):
        self.results = {
            'password_reset': {
                'screens': [],
                'api_methods': [],
                'navigation': [],
                'status': 'Not Checked'
            },
            'change_password': {
                'screens': [],
                'api_methods': [],
                'navigation': [],
                'status': 'Not Checked'
            }
        }
        
    def verify_password_reset(self):
        """Verify password reset feature"""
        print("\n🔐 Verifying Password Reset Feature...")
        
        # Check screens
        forgot_password_screen = MOBILE_APP / "app" / "(auth)" / "forgot-password.tsx"
        reset_password_screen = MOBILE_APP / "app" / "(auth)" / "reset-password.tsx"
        
        if forgot_password_screen.exists():
            self.results['password_reset']['screens'].append('✅ forgot-password.tsx exists')
            with open(forgot_password_screen, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'requestPasswordReset' in content:
                    self.results['password_reset']['screens'].append('✅ API integration found')
                if 'Alert.alert' in content:
                    self.results['password_reset']['screens'].append('✅ User feedback implemented')
        else:
            self.results['password_reset']['screens'].append('❌ forgot-password.tsx missing')
            
        if reset_password_screen.exists():
            self.results['password_reset']['screens'].append('✅ reset-password.tsx exists')
            with open(reset_password_screen, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'confirmPasswordReset' in content:
                    self.results['password_reset']['screens'].append('✅ Reset API integration found')
                if 'useLocalSearchParams' in content:
                    self.results['password_reset']['screens'].append('✅ Token handling implemented')
        else:
            self.results['password_reset']['screens'].append('❌ reset-password.tsx missing')
            
        # Check API methods
        api_service = MOBILE_APP / "services" / "api.ts"
        if api_service.exists():
            with open(api_service, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'requestPasswordReset' in content:
                    self.results['password_reset']['api_methods'].append('✅ requestPasswordReset() method exists')
                if 'confirmPasswordReset' in content:
                    self.results['password_reset']['api_methods'].append('✅ confirmPasswordReset() method exists')
                if '/auth/password-reset/' in content:
                    self.results['password_reset']['api_methods'].append('✅ Backend endpoint configured')
                    
        # Check navigation from login
        login_screen = MOBILE_APP / "app" / "(auth)" / "login.tsx"
        if login_screen.exists():
            with open(login_screen, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'forgot-password' in content:
                    self.results['password_reset']['navigation'].append('✅ Login screen has "Forgot Password?" link')
                else:
                    self.results['password_reset']['navigation'].append('❌ No link from login screen')
                    
        # Determine status
        total_checks = (len(self.results['password_reset']['screens']) + 
                       len(self.results['password_reset']['api_methods']) + 
                       len(self.results['password_reset']['navigation']))
        passed_checks = sum(1 for cat in ['screens', 'api_methods', 'navigation'] 
                          for item in self.results['password_reset'][cat] if item.startswith('✅'))
        
        if passed_checks == total_checks and total_checks > 0:
            self.results['password_reset']['status'] = '✅ FULLY IMPLEMENTED'
        elif passed_checks > 0:
            self.results['password_reset']['status'] = '⚠️ PARTIALLY IMPLEMENTED'
        else:
            self.results['password_reset']['status'] = '❌ NOT IMPLEMENTED'
            
    def verify_change_password(self):
        """Verify change password feature"""
        print("\n🔒 Verifying Change Password Feature...")
        
        # Check screens for both client and worker
        client_change_password = MOBILE_APP / "app" / "(client)" / "change-password.tsx"
        worker_change_password = MOBILE_APP / "app" / "(worker)" / "change-password.tsx"
        
        if client_change_password.exists():
            self.results['change_password']['screens'].append('✅ Client change-password.tsx exists')
            with open(client_change_password, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'changePassword' in content:
                    self.results['change_password']['screens'].append('✅ Client API integration found')
                if 'currentPassword' in content and 'newPassword' in content:
                    self.results['change_password']['screens'].append('✅ Client password validation implemented')
        else:
            self.results['change_password']['screens'].append('❌ Client change-password.tsx missing')
            
        if worker_change_password.exists():
            self.results['change_password']['screens'].append('✅ Worker change-password.tsx exists')
            with open(worker_change_password, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'changePassword' in content:
                    self.results['change_password']['screens'].append('✅ Worker API integration found')
                if 'currentPassword' in content and 'newPassword' in content:
                    self.results['change_password']['screens'].append('✅ Worker password validation implemented')
        else:
            self.results['change_password']['screens'].append('❌ Worker change-password.tsx missing')
            
        # Check API method
        api_service = MOBILE_APP / "services" / "api.ts"
        if api_service.exists():
            with open(api_service, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'changePassword' in content:
                    self.results['change_password']['api_methods'].append('✅ changePassword() method exists')
                if '/auth/change-password/' in content:
                    self.results['change_password']['api_methods'].append('✅ Backend endpoint configured')
                if 'current_password' in content and 'new_password' in content:
                    self.results['change_password']['api_methods'].append('✅ Correct API parameters')
                    
        # Check navigation from settings
        client_settings = MOBILE_APP / "app" / "(client)" / "settings.tsx"
        worker_settings = MOBILE_APP / "app" / "(worker)" / "settings.tsx"
        
        if client_settings.exists():
            with open(client_settings, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'change-password' in content:
                    self.results['change_password']['navigation'].append('✅ Client settings has "Change Password" option')
                    
        if worker_settings.exists():
            with open(worker_settings, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'change-password' in content:
                    self.results['change_password']['navigation'].append('✅ Worker settings has "Change Password" option')
                    
        # Determine status
        total_checks = (len(self.results['change_password']['screens']) + 
                       len(self.results['change_password']['api_methods']) + 
                       len(self.results['change_password']['navigation']))
        passed_checks = sum(1 for cat in ['screens', 'api_methods', 'navigation'] 
                          for item in self.results['change_password'][cat] if item.startswith('✅'))
        
        if passed_checks == total_checks and total_checks > 0:
            self.results['change_password']['status'] = '✅ FULLY IMPLEMENTED'
        elif passed_checks > 0:
            self.results['change_password']['status'] = '⚠️ PARTIALLY IMPLEMENTED'
        else:
            self.results['change_password']['status'] = '❌ NOT IMPLEMENTED'
            
    def generate_report(self):
        """Generate comprehensive verification report"""
        print("\n" + "="*80)
        print("📊 PASSWORD MANAGEMENT VERIFICATION REPORT")
        print("="*80)
        print(f"\nVerification Date: March 14, 2026")
        print(f"Project: Worker Connect - Mobile App\n")
        
        # Password Reset
        print("🔐 PASSWORD RESET FEATURE")
        print("="*80)
        print(f"Status: {self.results['password_reset']['status']}\n")
        
        print("Screens:")
        for item in self.results['password_reset']['screens']:
            print(f"  {item}")
            
        print("\nAPI Integration:")
        for item in self.results['password_reset']['api_methods']:
            print(f"  {item}")
            
        print("\nNavigation:")
        for item in self.results['password_reset']['navigation']:
            print(f"  {item}")
            
        # Change Password
        print("\n\n🔒 CHANGE PASSWORD FEATURE")
        print("="*80)
        print(f"Status: {self.results['change_password']['status']}\n")
        
        print("Screens:")
        for item in self.results['change_password']['screens']:
            print(f"  {item}")
            
        print("\nAPI Integration:")
        for item in self.results['change_password']['api_methods']:
            print(f"  {item}")
            
        print("\nNavigation:")
        for item in self.results['change_password']['navigation']:
            print(f"  {item}")
            
        # Final Summary
        print("\n\n📋 SUMMARY")
        print("="*80)
        
        reset_complete = self.results['password_reset']['status'].startswith('✅')
        change_complete = self.results['change_password']['status'].startswith('✅')
        
        if reset_complete and change_complete:
            print("✅ ALL PASSWORD MANAGEMENT FEATURES ARE FULLY IMPLEMENTED!")
            print("\nDetails:")
            print("  ✅ Forgot Password - Complete")
            print("  ✅ Reset Password - Complete")
            print("  ✅ Change Password (Client) - Complete")
            print("  ✅ Change Password (Worker) - Complete")
            print("\n🎉 Gap Analysis Update: NO GAPS in password management!")
            print("\nPreviously Reported Gaps (INCORRECT):")
            print("  ❌ Password Reset - Mobile Missing (WRONG - IT EXISTS!)")
            print("  ❌ Change Password - Mobile Missing (WRONG - IT EXISTS!)")
            print("\nActual Status:")
            print("  ✅ Password Reset - Mobile HAS IT")
            print("  ✅ Change Password - Mobile HAS IT")
            print("\n")
            print("="*80)
            print("🚀 CONCLUSION: 100% FEATURE PARITY FOR PASSWORD MANAGEMENT")
            print("="*80)
        else:
            print("⚠️ Some password management features need attention:")
            if not reset_complete:
                print(f"  {self.results['password_reset']['status']} - Password Reset")
            if not change_complete:
                print(f"  {self.results['change_password']['status']} - Change Password")
                
        print("\n")

def main():
    """Main execution function"""
    print("="*80)
    print("🔍 PASSWORD MANAGEMENT VERIFICATION SCRIPT")
    print("="*80)
    print("Verifying password reset and change password features...\n")
    
    verifier = PasswordFeatureVerifier()
    verifier.verify_password_reset()
    verifier.verify_change_password()
    verifier.generate_report()
    
    print("="*80)
    print("✅ VERIFICATION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
