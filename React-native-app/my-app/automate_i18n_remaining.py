"""
Phase 2: Apply useTranslation to ALL remaining screens
Covers all worker and client sections comprehensively
"""
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
APP_DIR = BASE_DIR / "app"

# Files already processed (skip these)
ALREADY_DONE = {
    # Original 4
    "(worker)/dashboard.tsx",
    "(worker)/earnings.tsx",
    "(auth)/login.tsx",
    "(worker)/settings.tsx",
    # Phase 1: 15 priority files
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
}

def get_all_tsx_files():
    """Get all .tsx files in app directory"""
    tsx_files = []
    for root, dirs, files in os.walk(APP_DIR):
        for file in files:
            if file.endswith('.tsx'):
                tsx_files.append(Path(root) / file)
    return tsx_files

def get_relative_path(file_path):
    """Get path relative to app directory"""
    try:
        return str(file_path.relative_to(APP_DIR))
    except:
        return str(file_path)

def has_use_translation(content):
    """Check if file already uses useTranslation"""
    return 'useTranslation' in content

def add_use_translation_import(content):
    """Add useTranslation import after other imports"""
    if "from 'react-i18next'" in content or 'from "react-i18next"' in content:
        return content
    
    # Find the last import statement
    import_pattern = r"(import .+ from ['\"].+['\"];?\n)"
    matches = list(re.finditer(import_pattern, content))
    
    if matches:
        last_import = matches[-1]
        insert_pos = last_import.end()
        new_import = "import { useTranslation } from 'react-i18next';\n"
        content = content[:insert_pos] + new_import + content[insert_pos:]
    
    return content

def add_use_translation_hook(content):
    """Add const { t } = useTranslation(); after component declaration"""
    patterns = [
        r"(export default function \w+\([^)]*\)\s*\{)",
        r"(const \w+ = \([^)]*\) => \{)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            insert_pos = match.end()
            hook_line = "\n  const { t } = useTranslation();"
            content = content[:insert_pos] + hook_line + content[insert_pos:]
            break
    
    return content

def process_file(file_path):
    """Process a single TypeScript file"""
    rel_path = get_relative_path(file_path)
    
    # Skip if already done
    if rel_path in ALREADY_DONE:
        return False, "already_done"
    
    # Skip _layout files
    if '_layout' in rel_path:
        return False, "layout_file"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already has useTranslation
        if has_use_translation(content):
            return False, "has_translation"
        
        # Apply transformations
        original_content = content
        content = add_use_translation_import(content)
        content = add_use_translation_hook(content)
        
        # Write changes
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "success"
        else:
            return False, "no_changes"
            
    except Exception as e:
        return False, f"error: {e}"

def main():
    """Process all remaining .tsx files"""
    print("🚀 Phase 2: Processing ALL remaining screens...\n")
    
    all_files = get_all_tsx_files()
    
    stats = {
        "success": 0,
        "already_done": 0,
        "has_translation": 0,
        "layout_file": 0,
        "no_changes": 0,
        "error": 0
    }
    
    for file_path in sorted(all_files):
        rel_path = get_relative_path(file_path)
        updated, status = process_file(file_path)
        
        if updated:
            print(f"✅ {rel_path}")
            stats["success"] += 1
        elif status == "already_done":
            # print(f"⏭️  {rel_path} (already processed)")
            stats["already_done"] += 1
        elif status == "has_translation":
            # print(f"⏭️  {rel_path} (has useTranslation)")
            stats["has_translation"] += 1
        elif status == "layout_file":
            # print(f"⏭️  {rel_path} (layout file - skipped)")
            stats["layout_file"] += 1
        elif status == "no_changes":
            print(f"⚠️  {rel_path} (no changes made)")
            stats["no_changes"] += 1
        else:
            print(f"❌ {rel_path}: {status}")
            stats["error"] += 1
    
    print(f"\n{'='*60}")
    print(f"✨ Phase 2 Complete!")
    print(f"{'='*60}")
    print(f"✅ New files updated: {stats['success']}")
    print(f"⏭️  Already had translations: {stats['has_translation']}")
    print(f"⏭️  Previously processed: {stats['already_done']}")
    print(f"⏭️  Layout files skipped: {stats['layout_file']}")
    print(f"⚠️  No changes: {stats['no_changes']}")
    print(f"❌ Errors: {stats['error']}")
    print(f"\n📊 Total screens with useTranslation: {stats['success'] + stats['has_translation'] + stats['already_done']}")
    
    print(f"\n📝 Next steps:")
    print("1. Review changes in VS Code")
    print("2. Manually replace hardcoded strings with t() calls in each file")
    print("3. Use the 682 translation keys in translations/en.json")
    print("4. Test language switching")

if __name__ == "__main__":
    main()
