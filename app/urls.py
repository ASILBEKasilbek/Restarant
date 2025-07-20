from .views import *
from django.urls import path
from django.contrib.auth import views

urlpatterns =[
    path('', index, name='index'), 
    path('login/',views.LoginView.as_view(template_name='login.html'),name='login'),
    path('logout/',views.LogoutView.as_view(next_page='login.html'),name='logout'),
    path('register/',register,name='register'),
    path('restaurant/<slug:slug>/', RestaurantMenuView.as_view(), name='restaurant_menu'),
    path('restaurant/<slug:slug>/order/', OrderCreateView.as_view(), name='order_create'),
    path('order/<int:order_id>/status/', OrderStatusView.as_view(), name='order_status'),
    path('telegram/webhook/', TelegramWebhookView.as_view(), name='telegram_webhook'),
]
