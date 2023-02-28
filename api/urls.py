from django.urls import path
from . import views

urlpatterns = [
    path('', views.getRoutes,  name="routes"),
    #path('ensayos/', views.getEnsayos, name="Ensayos"),
    #path('send/', views.createEnsayo, name="Create")
]