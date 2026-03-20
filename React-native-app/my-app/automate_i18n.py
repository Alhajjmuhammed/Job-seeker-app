"""
Smart i18n automation: Add useTranslation to all React Native screens
Intelligently replaces hardcoded strings with t() calls
"""
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
APP_DIR = BASE_DIR / "app"

# Files that already have useTranslation (skip these)
ALREADY_DONE = {
    "(worker)/dashboard.tsx",
    "(worker)/earnings.tsx",
    "(auth)/login.tsx",
    "(worker)/settings.tsx"
}

# String mapping for common patterns (key patterns to t() calls)
COMMON_REPLACEMENTS = {
    # Auth screens
    "Create Account": "t('auth.createAccount')",
    "Join Worker Connect today": "t('auth.joinToday')",
    "I want to:": "t('auth.iWantTo')",
    "👷 Find Work": "t('auth.findWork')",
    "I'm a worker": "t('auth.imWorker')",
    "👤 Hire Workers": "t('auth.hireWorkers')",
    "I need help": "t('auth.iNeedHelp')",
    "Worker Type *": "t('auth.workerType')",
    "Professional": "t('auth.professional')",
    "Non-Academic": "t('auth.nonAcademic')",
    "First Name *": "t('auth.firstName')",
    "Last Name *": "t('auth.lastName')",
    "Email *": "t('auth.email')",
    "Password *": "t('auth.password')",
    "Confirm Password *": "t('auth.confirmPassword')",
    "Agent Code": "t('auth.agentCode')",
    "(optional)": "t('auth.optional')",
    "Creating Account...": "t('auth.creatingAccount')",
    "Already have an account?": "t('auth.haveAccount')",
    "Sign In": "t('auth.signIn')",
    "Forgot Password?": "t('auth.forgotPassword')",
    "Reset Password": "t('auth.resetPassword')",
    "Back to Login": "t('auth.backToLogin')",
    
    # Common buttons
    "Save": "t('common.save')",
    "Cancel": "t('common.cancel')",
    "Submit": "t('common.submit')",
    "Edit": "t('common.edit')",
    "Delete": "t('common.delete')",
    "Continue": "t('worker.continue')",
    "Skip": "t('worker.skip')",
    "Loading...": "t('common.loading')",
    "Error": "t('common.error')",
    "Success": "t('common.success')",
    
    # Profile
    "Profile": "t('profile.title')",
    "My Profile": "t('profile.myProfile')",
    "Edit Profile": "t('profile.editProfile')",
    "Verified": "t('profile.verified')",
    "Available for Work": "t('profile.availableForWork')",
    "Loading profile...": "t('profile.loadingProfile')",
    
    # Notifications
    "Notifications": "t('nav.notifications')",
    "Mark all read": "t('notifications.markAllRead')",
    "All": "t('notifications.all')",
    "Unread": "t('notifications.unread')",
    "Loading notifications...": "t('notifications.loadingNotifications')",
    "No Notifications": "t('notifications.noNotifications')",
    
    # Messages
    "Messages": "t('nav.messages')",
    "Search messages...": "t('messages.searchMessages')",
    "Loading conversations...": "t('messages.loadingConversations')",
    "No conversations yet": "t('messages.noConversations')",
    
    # Jobs
    "My Jobs": "t('jobs.myJobs')",
    "Loading your jobs...": "t('jobs.loadingJobs')",
    "Browse Jobs": "t('applications.browseJobs')",
    "My Applications": "t('applications.myApplications')",
    "Search jobs...": "t('jobs.searchJobs')",
    
    # Settings
    "Settings": "t('nav.settings')",
    "Change Password": "t('settings.changePassword')",
    "Privacy Settings": "t('privacy.privacySettings')",
    
    # Documents
    "Upload Document": "t('documents.uploadDocument')",
    "Uploaded Documents": "t('documents.uploadedDocuments')",
    "National ID": "t('worker.nationalID')",
    
    # Generic
    "Pending": "t('assignments.pending')",
    "Active": "t('assignments.active')",
    "Completed": "t('assignments.completed')",
}

def get_relative_path(file_path):
    """Get path relative to app directory"""
    try:
        return str(file_path.relative_to(APP_DIR))
    except:
        return str(file_path)

def has_use_translation(content):
    """Check if file already uses useTranslation"""
    return 'useTranslation' in content and "const { t }" in content

