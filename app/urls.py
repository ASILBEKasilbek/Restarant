from django.urls import path
from . import views

app_name = 'restaurant'

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Owner Panel
    path('restaurant/<slug:slug>/owner/', views.owner_dashboard, name='owner_dashboard'),
    path('restaurant/<slug:slug>/menu/', views.manage_menu, name='manage_menu'),
    path('restaurant/<slug:slug>/menu/delete/<int:item_id>/', views.delete_menu_item, name='delete_menu_item'),
    path('restaurant/<slug:slug>/staff/', views.manage_staff, name='manage_staff'),
    path('restaurant/<slug:slug>/tables/', views.manage_tables, name='manage_tables'),

    # Waiter Panel
    path('restaurant/<slug:slug>/waiter/', views.waiter_dashboard, name='waiter_dashboard'),
    path('restaurant/<slug:slug>/order/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('restaurant/<slug:slug>/stock/<int:item_id>/update/', views.update_stock, name='update_stock'),

    # Customer Panel
    path('table/<str:qr_code>/', views.table_menu, name='table_menu'),
    path('table/<str:qr_code>/add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('table/<str:qr_code>/place-order/', views.place_order, name='place_order'),
    path('order-history/', views.order_history, name='order_history'),

    # Admin Panel
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/restaurants/', views.admin_manage_restaurants, name='admin_manage_restaurants'),
]