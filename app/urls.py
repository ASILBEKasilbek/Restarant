from .views import *
from django.urls import path
from django.contrib.auth import views

urlpatterns =[
    path('', index, name='index'), 
    path('login/',views.LoginView.as_view(template_name='login.html'),name='login'),
    path('logout/',views.LogoutView.as_view(next_page='login.html'),name='logout'),
    path('register/',register,name='register'),
]