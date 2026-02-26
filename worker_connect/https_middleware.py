"""
Middleware to handle HTTPS requests in development
Shows a helpful error page instead of just failing
"""

from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings


class DevelopmentHTTPSWarningMiddleware:
    """
    Middleware to detect HTTPS requests in development and show helpful message
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only in DEBUG mode (development)
        # Check multiple ways to detect HTTPS
        is_https = (
            request.is_secure() or 
            request.META.get('HTTP_X_FORWARDED_PROTO') == 'https' or
            request.META.get('wsgi.url_scheme') == 'https' or
            request.scheme == 'https'
        )
        
        if settings.DEBUG and is_https:
            # Check if request is over HTTPS
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>HTTPS Not Supported in Development</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                        max-width: 800px;
                        margin: 50px auto;
                        padding: 20px;
                        background: #f5f5f5;
                    }
                    .container {
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }
                    h1 {
                        color: #e74c3c;
                        margin-top: 0;
                    }
                    .warning {
                        background: #fff3cd;
                        border-left: 4px solid #ffc107;
                        padding: 15px;
                        margin: 20px 0;
                    }
                    .solution {
                        background: #d4edda;
                        border-left: 4px solid #28a745;
                        padding: 15px;
                        margin: 20px 0;
                    }
                    .url-box {
                        background: #f8f9fa;
                        border: 2px solid #007bff;
                        padding: 15px;
                        margin: 15px 0;
                        border-radius: 5px;
                        font-size: 18px;
                        font-weight: bold;
                        color: #007bff;
                        text-align: center;
                    }
                    code {
                        background: #f4f4f4;
                        padding: 2px 6px;
                        border-radius: 3px;
                        font-family: 'Courier New', monospace;
                    }
                    .btn {
                        display: inline-block;
                        padding: 12px 30px;
                        background: #007bff;
                        color: white;
                        text-decoration: none;
                        border-radius: 5px;
                        margin: 10px 5px;
                        font-weight: bold;
                    }
                    .btn:hover {
                        background: #0056b3;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>⚠️ HTTPS Not Supported in Development</h1>
                    
                    <div class="warning">
                        <strong>Problem:</strong> You're trying to access this Django development server using HTTPS, 
                        but the development server only supports HTTP (not HTTPS).
                    </div>
                    
                    <div class="solution">
                        <h2>✅ Solution: Use HTTP Instead</h2>
                        <p>Click the button below or copy the URL:</p>
                        
                        <div class="url-box">
                            http://127.0.0.1:8080/
                        </div>
                        
                        <div style="text-align: center;">
                            <a href="http://127.0.0.1:8080/" class="btn">Go to HTTP Version</a>
                            <a href="http://127.0.0.1:8080/admin/" class="btn">Admin Panel</a>
                            <a href="http://127.0.0.1:8080/api/docs/" class="btn">API Docs</a>
                        </div>
                    </div>
                    
                    <h3>🔧 Permanent Fix:</h3>
                    <ol>
                        <li><strong>Clear your browser's HSTS cache:</strong>
                            <ul>
                                <li>Chrome/Edge: Go to <code>chrome://net-internals/#hsts</code></li>
                                <li>Under "Delete domain security policies", enter: <code>localhost</code> and <code>127.0.0.1</code></li>
                                <li>Click "Delete" for each</li>
                            </ul>
                        </li>
                        <li><strong>Or use Private/Incognito mode:</strong>
                            <ul>
                                <li>Press <code>Ctrl+Shift+N</code> in Chrome/Edge</li>
                                <li>Then go to: <code>http://127.0.0.1:8080/</code></li>
                            </ul>
                        </li>
                    </ol>
                    
                    <h3>🔐 Login Credentials:</h3>
                    <ul>
                        <li><strong>Admin:</strong> admin@test.com / test1234</li>
                        <li><strong>Client:</strong> client@test.com / test1234</li>
                        <li><strong>Worker:</strong> worker@test.com / test1234</li>
                    </ul>
                    
                    <hr style="margin: 30px 0;">
                    
                    <p style="color: #666; font-size: 14px;">
                        <strong>Why this happens:</strong> Your browser automatically redirects HTTP to HTTPS because 
                        it remembers that this domain used HTTPS before (HSTS policy). In development, we use HTTP 
                        for simplicity. In production, you should always use HTTPS.
                    </p>
                </div>
            </body>
            </html>
            """
            
            return HttpResponse(html_content, status=200)
        
        # Normal processing
        response = self.get_response(request)
        return response
