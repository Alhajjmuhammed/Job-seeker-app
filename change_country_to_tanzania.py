#!/usr/bin/env python3
"""
Country Change Script: Sudan → Tanzania
Changes all country references from Sudan to Tanzania
"""

import os
from pathlib import Path

def main():
    """Main function to update country references"""
    base_dir = Path(__file__).parent
    
    changes = [
        # Worker model
        {
            'file': base_dir / 'workers' / 'models.py',
            'old': "    country = models.CharField(max_length=100, default='Sudan')",
            'new': "    country = models.CharField(max_length=100, default='Tanzania')"
        },
        # Client model
        {
            'file': base_dir / 'clients' / 'models.py',
            'old': "    country = models.CharField(max_length=100, default='Sudan')",
            'new': "    country = models.CharField(max_length=100, default='Tanzania')"
        },
        # Worker forms - country choices (line with South Sudan will be different)
        {
            'file': base_dir / 'workers' / 'forms.py',
            'old': "    ('South Sudan', 'South Sudan'),",
            'new': "    ('Tanzania', 'Tanzania'),"
        },
        # React Native profile edit - line 51
        {
            'file': base_dir / 'React-native-app' / 'my-app' / 'app' / '(worker)' / 'profile-edit.tsx',
            'old': "  const [country, setCountry] = useState('Sudan');",
            'new': "  const [country, setCountry] = useState('Tanzania');"
        },
        # React Native profile edit - line 394
        {
            'file': base_dir / 'React-native-app' / 'my-app' / 'app' / '(worker)' / 'profile-edit.tsx',
            'old': "      setCountry(profileData.country || 'Sudan');",
            'new': "      setCountry(profileData.country || 'Tanzania');"
        },
        # React Native profile edit - Picker Sudan item
        {
            'file': base_dir / 'React-native-app' / 'my-app' / 'app' / '(worker)' / 'profile-edit.tsx',
            'old': '                  <Picker.Item label="Sudan" value="Sudan" />',
            'new': '                  <Picker.Item label="Tanzania" value="Tanzania" />'
        },
        # React Native profile edit - Picker South Sudan item (remove)
        {
            'file': base_dir / 'React-native-app' / 'my-app' / 'app' / '(worker)' / 'profile-edit.tsx',
            'old': '                  <Picker.Item label="South Sudan" value="South Sudan" />\n',
            'new': ''
        },
        # Experience add form placeholder
        {
            'file': base_dir / 'React-native-app' / 'my-app' / 'app' / '(worker)' / 'experience' / 'add.tsx',
            'old': '              placeholder="e.g., Khartoum, Sudan"',
            'new': '              placeholder="e.g., Dar es Salaam, Tanzania"'
        },
        # Experience edit form placeholder
        {
            'file': base_dir / 'React-native-app' / 'my-app' / 'app' / '(worker)' / 'experience' / '[id]' / 'edit.tsx',
            'old': '              placeholder="e.g., Khartoum, Sudan"',
            'new': '              placeholder="e.g., Dar es Salaam, Tanzania"'
        },
        # Test users script - worker 1
        {
            'file': base_dir / 'create_test_users.py',
            'old': "                'country': 'Sudan'",
            'new': "                'country': 'Tanzania'"
        },
    ]
    
    print("🔄 Starting country change: Sudan → Tanzania")
    print(f"📁 Base directory: {base_dir}")
    print()
    
    success_count = 0
    for change in changes:
        file_path = change['file']
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path.relative_to(base_dir)}")
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if change['old'] in content:
                content = content.replace(change['old'], change['new'], 1)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ Updated: {file_path.relative_to(base_dir)}")
                success_count += 1
            else:
                print(f"⚠️  Pattern not found in: {file_path.relative_to(base_dir)}")
        
        except Exception as e:
            print(f"❌ Error processing {file_path.relative_to(base_dir)}: {e}")
    
    print()
    print("=" * 60)
    print(f"✅ Country change complete: {success_count} files updated")
    print("=" * 60)

if __name__ == '__main__':
    main()
