from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'restaurant'

urlpatterns = [
    # Homepage
    path('', views.index, name='index'),
    # Table menu view with restaurant slug and table number
    path(
        'menu/<slug:restaurant_slug>/table/<str:table_number>/',
        views.table_menu,
        name='table_menu'
    ),
    # Add to cart
    path(
        'cart/add/<slug:restaurant_slug>/',
        views.add_to_cart,
        name='add_to_cart'
    ),
    # Create order (table or general)
    path(
        'order/create/<slug:restaurant_slug>/',
        views.create_order,
        name='create_order'
    ),
    # Create delivery order
    path(
        'order/delivery/',
        views.create_delivery_order,
        name='create_delivery_order'
    ),
    # Order status
    path(
        'order/<int:order_id>/status/',
        views.order_status,
        name='order_status'
    ),
    # Cancel order
    path(
        'order/<int:order_id>/cancel/',
        views.cancel_order,
        name='cancel_order'
    ),
    # Update order status
    path(
        'order/<int:order_id>/update-status/',
        views.update_order_status,
        name='update_order_status'
    ),
    # Submit review
    path(
        'order/<int:order_id>/review/',
        views.submit_review,
        name='submit_review'
    ),
    # Restaurant ratings
    path(
        'restaurant/<slug:restaurant_slug>/ratings/',
        views.restaurant_ratings,
        name='restaurant_ratings'
    ),
    # Spend loyalty points
    path(
        'loyalty/spend/',
        views.spend_loyalty_points,
        name='spend_loyalty_points'
    ),
    # User profile
    path(
        'profile/',
        views.user_profile,
        name='user_profile'
    ),
    # Popular items
    path(
        'restaurant/<slug:restaurant_slug>/popular/',
        views.popular_items,
        name='popular_items'
    ),
    # Menu items API
    path(
        'api/menu/<slug:restaurant_slug>/',
        views.menu_items_api,
        name='menu_items_api'
    ),
]