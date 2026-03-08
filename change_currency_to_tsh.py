#!/usr/bin/env python3
"""
Currency Change Script: SDG (Sudan) → TSH (Tanzania)
Changes all currency references from Sudanese Pound to Tanzanian Shilling
"""

import os
import re
from pathlib import Path

# Files and patterns to exclude
EXCLUDE_PATTERNS = [
    'node_modules',
    '__pycache__',
    '.git',
    'package-lock.json',
    'db.sqlite3',
    '.pyc',
    'change_currency_to_tsh.py',  # This script itself
]

# File extensions to process
PROCESS_EXTENSIONS = [
    '.py',
    '.html',
    '.tsx',
    '.ts',
    '.js',
    '.jsx',
]

def should_process_file(file_path):
    """Check if file should be processed"""
    path_str = str(file_path)
    
    # Check exclusions
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path_str:
            return False
    
    # Check extension
    if file_path.suffix in PROCESS_EXTENSIONS:
        return True
    
    return False

def replace_currency_in_file(file_path):
    """Replace SDG with TSH in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace SDG with TSH
        content = content.replace('SDG', 'TSH')
        content = content.replace('sdg', 'tsh')
        content = content.replace('Sdg', 'Tsh')
        
        # If content changed, write it back
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
    
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def main():
    """Main function to process all files"""
    base_dir = Path(__file__).parent
    
    files_changed = []
    files_processed = 0
    
    print("🔄 Starting currency change: SDG → TSH")
    print(f"📁 Base directory: {base_dir}")
    print()
    
    # Walk through all files
    for root, dirs, files in os.walk(base_dir):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_PATTERNS]
        
        for file in files:
            file_path = Path(root) / file
            
            if should_process_file(file_path):
                files_processed += 1
                if replace_currency_in_file(file_path):
                    relative_path = file_path.relative_to(base_dir)
                    files_changed.append(str(relative_path))
                    print(f"✅ Updated: {relative_path}")
    
    print()
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Files processed: {files_processed}")
    print(f"Files changed: {len(files_changed)}")
    print()
    
    if files_changed:
        print("Changed files:")
        for file in sorted(files_changed):
            print(f"  • {file}")
    else:
        print("No files needed changes.")
    
    print()
    print("✅ Currency change complete: All SDG → TSH")

if __name__ == '__main__':
    main()
