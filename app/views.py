from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Prefetch
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Restaurant, Table, MenuItem, Order, OrderItem, Cart, CartItem, Staff, UserProfile, AdminDashboard
from .forms import MenuItemForm, OrderStatusForm, TableForm, StaffForm, RegistrationForm
from django.contrib.auth.models import User
from django.contrib.auth import login
import json
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .forms import RegistrationForm
from .models import UserProfile

# Helper function to send real-time notifications
def send_notification(group_name, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'send_notification',
            'message': message
        }
    )

# Home View
def home(request):
    """Display the homepage with a list of active restaurants."""
    restaurants = Restaurant.objects.filter(is_active=True).select_related('owner').prefetch_related('images')
    return render(request, 'restaurant/home.html', {'restaurants': restaurants})


def register(request):
    """Handle user registration and create UserProfile."""
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password1')
            user.set_password(password)
            user.save()

            # Create user profile
            UserProfile.objects.create(
                user=user,
                phone_number=form.cleaned_data.get('phone_number'),
                preferred_language=form.cleaned_data.get('language')
            )

            # ✅ Autentifikatsiya (backendni avtomatik aniqlaydi)
            user = authenticate(request, username=user.username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Ro'yxatdan o'tish muvaffaqiyatli! Xush kelibsiz!")
                return redirect('restaurant:home')
            else:
                messages.error(request, "Login muvaffaqiyatsiz. Iltimos, keyinroq urinib ko‘ring.")
    else:
        form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

# Owner Panel Views
@login_required
def owner_dashboard(request, slug):
    """Restaurant owner dashboard with statistics, recent orders, and staff."""
    restaurant = get_object_or_404(Restaurant, slug=slug, owner=request.user)
    statistics = restaurant.get_statistics()
    orders = restaurant.orders.select_related('table', 'user_profile', 'assigned_waiter').order_by('-created_at')[:10]
    staff = restaurant.staff.select_related('user').all()
    return render(request, 'restaurant/owner_dashboard.html', {
        'restaurant': restaurant,
        'statistics': statistics,
        'orders': orders,
        'staff': staff,
    })

@login_required
def manage_menu(request, slug):
    """Manage menu items for a restaurant (add/edit/delete)."""
    restaurant = get_object_or_404(Restaurant, slug=slug, owner=request.user)
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES, restaurant=restaurant)
        if form.is_valid():
            menu_item = form.save(commit=False)
            menu_item.restaurant = restaurant
            menu_item.save()
            messages.success(request, "Menyu elementi qo'shildi!")
            send_notification(
                f'restaurant_{restaurant.id}_waiters',
                {'message': f"Yangi menyu elementi: {menu_item.name} qo'shildi."}
            )
            return redirect('restaurant:manage_menu', slug=slug)
    else:
        form = MenuItemForm(restaurant=restaurant)
    menu_items = restaurant.menu_items.select_related('category').prefetch_related('images').all()
    return render(request, 'restaurant/manage_menu.html', {
        'restaurant': restaurant,
        'menu_items': menu_items,
        'form': form,
    })

@login_required
def delete_menu_item(request, slug, item_id):
    """Delete a menu item."""
    restaurant = get_object_or_404(Restaurant, slug=slug, owner=request.user)
    menu_item = get_object_or_404(MenuItem, id=item_id, restaurant=restaurant)
    menu_item.delete()
    messages.success(request, "Menyu elementi o'chirildi!")
    send_notification(
        f'restaurant_{restaurant.id}_waiters',
        {'message': f"Menyu elementi: {menu_item.name} o'chirildi."}
    )
    return redirect('restaurant:manage_menu', slug=slug)

@login_required
def manage_staff(request, slug):
    """Manage restaurant staff (add/edit/delete)."""
    restaurant = get_object_or_404(Restaurant, slug=slug, owner=request.user)
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            staff = form.save(commit=False)
            staff.restaurant = restaurant
            staff.save()
            messages.success(request, "Xodim qo'shildi!")
            return redirect('restaurant:manage_staff', slug=slug)
    else:
        form = StaffForm()
    staff = restaurant.staff.select_related('user').all()
    return render(request, 'restaurant/manage_staff.html', {
        'restaurant': restaurant,
        'staff': staff,
        'form': form,
    })

