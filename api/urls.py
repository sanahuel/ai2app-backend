from django.urls import path
from . import views
from django.views.decorators.csrf import csrf_exempt
from .views import NewView, ControlView, ControlExpView, ResultView, ResultExpView

urlpatterns = [
    path('new/', NewView.as_view()),
    path('results/', ResultView.as_view()),
    path('results/<int:pk>', ResultExpView.as_view()),
    path('control/', ControlView.as_view()),
    path('control/<int:pk>', csrf_exempt(ControlExpView.as_view()))
]