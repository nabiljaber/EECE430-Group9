# ajerlo/views.py
from rentals.views import home as rentals_home

def home(request):
    """
    Root '/' view.
    Delegate to the rentals home (hero + newest cars),
    just like on localhost:8000/.
    """
    return rentals_home(request)
