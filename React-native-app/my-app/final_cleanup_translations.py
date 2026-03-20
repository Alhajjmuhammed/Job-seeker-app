"""
Final Cleanup: Fix all remaining hardcoded strings in partially translated files
Uses pattern matching to replace common strings across all files
"""
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
APP_DIR = BASE_DIR / "app"

# Comprehensive string-to-key mapping
STRING_MAPPINGS = {
    # Common Alerts
    "Assignment not found": "t('assignments.assignmentNotFound')",
    "Failed to load assignment": "t('assignments.failedLoadAssignments')",
    "Failed to load assignment details": "t('assignments.failedLoadAssignmentDetails')",
    "Assignment Accepted!": "t('assignments.assignmentAccepted')",
    "Assignment Rejected": "t('assignments.assignmentRejected')",
    "Complete Failed": "t('assignments.completeFailed')",
    "Already Completed": "t('assignments.alreadyCompleted')",
    "Reason Required": "t('assignments.reasonRequired')",
    
    # Common UI Text
    "Client Information": "t('assignments.clientInformation')",
    "Your Response": "t('assignments.yourResponse')",
    "Accepting Assignment": "t('assignments.acceptingAssignment')",
    "Rejecting Assignment": "t('assignments.rejectingAssignment')",
    "Confirmation Message": "t('assignments.confirmationMessage')",
    "Accept Assignment": "t('assignments.acceptAssignment')",
    "Reject Assignment": "t('assignments.rejectAssignment')",
    "Complete Service": "t('assignments.completeService')",
    "Service Summary": "t('assignments.serviceSummary')",
    "Completion Notes \\*": "t('assignments.completionNotes')",
    "Completion Checklist": "t('assignments.completionChecklist')",
    "Important": "t('assignments.important')",
    "Not Yet": "t('assignments.notYet')",
    "Ready to Complete!": "t('assignments.readyToComplete')",
    "What to Include:": "t('assignments.whatToInclude')",
    
    # Auth strings
    "Enter your email": "t('auth.enterEmail')",
    "Enter your password": "t('auth.enterPassword')",
    "Please fill in all required fields": "t('auth.fillAllFields')",
    "Passwords do not match": "t('auth.passwordsNoMatch')",
    "Registration Failed": "t('auth.registrationFailed')",
    
    # Profile strings  
    "Loading profile...": "t('profile.loadingProfile')",
    "Edit Profile": "t('profile.editProfile')",
    "Save Changes": "t('common.save')",
    "Update Profile": "t('profile.updateProfile')",
    
    # Client strings
    "Request Service": "t('requestService.title')",
    "My Requests": "t('requestService.myRequests')",
    "Service Request Details": "t('requestService.details')",
    
    # Generic buttons
    "View Details": "t('common.view')",
    "View Assignment": "t('assignments.viewAssignment')",
    
    # Messages
    "Loading conversations...": "t('messages.loadingConversations')",
    "No conversations yet": "t('messages.noConversations')",
    "Send": "t('messages.send')",
    "Type a message...": "t('messages.typeMessage')",
}

def fix_text_content(content):
    """Fix hardcoded strings in <Text> tags"""
    modified = content
    
    for old_str, t_call in STRING_MAPPINGS.items():
        # Pattern: <Text...>String</Text>
        pattern = f"<Text([^>]*)>{re.escape(old_str)}</Text>"
        replacement = f"<Text\\1>{{{t_call}}}</Text>"
        modified = re.sub(pattern, replacement, modified)
    
    return modified

def fix_alert_calls(content):
    """Fix hardcoded strings in Alert.alert()"""
    modified = content
    
    for old_str, t_call in STRING_MAPPINGS.items():
        # Pattern: Alert.alert('String' or "String"
        patterns = [
            f"Alert\\.alert\\('{re.escape(old_str)}'",
            f'Alert\\.alert\\("{re.escape(old_str)}"',
        ]
        
        for pattern in patterns:
            if re.search(pattern, modified):
                replacement = f"Alert.alert({t_call}"
                modified = re.sub(pattern, replacement, modified)
    
    return modified

def fix_placeholders(content):
    """Fix placeholder attributes"""
    modified = content
    
    placeholder_mapping = {
        "Search": "t('common.search')",
        "Search jobs...": "t('jobs.searchJobs')",
        "Search messages...": "t('messages.searchMessages')",
        "Search by title, client, location...": "t('assignments.searchByTitleClient')",
        "Type a message...": "t('messages.typeMessage')",
        "Enter your email": "t('auth.enterEmail')",
        "Enter your password": "t('auth.enterPassword')",
    }
    
    for old_str, t_call in placeholder_mapping.items():
        pattern = f'placeholder=["\']{ re.escape(old_str)}["\']'
        replacement = f"placeholder={{{t_call}}}"
        modified = re.sub(pattern, replacement, modified)
    
    return modified

def process_file(file_path):
    """Process a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip if no useTranslation
        if 'useTranslation' not in content:
            return False
        
        original_content = content
        
        # Apply all fixes
        content = fix_text_content(content)
        content = fix_alert_calls(content)
        content = fix_placeholders(content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    print("🔧 Final Cleanup: Fixing remaining hardcoded strings...\n")
    
    # Get all .tsx files that have useTranslation
    tsx_files = []
    for root, dirs, files in os.walk(APP_DIR):
        for file in files:
            if file.endswith('.tsx') and '_layout' not in file:
                file_path = Path(root) / file
                # Check if file has useTranslation
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        if 'useTranslation' in f.read():
                            tsx_files.append(file_path)
                except:
                    pass
    
    updated_count = 0
    
    for file_path in sorted(tsx_files):
        rel_path = str(file_path.relative_to(APP_DIR))
        if process_file(file_path):
            print(f"✅ {rel_path}")
            updated_count += 1
    
    print(f"\n{'='*60}")
    print(f"✨ Final Cleanup Complete!")
    print(f"{'='*60}")
    print(f"✅ Files updated: {updated_count}")
    print(f"\n📝 Next: Run verify_translation_coverage.py to check progress")

if __name__ == "__main__":
    main()
