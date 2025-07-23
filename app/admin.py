from django.contrib import admin
from .models import (
    Restaurant, Category, MenuItem, UserProfile, Cart, CartItem,
    Order, OrderItem, Review, LoyaltyTransaction
)

# Inline configurations
class CategoryInline(admin.TabularInline):
    model = Category
    extra = 1

class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 1

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0

# Admin models
@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'phone_number')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [CategoryInline, MenuItemInline]
    search_fields = ('name', 'address')
    list_filter = ('is_active',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'order')
    list_filter = ('restaurant',)
    search_fields = ('name',)

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'price', 'is_available')
    list_filter = ('restaurant', 'is_available', 'category')
    search_fields = ('name', 'description')
    autocomplete_fields = ['restaurant', 'category']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'phone_number', 'loyalty_points', 'preferred_language')
    search_fields = ('telegram_id', 'phone_number')
    list_filter = ('preferred_language',)

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'restaurant')
    inlines = [CartItemInline]
    search_fields = ('user__telegram_id',)
    list_filter = ('restaurant',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'restaurant', 'user', 'status', 'total_price', 'created_at')
    list_filter = ('status', 'restaurant')
    search_fields = ('user__telegram_id', 'delivery_address')
    inlines = [OrderItemInline, ReviewInline]
    autocomplete_fields = ['restaurant', 'user']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'menu_item', 'quantity', 'price')
    list_filter = ('order__restaurant',)
    autocomplete_fields = ['order', 'menu_item']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('order', 'user', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('user__telegram_id', 'order__id')

@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'points', 'transaction_type', 'description', 'created_at')
    list_filter = ('transaction_type',)
    search_fields = ('user__telegram_id', 'description')
    autocomplete_fields = ['user', 'order']
