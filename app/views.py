from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.db.models import Sum, Count, Avg
from django.core.cache import cache
from django.core.exceptions import ValidationError
from .models import Restaurant, Category, MenuItem, UserProfile, Order, OrderItem, Review, LoyaltyTransaction, Cart, CartItem
from .forms import OrderForm, OrderItemFormSet, DeliveryOrderForm, ReviewForm
from django.urls import reverse
from qr_code.qrcode.utils import QRCodeOptions
import json
import logging
from django.db import transaction
from django.core.paginator import Paginator

# Set up logging
logger = logging.getLogger(__name__)

# Homepage
def index(request):
    # Get active restaurants
    restaurants = Restaurant.objects.filter(is_active=True).order_by('name')[:6]
    
    # Get popular items across all restaurants
    cache_key = 'popular_items_global'
    popular_items = cache.get(cache_key)
    if not popular_items:
        popular_items = MenuItem.objects.filter(
            is_available=True
        ).annotate(
            order_count=Sum('order_items__quantity')
        ).order_by('-order_count')[:5]
        cache.set(cache_key, popular_items, 3600)  # 1-hour cache

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        restaurants = restaurants.filter(name__icontains=search_query)
        popular_items = popular_items.filter(name__icontains=search_query)

    context = {
        'restaurants': restaurants,
        'popular_items': popular_items,
        'search_query': search_query,
    }
    return render(request, 'restaurant/index.html', context)

# QR kodli stol menyusini ko'rsatish
def table_menu(request, restaurant_slug, table_number):
    restaurant = get_object_or_404(Restaurant, slug=restaurant_slug, is_active=True)
    categories = Category.objects.filter(restaurant=restaurant)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    menu_items = MenuItem.objects.filter(
        restaurant=restaurant, 
        is_available=True
    )
    if search_query:
        menu_items = menu_items.filter(name__icontains=search_query)

    # Pagination
    paginator = Paginator(menu_items, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # QR-kod URL
    qr_code_url = request.build_absolute_uri(
        reverse('table_menu', args=[restaurant_slug, table_number])
    )
    qr_options = QRCodeOptions(size='M', border=4, error_correction='H')

    context = {
        'restaurant': restaurant,
        'categories': categories,
        'menu_items': page_obj,
        'table_number': table_number,
        'qr_code_url': qr_code_url,
        'qr_options': qr_options,
        'search_query': search_query,
    }
    return render(request, 'restaurant/table_menu.html', context)

# Savatga qo'shish
@require_POST
@login_required
def add_to_cart(request, restaurant_slug):
    try:
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug, is_active=True)
        user = UserProfile.objects.get(telegram_id=request.user.username)
        menu_item_id = request.POST.get('menu_item_id')
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity < 1:
            return JsonResponse({'error': _("Noto'g'ri miqdor")}, status=400)

        menu_item = get_object_or_404(MenuItem, id=menu_item_id, restaurant=restaurant)
        
        cart, created = Cart.objects.get_or_create(user=user, restaurant=restaurant)
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            menu_item=menu_item,
            defaults={'quantity': quantity}
        )
        
        if not item_created:
            cart_item.quantity += quantity
            cart_item.save()

        return JsonResponse({
            'message': _("{item} savatga qo'shildi").format(item=menu_item.name),
            'cart_count': cart.items.count()
        })
    except Exception as e:
        logger.error(f"Error adding to cart: {str(e)}")
        return JsonResponse({'error': _("Xatolik yuz berdi")}, status=500)

# Buyurtma yaratish
@transaction.atomic
def create_order(request, restaurant_slug):
    restaurant = get_object_or_404(Restaurant, slug=restaurant_slug, is_active=True)
    table_number = request.GET.get('table_number', '')
    user = UserProfile.objects.get(telegram_id=request.user.username) if request.user.is_authenticated else None

    if request.method == 'POST':
        form = OrderForm(request.POST, restaurant=restaurant)
        formset = OrderItemFormSet(request.POST, instance=Order(restaurant=restaurant))
        
        if form.is_valid() and formset.is_valid():
            try:
                order = form.save(commit=False)
                order.restaurant = restaurant
                order.user = user
                order.table_number = table_number
                order.save()
                formset.instance = order
                formset.save()

                # Umumiy narxni hisoblash
                total_price = sum(item.quantity * item.price for item in order.items.all())
                order.total_price = total_price

                # Sadoqat ballarini qo'shish
                if user:
                    points = int(total_price / 10)
                    LoyaltyTransaction.objects.create(
                        user=user,
                        order=order,
                        points=points,
                        transaction_type='earned',
                        description=_("Points earned for order #{}").format(order.id)
                    )
                    user.loyalty_points += points
                    user.save()

                # Savatni tozalash
                if user:
                    Cart.objects.filter(user=user, restaurant=restaurant).delete()

                order.save()
                messages.success(request, _("Buyurtmangiz muvaffaqiyatli qabul qilindi!"))
                return redirect('order_status', order_id=order.id)
                
            except Exception as e:
                logger.error(f"Error creating order: {str(e)}")
                messages.error(request, _("Buyurtma yaratishda xatolik yuz berdi"))
        else:
            messages.error(request, _("Ma'lumotlarni kiritishda xatolik"))
    else:
        form = OrderForm(restaurant=restaurant)
        formset = OrderItemFormSet(instance=Order(restaurant=restaurant))

    context = {
        'restaurant': restaurant,
        'form': form,
        'formset': formset,
        'table_number': table_number,
    }
    return render(request, 'restaurant/create_order.html', context)

