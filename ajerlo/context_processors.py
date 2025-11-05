def branding(request):
    from django.conf import settings
    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "Ajerlo"),
        "SITE_TAGLINE": getattr(settings, "SITE_TAGLINE", ""),
    }