def add_use_translation_import(content):
    """Add useTranslation import after other imports"""
    # Check if i18n import already exists
    if "from 'react-i18next'" in content or 'from "react-i18next"' in content:
        return content
    
    # Find the last import statement
    import_pattern = r"(import .+ from ['\"].+['\"];?\n)"
    matches = list(re.finditer(import_pattern, content))
    
    if matches:
        last_import = matches[-1]
        insert_pos = last_import.end()
        
        # Add the import
        new_import = "import { useTranslation } from 'react-i18next';\n"
        content = content[:insert_pos] + new_import + content[insert_pos:]
    
    return content

def add_use_translation_hook(content):
    """Add const { t } = useTranslation(); after component declaration"""
    # Find the function/export default pattern
    patterns = [
        r"(export default function \w+\([^)]*\)\s*\{)",
        r"(const \w+ = \([^)]*\) => \{)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            insert_pos = match.end()
            # Add the hook
            hook_line = "\n  const { t } = useTranslation();"
            content = content[:insert_pos] + hook_line + content[insert_pos:]
            break
    
    return content

def replace_text_strings(content):
    """Replace hardcoded strings with t() calls"""
    modified = content
    
    # Replace in Alert.alert calls
    for old_str, t_call in COMMON_REPLACEMENTS.items():
        # Pattern: Alert.alert('String' or "String"
        patterns = [
            f"Alert.alert\\('{re.escape(old_str)}'",
            f'Alert.alert\\("{re.escape(old_str)}"',
            f"Alert.alert\\('{re.escape(old_str)}'",
        ]
        
        for pattern in patterns:
            if pattern in modified:
                replacement = f"Alert.alert({t_call}"
                modified = modified.replace(pattern.replace('\\\\', '\\'), replacement)
    
    # Replace in <Text> tags
    for old_str, t_call in COMMON_REPLACEMENTS.items():
        # Pattern: <Text...>String</Text>
        pattern = f"<Text([^>]*)>{re.escape(old_str)}</Text>"
        replacement = f"<Text\\1>{{{t_call}}}</Text>"
        modified = re.sub(pattern, replacement, modified)
        
        # Pattern: <Text...>{String}</Text>  (already in braces)
        pattern = f"<Text([^>]*)>{{['\"]{ re.escape(old_str)}['\"] }}</Text>"
        replacement = f"<Text\\1>{{{t_call}}}</Text>"
        modified = re.sub(pattern, replacement, modified)
    
    # Replace placeholder attributes
    for old_str, t_call in COMMON_REPLACEMENTS.items():
        patterns = [
            f'placeholder="{re.escape(old_str)}"',
            f"placeholder='{re.escape(old_str)}'"
        ]
        for pattern in patterns:
            if pattern in modified:
                replacement = f"placeholder={{{t_call}}}"
                modified = modified.replace(pattern, replacement)
    
    return modified

def process_file(file_path):
    """Process a single TypeScript file"""
    rel_path = get_relative_path(file_path)
    
    # Skip if already done
    if rel_path in ALREADY_DONE:
        print(f"⏭️  Skipping {rel_path} (already has useTranslation)")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already has useTranslation
        if has_use_translation(content):
            print(f"⏭️  Skipping {rel_path} (already has useTranslation)")
            return False
        
        # Apply transformations
        original_content = content
        content = add_use_translation_import(content)
        content = add_use_translation_hook(content)
        content = replace_text_strings(content)
        
        # Only write if something changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Updated {rel_path}")
            return True
        else:
            print(f"⚠️  No changes for {rel_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {rel_path}: {e}")
        return False

def main():
    """Process all .tsx files in priority order"""
    print("🚀 Starting mobile app i18n automation...\n")
    
    # Priority files to process first
    priority_files = [
        "(auth)/register.tsx",
        "(auth)/forgot-password.tsx",
        "(auth)/reset-password.tsx",
        "(worker)/profile.tsx",
        "(worker)/profile-edit.tsx",
        "(worker)/notifications.tsx",
        "(worker)/messages.tsx",
        "(worker)/jobs.tsx",
        "(worker)/applications.tsx",
        "(client)/dashboard.tsx",
        "(client)/profile.tsx",
        "(client)/notifications.tsx",
        "(client)/messages.tsx",
        "(client)/my-requests.tsx",
        "(client)/request-service.tsx",
    ]
    
    updated_count = 0
    
    # Process priority files first
    print("📋 Processing priority screens...")
    for rel_path in priority_files:
        file_path = APP_DIR / rel_path
        if file_path.exists():
            if process_file(file_path):
                updated_count += 1
    
    print(f"\n✨ Completed! Updated {updated_count} files")
    print("\n📝 Next steps:")
    print("1. Review the changes in VS Code")
    print("2. Test language switching in the app")
    print("3. Manually adjust any complex strings that need context")
    print("4. Run the remaining 40+ screens with the same pattern")

if __name__ == "__main__":
    main()