# Yetkazib berish buyurtmasi
@transaction.atomic
def create_delivery_order(request):
    if request.method == 'POST':
        form = DeliveryOrderForm(request.POST)
        if form.is_valid():
            try:
                order = form.save(commit=False)
                user = UserProfile.objects.get(telegram_id=request.user.username) if request.user.is_authenticated else None
                order.user = user
                order.save()

                items_data = json.loads(request.POST.get('items_data', '[]'))
                total_price = 0
                for item_data in items_data:
                    menu_item = MenuItem.objects.get(id=item_data['menu_item_id'])
                    quantity = item_data['quantity']
                    price = menu_item.price
                    OrderItem.objects.create(
                        order=order,
                        menu_item=menu_item,
                        quantity=quantity,
                        price=price
                    )
                    total_price += quantity * price

                order.total_price = total_price
                order.save()

                if user:
                    points = int(total_price / 10)
                    LoyaltyTransaction.objects.create(
                        user=user,
                        order=order,
                        points=points,
                        transaction_type='earned',
                        description=_("Points earned for delivery order #{}").format(order.id)
                    )
                    user.loyalty_points += points
                    user.save()

                    # Savatni tozalash
                    Cart.objects.filter(user=user).delete()

                messages.success(request, _("Yetkazib berish buyurtmangiz qabul qilindi!"))
                return redirect('order_status', order_id=order.id)
            except Exception as e:
                logger.error(f"Error creating delivery order: {str(e)}")
                messages.error(request, _("Buyurtma yaratishda xatolik yuz berdi"))
        else:
            messages.error(request, _("Ma'lumotlarni kiritishda xatolik"))
    else:
        form = DeliveryOrderForm()

    restaurants = Restaurant.objects.filter(is_active=True)
    context = {
        'form': form,
        'restaurants': restaurants,
    }
    return render(request, 'restaurant/delivery_order.html', context)

# Buyurtma holatini ko'rsatish
def order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    context = {
        'order': order,
        'items': order.items.all(),
        'estimated_time': order.created_at + timezone.timedelta(minutes=30),
        'can_cancel': order.status in ['pending', 'accepted'],
    }
    return render(request, 'restaurant/order_status.html', context)

# Buyurtmani bekor qilish
@login_required
@require_POST
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    user = UserProfile.objects.get(telegram_id=request.user.username)
    
    if order.user != user or order.status not in ['pending', 'accepted']:
        return JsonResponse({'error': _("Buyurtmani bekor qilish mumkin emas")}, status=400)
    
    try:
        order.status = 'cancelled'
        order.save()
        
        # Sadoqat ballarini qaytarish
        if order.user:
            points = int(order.total_price / 10)
            LoyaltyTransaction.objects.create(
                user=order.user,
                order=order,
                points=-points,
                transaction_type='refunded',
                description=_("Points refunded for cancelled order #{}").format(order.id)
            )
            order.user.loyalty_points -= points
            order.user.save()
            
        return JsonResponse({'message': _("Buyurtma bekor qilindi")})
    except Exception as e:
        logger.error(f"Error cancelling order: {str(e)}")
        return JsonResponse({'error': _("Xatolik yuz berdi")}, status=500)

# Buyurtma holatini yangilash
@require_POST
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')
    
    if new_status in dict(Order.STATUS_CHOICES).keys():
        try:
            order.status = new_status
            order.save()
            cache.delete(f'order_status_{order_id}')
            return JsonResponse({'status': new_status, 'message': _("Status yangilandi")})
        except Exception as e:
            logger.error(f"Error updating order status: {str(e)}")
            return JsonResponse({'error': _("Xatolik yuz berdi")}, status=500)
    return JsonResponse({'error': _("Noto'g'ri status")}, status=400)

