from django.contrib import admin
from .models import Restaurant, Table, Category, MenuItem, Staff, UserProfile, Cart, CartItem, Order, OrderItem, Review, LoyaltyTransaction, InventoryTransaction, AdminDashboard, Image

# Image modelini ro'yxatdan o'tkazish
@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['caption', 'image', 'created_at']
    search_fields = ['caption']
    list_filter = ['created_at']

# RestaurantAdmin ni yangilash
@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'address', 'phone_number', 'is_active', 'cached_average_rating', 'owner']
    list_filter = ['is_active']
    search_fields = ['name', 'address']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']
    filter_horizontal = ['images']  # images maydoni uchun qulay interfeys

# Qolgan admin sinflari o'zgarishsiz qoladi
@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['restaurant', 'table_number', 'qr_code', 'capacity']
    list_filter = ['restaurant']
    search_fields = ['table_number', 'qr_code']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'restaurant', 'order']
    list_filter = ['restaurant']
    search_fields = ['name']
    list_editable = ['order']

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'restaurant', 'category', 'price', 'discount_price', 'is_available', 'stock_quantity']
    list_filter = ['restaurant', 'category', 'is_available']
    search_fields = ['name', 'description']
    list_editable = ['is_available', 'stock_quantity']

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['user', 'restaurant', 'role']
    list_filter = ['restaurant', 'role']
    search_fields = ['user__username']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'loyalty_points', 'preferred_language']
    search_fields = ['user__username', 'phone_number']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user_profile', 'restaurant', 'table', 'total_price']
    list_filter = ['restaurant']
    search_fields = ['user_profile__user__username']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'menu_item', 'quantity']
    list_filter = ['cart__restaurant']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'restaurant', 'user_profile', 'table', 'status', 'total_price', 'created_at']
    list_filter = ['restaurant', 'status', 'created_at']
    search_fields = ['id', 'user_profile__user__username']
    list_editable = ['status']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'menu_item', 'quantity', 'price']
    list_filter = ['order__restaurant']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['order', 'user_profile', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['order__id', 'user_profile__user__username']

@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ['user_profile', 'order', 'points', 'transaction_type', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['user_profile__user__username']

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ['menu_item', 'quantity', 'description', 'created_at']
    list_filter = ['created_at']
    search_fields = ['menu_item__name', 'description']

@admin.register(AdminDashboard)
class AdminDashboardAdmin(admin.ModelAdmin):
    list_display = ['total_restaurants', 'total_users', 'total_orders', 'total_revenue']
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False