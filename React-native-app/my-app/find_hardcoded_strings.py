"""
Helper script: Find and list all hardcoded strings that need manual translation
Outputs specific strings and their locations for easy manual fixing
"""
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
APP_DIR = BASE_DIR / "app"

def find_hardcoded_strings(file_path):
    """Find all hardcoded strings in a file"""
    hardcoded = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # Skip if no useTranslation
        if 'useTranslation' not in content:
            return []
        
        for line_num, line in enumerate(lines, 1):
            # Find strings in <Text> tags without t()
            text_matches = re.finditer(r'<Text[^>]*>([^<{]+)</Text>', line)
            for match in text_matches:
                text = match.group(1).strip()
                if text and not text.startswith('{') and len(text) > 1:
                    # Filter out common non-translatable content
                    if not re.match(r'^[\d\s\-\+\$]+$', text):  # Numbers, currency
                        hardcoded.append({
                            'type': 'text',
                            'line': line_num,
                            'string': text,
                            'context': line.strip()
                        })
            
            # Find Alert.alert without t()
            alert_matches = re.finditer(r"Alert\.alert\(['\"]([^'\"]+)['\"]", line)
            for match in alert_matches:
                text = match.group(1)
                if not text.startswith('t('):
                    hardcoded.append({
                        'type': 'alert',
                        'line': line_num,
                        'string': text,
                        'context': line.strip()
                    })
            
            # Find placeholders without t()
            placeholder_matches = re.finditer(r'placeholder=["\']([^"\']+)["\']', line)
            for match in placeholder_matches:
                text = match.group(1)
                if not text.startswith('{'):
                    hardcoded.append({
                        'type': 'placeholder',
                        'line': line_num,
                        'string': text,
                        'context': line.strip()
                    })
        
        return hardcoded
    except Exception as e:
        return []

def suggest_translation_key(string, file_path):
    """Suggest an appropriate translation key for a string"""
    rel_path = str(file_path.relative_to(APP_DIR))
    
    # Determine section based on file path
    if '(auth)' in rel_path:
        section = 'auth'
    elif '(worker)' in rel_path:
        section = 'worker'
    elif '(client)' in rel_path:
        section = 'client'
    else:
        section = 'common'
    
    # Create a key from the string
    key_part = re.sub(r'[^a-zA-Z0-9\s]', '', string.lower())
    key_part = '_'.join(key_part.split()[:3])  # First 3 words
    
    return f"{section}.{key_part}"

def main():
    print("🔍 Finding All Hardcoded Strings...\n")
    
    # Priority files with most hardcoded strings
    priority_files = [
        "(worker)\\assignments\\complete\\[id].tsx",  # 23 hardcoded
        "(worker)\\assignments\\respond\\[id].tsx",    # 18 hardcoded
        "(client)\\service-request\\[id].tsx",         # 18 hardcoded
        "(worker)\\service-assignment\\[id].tsx",      # 19 hardcoded
        "(worker)\\experience\\[id]\\edit.tsx",        # 14 hardcoded
        "(worker)\\experience\\add.tsx",               # 13 hardcoded
        "(worker)\\assignments\\clock\\in\\[id].tsx",  # 14 hardcoded
        "(worker)\\job\\[id]\\apply.tsx",              # 12 hardcoded
        "(worker)\\assignments\\clock\\out\\[id].tsx", # 12 hardcoded
        "(client)\\edit-service-request\\[id].tsx",    # 11 hardcoded
    ]
    
    print("🎯 TOP 10 FILES NEEDING MOST WORK:\n")
    
    for rel_path in priority_files:
        file_path = APP_DIR / rel_path.replace('\\\\', '\\')
        if not file_path.exists():
            continue
        
        hardcoded = find_hardcoded_strings(file_path)
        if not hardcoded:
            continue
        
        print(f"\n{'='*70}")
        print(f"📄 {rel_path} ({len(hardcoded)} strings)")
        print("="*70)
        
        for item in hardcoded[:10]:  # Show first 10
            suggested_key = suggest_translation_key(item['string'], file_path)
            print(f"\nLine {item['line']} ({item['type']}):")
            print(f"  String: \"{item['string']}\"")
            print(f"  Suggested key: t('{suggested_key}')")
            if len(item['context']) < 100:
                print(f"  Context: {item['context']}")
        
        if len(hardcoded) > 10:
            print(f"\n  ... and {len(hardcoded) - 10} more strings")
    
    print(f"\n{'='*70}")
    print("📝 HOW TO FIX MANUALLY:")
    print("="*70)
    print("1. Open the file in VS Code")
    print("2. Find the line number indicated")
    print("3. Replace the hardcoded string with t('key')")
    print("   Example: <Text>Profile</Text>  →  <Text>{t('profile.title')}</Text>")
    print("4. Add the translation to translations/en.json if not present")
    print("5. Test the screen with language switching")
    
    print(f"\n💡 TIP: Focus on the most visible strings first:")
    print("   - Page titles and headings")
    print("   - Button labels")
    print("   - Alert messages")
    print("   - Navigation labels")

if __name__ == "__main__":
    main()
