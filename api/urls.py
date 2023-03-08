from django.urls import path
from . import views
from .views import NewView, ControlView, ControlExpView, ResultView, ResultExpView

urlpatterns = [
    path('', views.getRoutes,  name="routes"),
    path('new/', NewView.as_view()),
    path('results/', ResultView.as_view()),
    path('results/<int:pk>', ResultExpView.as_view()),
    path('control/', ControlView.as_view()),
    path('control/<int:pk>', ControlExpView.as_view())
]