@login_required
def manage_tables(request, slug):
    """Manage restaurant tables (add/edit/delete)."""
    restaurant = get_object_or_404(Restaurant, slug=slug, owner=request.user)
    if request.method == 'POST':
        form = TableForm(request.POST)
        if form.is_valid():
            table = form.save(commit=False)
            table.restaurant = restaurant
            table.save()
            messages.success(request, "Stol qo'shildi!")
            return redirect('restaurant:manage_tables', slug=slug)
    else:
        form = TableForm()
    tables = restaurant.tables.all()
    return render(request, 'restaurant/manage_tables.html', {
        'restaurant': restaurant,
        'tables': tables,
        'form': form,
    })

# Waiter Panel Views
@login_required
def waiter_dashboard(request, slug):
    """Waiter dashboard to view and manage orders and inventory."""
    restaurant = get_object_or_404(Restaurant, slug=slug)
    staff = get_object_or_404(Staff, user=request.user, restaurant=restaurant, role='waiter')
    orders = restaurant.orders.filter(
        status__in=['pending', 'accepted', 'preparing']
    ).select_related('table', 'user_profile', 'assigned_waiter').prefetch_related('items__menu_item')
    menu_items = restaurant.menu_items.filter(is_available=True).select_related('category').prefetch_related('images')
    return render(request, 'restaurant/waiter_dashboard.html', {
        'restaurant': restaurant,
        'orders': orders,
        'menu_items': menu_items,
        'staff': staff,
    })

@login_required
@require_POST
@csrf_exempt
def update_order_status(request, slug, order_id):
    """Update the status of an order and notify relevant parties."""
    restaurant = get_object_or_404(Restaurant, slug=slug)
    staff = get_object_or_404(Staff, user=request.user, restaurant=restaurant, role='waiter')
    order = get_object_or_404(Order, id=order_id, restaurant=restaurant)
    form = OrderStatusForm(request.POST, instance=order)
    if form.is_valid():
        order.update_status(form.cleaned_data['status'], waiter=staff)
        send_notification(
            f'restaurant_{restaurant.id}_customers',
            {'message': f"Buyurtma #{order.id} holati: {order.get_status_display()}"}
        )
        send_notification(
            f'restaurant_{restaurant.id}_owner',
            {'message': f"Buyurtma #{order.id} holati {staff.user.username} tomonidan yangilandi: {order.get_status_display()}"}
        )
        return JsonResponse({'status': 'success', 'new_status': order.get_status_display()})
    return HttpResponseBadRequest(json.dumps(form.errors))

@login_required
@require_POST
@csrf_exempt
def update_stock(request, slug, item_id):
    """Update menu item stock and log the transaction."""
    restaurant = get_object_or_404(Restaurant, slug=slug)
    staff = get_object_or_404(Staff, user=request.user, restaurant=restaurant, role='waiter')
    menu_item = get_object_or_404(MenuItem, id=item_id, restaurant=restaurant)
    try:
        quantity = int(request.POST.get('quantity', 0))
        if quantity != 0:
            menu_item.stock_quantity += quantity
            menu_item.is_available = menu_item.stock_quantity > 0
            menu_item.save()
            InventoryTransaction.objects.create(
                menu_item=menu_item,
                quantity=quantity,
                description=f"Xodim {request.user.username} tomonidan zaxira yangilandi"
            )
            send_notification(
                f'restaurant_{restaurant.id}_owner',
                {'message': f"{menu_item.name} zaxirasi {quantity} dona o'zgardi."}
            )
            return JsonResponse({'status': 'success', 'new_quantity': menu_item.stock_quantity})
        return HttpResponseBadRequest("Miqdor 0 bo'lmasligi kerak")
    except ValueError:
        return HttpResponseBadRequest("Noto'g'ri miqdor kiritildi")

# Customer Panel Views
def table_menu(request, qr_code):
    table = get_object_or_404(Table, qr_code=qr_code)
    restaurant = table.restaurant
    categories = restaurant.categories.prefetch_related('menu_items__images').all()
    
    cart = None

    if request.user.is_authenticated:
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if user_profile:
            cart, _ = Cart.objects.get_or_create(
                user_profile=user_profile,
                restaurant=restaurant,
                table=table
            )
    print(qr_code)
    return render(request, 'restaurant/customer_menu.html', {
        'restaurant': restaurant,
        'table': table,
        'categories': categories,
        'cart': cart,
        'qr_code': qr_code,
    })

