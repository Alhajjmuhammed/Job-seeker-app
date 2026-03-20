"""
Verify translation coverage across all mobile screens
Shows which screens are fully translated vs need manual work
"""
import os
import re
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).parent
APP_DIR = BASE_DIR / "app"

def analyze_file(file_path):
    """Analyze a single file for translation patterns"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for useTranslation
        has_hook = 'useTranslation' in content and 'const { t }' in content
        
        # Count t() calls
        t_calls = len(re.findall(r"t\(['\"][\w.]+['\"]\)", content))
        
        # Find hardcoded strings (rough estimate)
        # Strings in <Text> tags without t()
        text_tags = re.findall(r'<Text[^>]*>([^<{]+)</Text>', content)
        hardcoded_in_text = len([s for s in text_tags if s.strip() and not s.strip().startswith('{')])
        
        # Alert messages without t()
        alert_calls = re.findall(r"Alert\.alert\(['\"]([^'\"]+)['\"]", content)
        hardcoded_alerts = len([a for a in alert_calls if not a.startswith('t(')])
        
        # Placeholders without t()
        placeholders = re.findall(r'placeholder=["\']([^"\']+)["\']', content)
        hardcoded_placeholders = len([p for p in placeholders if not p.startswith('{')])
        
        return {
            'has_hook': has_hook,
            't_calls': t_calls,
            'hardcoded_text': hardcoded_in_text,
            'hardcoded_alerts': hardcoded_alerts,
            'hardcoded_placeholders': hardcoded_placeholders,
            'total_hardcoded': hardcoded_in_text + hardcoded_alerts + hardcoded_placeholders
        }
    except Exception as e:
        return None

def main():
    print("🔍 Verifying Translation Coverage...\n")
    
    # Get all .tsx files
    tsx_files = []
    for root, dirs, files in os.walk(APP_DIR):
        for file in files:
            if file.endswith('.tsx') and '_layout' not in file:
                tsx_files.append(Path(root) / file)
    
    # Analyze each file
    results = defaultdict(list)
    total_t_calls = 0
    total_hardcoded = 0
    
    for file_path in sorted(tsx_files):
        rel_path = str(file_path.relative_to(APP_DIR))
        analysis = analyze_file(file_path)
        
        if not analysis:
            continue
        
        total_t_calls += analysis['t_calls']
        total_hardcoded += analysis['total_hardcoded']
        
        # Categorize
        if not analysis['has_hook']:
            results['no_hook'].append(rel_path)
        elif analysis['total_hardcoded'] == 0 and analysis['t_calls'] > 0:
            results['fully_translated'].append((rel_path, analysis['t_calls']))
        elif analysis['t_calls'] > 0 and analysis['total_hardcoded'] > 0:
            results['partially_translated'].append((rel_path, analysis['t_calls'], analysis['total_hardcoded']))
        elif analysis['t_calls'] == 0:
            results['has_hook_no_strings'].append(rel_path)
    
    # Print results
    print("="*70)
    print("✅ FULLY TRANSLATED SCREENS")
    print("="*70)
    for path, t_count in sorted(results['fully_translated']):
        print(f"✅ {path:<50} ({t_count} translations)")
    
    print(f"\n{'='*70}")
    print("⚠️  PARTIALLY TRANSLATED (Need Manual Review)")
    print("="*70)
    for path, t_count, hard_count in sorted(results['partially_translated']):
        print(f"⚠️  {path:<45} {t_count} t() | {hard_count} hardcoded")
    
    print(f"\n{'='*70}")
    print("📊 SUMMARY")
    print("="*70)
    print(f"✅ Fully translated: {len(results['fully_translated'])}")
    print(f"⚠️  Partially translated: {len(results['partially_translated'])}")
    print(f"❌ No translation hook: {len(results['no_hook'])}")
    print(f"🔧 Has hook but no strings: {len(results['has_hook_no_strings'])}")
    print(f"\n📈 Total t() calls across all files: {total_t_calls}")
    print(f"⚠️  Estimated hardcoded strings remaining: {total_hardcoded}")
    
    coverage_percentage = (total_t_calls / (total_t_calls + total_hardcoded) * 100) if (total_t_calls + total_hardcoded) > 0 else 0
    print(f"\n🎯 Translation Coverage: {coverage_percentage:.1f}%")
    
    if results['partially_translated']:
        print(f"\n💡 TIP: Review the {len(results['partially_translated'])} partially translated files above.")
        print("   These files have both t() calls and hardcoded strings.")
        print("   Manually replace remaining strings with appropriate t() keys.")

if __name__ == "__main__":
    main()
