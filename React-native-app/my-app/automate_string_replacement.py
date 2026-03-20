"""
Phase 3: Intelligent string replacement with t() calls
Maps hardcoded strings to appropriate translation keys
"""
import os
import re
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
APP_DIR = BASE_DIR / "app"
TRANSLATIONS_FILE = BASE_DIR / "translations" / "en.json"

# Load translation keys
with open(TRANSLATIONS_FILE, 'r', encoding='utf-8') as f:
    TRANSLATIONS = json.load(f)

# Build reverse mapping: English string -> translation key
STRING_TO_KEY = {}

def flatten_translations(obj, prefix=""):
    """Recursively flatten translation object to key-value pairs"""
    for key, value in obj.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flatten_translations(value, full_key)
        elif isinstance(value, str):
            STRING_TO_KEY[value.lower()] = full_key

flatten_translations(TRANSLATIONS)

# Additional common patterns with their translation keys
PATTERN_MAPPINGS = [
    # Exact matches
    (r'\bProfile\b', 'profile.title'),
    (r'\bNotifications\b', 'nav.notifications'),
    (r'\bMessages\b', 'nav.messages'),
    (r'\bSettings\b', 'nav.settings'),
    (r'\bDashboard\b', 'nav.dashboard'),
    (r'\bJobs\b', 'nav.jobs'),
    (r'\bMy Jobs\b', 'jobs.myJobs'),
    (r'\bEarnings\b', 'nav.earnings'),
    (r'\bDocuments\b', 'nav.documents'),
    (r'\bHelp\b', 'nav.help'),
    (r'\bSupport\b', 'nav.support'),
    
    # Common actions
    (r'\bSave\b', 'common.save'),
    (r'\bCancel\b', 'common.cancel'),
    (r'\bEdit\b', 'common.edit'),
    (r'\bDelete\b', 'common.delete'),
    (r'\bSubmit\b', 'common.submit'),
    (r'\bContinue\b', 'worker.continue'),
    (r'\bSkip\b', 'worker.skip'),
    (r'\bConfirm\b', 'common.confirm'),
    (r'\bBack\b', 'common.back'),
    
    # States
    (r'\bLoading\.\.\.\b', 'common.loading'),
    (r'\bError\b', 'common.error'),
    (r'\bSuccess\b', 'common.success'),
    (r'\bPending\b', 'assignments.pending'),
    (r'\bActive\b', 'assignments.active'),
    (r'\bCompleted\b', 'assignments.completed'),
]

def get_translation_key(text):
    """Find the best translation key for a given text"""
    text_lower = text.lower().strip()
    
    # Direct match
    if text_lower in STRING_TO_KEY:
        return STRING_TO_KEY[text_lower]
    
    # Pattern match
    for pattern, key in PATTERN_MAPPINGS:
        if re.search(pattern, text, re.IGNORECASE):
            return key
    
    return None

def replace_in_text_tags(content):
    """Replace strings in <Text> tags"""
    def replacer(match):
        before = match.group(1)  # <Text attributes>
        text = match.group(2)    # The actual text
        after = match.group(3)   # </Text>
        
        # Skip if already using t()
        if text.strip().startswith('{t(') or text.strip().startswith('{`'):
            return match.group(0)
        
        # Skip if it's already a variable
        if text.strip().startswith('{') and text.strip().endswith('}'):
            return match.group(0)
        
        # Try to find translation key
        key = get_translation_key(text)
        if key:
            return f"{before}{{t('{key}')}}{after}"
        
        return match.group(0)
    
    # Pattern: <Text...>text content</Text>
    pattern = r'(<Text[^>]*>)([^<{]+)(</Text>)'
    return re.sub(pattern, replacer, content)

def replace_in_alerts(content):
    """Replace strings in Alert.alert() calls"""
    def replacer(match):
        full_match = match.group(0)
        title = match.group(1)
        message = match.group(2) if match.group(2) else None
        
        title_key = get_translation_key(title)
        if title_key:
            new_title = f"t('{title_key}')"
        else:
            new_title = f"'{title}'"
        
        if message:
            message_key = get_translation_key(message)
            if message_key:
                new_message = f"t('{message_key}')"
            else:
                new_message = f"'{message}'"
            return f"Alert.alert({new_title}, {new_message}"
        else:
            return f"Alert.alert({new_title}"
    
    # Pattern: Alert.alert('Title', 'Message'
    pattern = r"Alert\.alert\(['\"]([^'\"]+)['\"](?:,\s*['\"]([^'\"]+)['\"])?"
    return re.sub(pattern, replacer, content)

def replace_placeholders(content):
    """Replace placeholder attributes"""
    def replacer(match):
        text = match.group(1)
        key = get_translation_key(text)
        if key:
            return f"placeholder={{t('{key}')}}"
        return match.group(0)
    
    pattern = r'placeholder=["\']([^"\']+)["\']'
    return re.sub(pattern, replacer, content)

def process_file(file_path):
    """Process a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip if no useTranslation
        if 'useTranslation' not in content:
            return False, "no_hook"
        
        original_content = content
        
        # Apply replacements
        content = replace_in_text_tags(content)
        content = replace_in_alerts(content)
        content = replace_placeholders(content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "success"
        else:
            return False, "no_changes"
            
    except Exception as e:
        return False, f"error: {e}"

def main():
    """Process all files with useTranslation"""
    print("🚀 Phase 3: Replacing hardcoded strings with t() calls...\n")
    print(f"📚 Loaded {len(STRING_TO_KEY)} translation mappings\n")
    
    # Get all .tsx files
    tsx_files = []
    for root, dirs, files in os.walk(APP_DIR):
        for file in files:
            if file.endswith('.tsx') and '_layout' not in file:
                tsx_files.append(Path(root) / file)
    
    stats = {"success": 0, "no_changes": 0, "error": 0}
    
    for file_path in sorted(tsx_files):
        rel_path = str(file_path.relative_to(APP_DIR))
        updated, status = process_file(file_path)
        
        if updated:
            print(f"✅ {rel_path}")
            stats["success"] += 1
        elif status == "no_changes":
            # Silently skip
            stats["no_changes"] += 1
        elif status != "no_hook":
            print(f"⚠️  {rel_path}: {status}")
            stats["error"] += 1
    
    print(f"\n{'='*60}")
    print(f"✨ Phase 3 Complete!")
    print(f"{'='*60}")
    print(f"✅ Files  updated: {stats['success']}")
    print(f"⚠️  No changes: {stats['no_changes']}")
    print(f"❌ Errors: {stats['error']}")
    
    print(f"\n📝 Next steps:")
    print("1. Review all changes in VS Code")
    print("2. Manually fix complex strings that need context") 
    print("3. Test each screen with language switching")
    print("4. Add missing translations to sw/fr/it.json files")

if __name__ == "__main__":
    main()
