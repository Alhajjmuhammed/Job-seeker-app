#!/usr/bin/env python3
"""
Clean up URL configuration to remove duplicate namespace warnings
"""

def fix_url_duplicates():
    """Remove duplicate URL includes to fix namespace warnings"""
    
    url_file = "worker_connect/urls.py"
    
    # Read current content
    try:
        with open(url_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        print(f"📝 Current {url_file} size: {len(content)} characters")
        
        # The main issue is duplicate includes for the same namespace
        # We need to remove some of the mobile compatibility duplicates
        
        # Remove duplicate includes that cause namespace conflicts
        fixes = [
            # Remove duplicate search includes
            ("    path('api/search/', include('worker_connect.search_urls')),  # Mobile compatibility\n", ""),
            # Remove duplicate chat includes  
            ("    path('api/chat/', include('worker_connect.chat_urls')),  # Mobile compatibility\n", ""),
            # Remove duplicate messaging includes
            ("    path('api/messages/', include('jobs.messaging_urls')),  # Mobile compatibility\n", ""),
        ]
        
        new_content = content
        changes_made = 0
        
        for old, new in fixes:
            if old in new_content:
                new_content = new_content.replace(old, new)
                changes_made += 1
                print(f"✅ Removed duplicate include")
        
        if changes_made > 0:
            # Write back the cleaned content
            with open(url_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"📝 Updated {url_file} with {changes_made} changes")
            return True
        else:
            print("ℹ️  No duplicate includes found to remove")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🛠️  FIXING URL NAMESPACE DUPLICATES")
    print("=" * 50)
    
    if fix_url_duplicates():
        print("✅ URL configuration cleaned up!")
    else:
        print("ℹ️  URL configuration is already clean")

if __name__ == "__main__":
    main()