@require_POST
@csrf_exempt
def add_to_cart(request, qr_code):
    """Add items to the cart."""
    table = get_object_or_404(Table, qr_code=qr_code)
    restaurant = table.restaurant
    menu_item_id = request.POST.get('menu_item_id')
    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity < 1:
            return HttpResponseBadRequest("Miqdor 1 dan kam bo'lmasligi kerak")
        menu_item = get_object_or_404(MenuItem, id=menu_item_id, restaurant=restaurant, is_available=True)
        
        user_profile = None
        if request.user.is_authenticated:
            user_profile = get_object_or_404(UserProfile, user=request.user)
        
        cart, created = Cart.objects.get_or_create(
            user_profile=user_profile,
            restaurant=restaurant,
            table=table
        )
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            menu_item=menu_item,
            defaults={'quantity': quantity}
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        if menu_item.reduce_stock(quantity):
            send_notification(
                f'restaurant_{restaurant.id}_waiters',
                {'message': f"Yangi savat elementi: {menu_item.name} ({quantity} dona)"}
            )
            return JsonResponse({
                'status': 'success',
                'cart_total': cart.total_price,
                'item_name': menu_item.name,
                'quantity': cart_item.quantity
            })
        return HttpResponseBadRequest("Zaxira yetarli emas")
    except ValueError:
        return HttpResponseBadRequest("Noto'g'ri miqdor kiritildi")

@require_POST
@csrf_exempt
def place_order(request, qr_code):
    """Place an order from the cart."""
    table = get_object_or_404(Table, qr_code=qr_code)
    restaurant = table.restaurant
    user_profile = get_object_or_404(UserProfile, user=request.user) if request.user.is_authenticated else None
    cart = get_object_or_404(Cart, restaurant=restaurant, table=table, user_profile=user_profile)
    
    if not cart.items.exists():
        return HttpResponseBadRequest("Savat bo'sh")
    
    order = Order.objects.create(
        restaurant=restaurant,
        user_profile=user_profile,
        table=table,
        total_price=cart.total_price,
        status='pending'
    )
    
    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            menu_item=item.menu_item,
            quantity=item.quantity,
            price=item.menu_item.effective_price
        )
    
    order.calculate_estimated_delivery()
    if user_profile:
        user_profile.award_loyalty_points(order)
    
    cart.items.all().delete()
    send_notification(
        f'restaurant_{restaurant.id}_waiters',
        {'message': f"Yangi buyurtma #{order.id} qabul qilindi"}
    )
    send_notification(
        f'restaurant_{restaurant.id}_owner',
        {'message': f"Yangi buyurtma #{order.id} qabul qilindi"}
    )
    return JsonResponse({'status': 'success', 'order_id': order.id})

@login_required
def order_history(request):
    """Display the order history for a customer."""
    user_profile = get_object_or_404(UserProfile, user=request.user)
    orders = user_profile.orders.select_related('restaurant', 'table', 'assigned_waiter').prefetch_related('items__menu_item').order_by('-created_at')
    return render(request, 'restaurant/order_history.html', {'orders': orders})

# Admin Panel Views
@login_required
def admin_dashboard(request):
    """Admin dashboard with system-wide statistics."""
    if not request.user.is_superuser:
        messages.error(request, "Sizda admin paneliga kirish huquqi yo'q.")
        return redirect('restaurant:home')
    
    dashboard = AdminDashboard.objects.first()
    if dashboard:
        dashboard.update_statistics()
    else:
        dashboard = AdminDashboard.objects.create()
        dashboard.update_statistics()
    
    return render(request, 'restaurant/admin_dashboard.html', {
        'dashboard': dashboard,
    })

@login_required
def admin_manage_restaurants(request):
    """Admin view to manage all restaurants."""
    if not request.user.is_superuser:
        return redirect('restaurant:home')
    
    restaurants = Restaurant.objects.select_related('owner').prefetch_related('images').all()
    return render(request, 'restaurant/admin_manage_restaurants.html', {
        'restaurants': restaurants,
    })