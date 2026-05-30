from django.shortcuts import render
from django.conf import settings


# Update APK_FILENAME each time you upload a new APK to the server
APK_FILENAME = 'worker-connect.apk'
APK_VERSION = '1.0.0'
APK_SIZE = '~86 MB'


def download_app(request):
    """
    Public download page for the Worker Connect Android app.
    Serves a page with a direct APK download link and QR code.
    """
    # Build the absolute APK URL
    base_url = getattr(settings, 'APK_BASE_URL', None)
    if base_url is None:
        # Auto-detect from request
        scheme = 'https' if request.is_secure() else 'http'
        base_url = f"{scheme}://{request.get_host()}"

    apk_url = f"{base_url}/static/apk/{APK_FILENAME}"

    context = {
        'apk_url': apk_url,
        'app_version': APK_VERSION,
        'apk_size': APK_SIZE,
    }
    return render(request, 'download.html', context)