# Sharh qoldirish
@login_required
def submit_review(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    user = UserProfile.objects.get(telegram_id=request.user.username)
    
    if order.user != user:
        messages.error(request, _("Faqat o'zingizning buyurtmalaringizga sharh qoldirishingiz mumkin"))
        return redirect('order_status', order_id=order.id)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            try:
                review = form.save(commit=False)
                review.order = order
                review.user = user
                review.save()
                messages.success(request, _("Sharhingiz qabul qilindi!"))
                return redirect('order_status', order_id=order.id)
            except Exception as e:
                logger.error(f"Error submitting review: {str(e)}")
                messages.error(request, _("Sharh qoldirishda xatolik yuz berdi"))
        else:
            messages.error(request, _("Ma'lumotlarni kiritishda xatolik"))
    else:
        form = ReviewForm()

    return render(request, 'restaurant/submit_review.html', {'order': order, 'form': form})

# Restoran reytinglari
def restaurant_ratings(request, restaurant_slug):
    restaurant = get_object_or_404(Restaurant, slug=restaurant_slug, is_active=True)
    reviews = Review.objects.filter(order__restaurant=restaurant)
    
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    rating_counts = reviews.aggregate(
        five=Count('rating', filter={'rating': 5}),
        four=Count('rating', filter={'rating': 4}),
        three=Count('rating', filter={'rating': 3}),
        two=Count('rating', filter={'rating': 2}),
        one=Count('rating', filter={'rating': 1}),
    )

    context = {
        'restaurant': restaurant,
        'reviews': reviews[:5],
        'avg_rating': round(avg_rating, 1),
        'rating_counts': rating_counts,
        'total_reviews': reviews.count(),
    }
    return render(request, 'restaurant/ratings.html', context)

# Sadoqat ballarini sarflash
@login_required
@transaction.atomic
def spend_loyalty_points(request):
    user = UserProfile.objects.get(telegram_id=request.user.username)
    
    if request.method == 'POST':
        points = int(request.POST.get('points', 0))
        if points > 0 and points <= user.loyalty_points:
            try:
                user.loyalty_points -= points
                user.save()
                LoyaltyTransaction.objects.create(
                    user=user,
                    points=points,
                    transaction_type='spent',
                    description=_("Points spent by user")
                )
                messages.success(request, _("{points} ball sarflandi").format(points=points))
            except Exception as e:
                logger.error(f"Error spending loyalty points: {str(e)}")
                messages.error(request, _("Ballarni sarflashda xatolik yuz berdi"))
        else:
            messages.error(request, _("Noto'g'ri ball miqdori yoki yetarli ball yo'q"))
        return redirect('user_profile')
    
    return render(request, 'restaurant/spend_points.html', {'user': user})

# Foydalanuvchi profilini ko'rsatish
@login_required
def user_profile(request):
    user = UserProfile.objects.get(telegram_id=request.user.username)
    orders = Order.objects.filter(user=user).order_by('-created_at')[:5]
    transactions = LoyaltyTransaction.objects.filter(user=user).order_by('-created_at')[:5]
    
    # Statistikalar
    total_orders = Order.objects.filter(user=user).count()
    total_spent = Order.objects.filter(user=user).aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    context = {
        'user': user,
        'orders': orders,
        'transactions': transactions,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'avg_order_value': total_spent / total_orders if total_orders > 0 else 0,
    }
    return render(request, 'restaurant/user_profile.html', context)

# Eng mashhur taomlarni ko'rsatish
def popular_items(request, restaurant_slug):
    restaurant = get_object_or_404(Restaurant, slug=restaurant_slug, is_active=True)
    cache_key = f'popular_items_{restaurant_slug}'
    
    popular_items = cache.get(cache_key)
    if not popular_items:
        popular_items = MenuItem.objects.filter(
            restaurant=restaurant, 
            is_available=True
        ).annotate(
            order_count=Sum('order_items__quantity')
        ).order_by('-order_count')[:5]
        cache.set(cache_key, popular_items, 3600)  # 1 soatlik cache

    context = {
        'restaurant': restaurant,
        'popular_items': popular_items,
    }
    return render(request, 'restaurant/popular_items.html', context)

# API endpoint for menu items
def menu_items_api(request, restaurant_slug):
    restaurant = get_object_or_404(Restaurant, slug=restaurant_slug, is_active=True)
    menu_items = MenuItem.objects.filter(restaurant=restaurant, is_available=True).values(
        'id', 'name', 'price', 'description', 'category__name'
    )
    return JsonResponse({'menu_items': list(menu_items)})

def logout_view(request):
    # Handle logout logic here
    return redirect('index')
def register_view(request):
    if request.method == 'POST':
        # Handle registration logic here
        pass
    return render(request, 'restaurant/register.html')