from django.shortcuts import render
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.shortcuts import redirect,render
# Create your views here.
def index(request):
    return render(request, 'main.html')

def register(request):
    if request.method=="POST":
        form= UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request,user)
            return redirect('index')
    else:
        form=UserCreationForm()
    return render(request,'register.html',{'form':form})



from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponseRedirect
from .models import Restaurant, Category, MenuItem, Order, OrderItem, UserProfile
from .forms import OrderForm
from django.db import transaction
from django.urls import reverse
import telegram
import json

# Bot token (settings.py dan olinadi yoki .env faylida saqlanadi)
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # .env faylida saqlang
bot = telegram.Bot(token=BOT_TOKEN)

class RestaurantMenuView(View):
    template_name = 'restaurant/menu.html'

    def get(self, request, slug):
        restaurant = get_object_or_404(Restaurant, slug=slug, is_active=True)
        categories = Category.objects.filter(restaurant=restaurant)
        menu_items = MenuItem.objects.filter(restaurant=restaurant, is_available=True)
        context = {
            'restaurant': restaurant,
            'categories': categories,
            'menu_items': menu_items,
        }
        return render(request, self.template_name, context)

class OrderCreateView(View):
    template_name = 'restaurant/order.html'
    form_class = OrderForm

    def get(self, request, slug):
        restaurant = get_object_or_404(Restaurant, slug=slug, is_active=True)
        form = self.form_class()
        context = {
            'restaurant': restaurant,
            'form': form,
        }
        return render(request, self.template_name, context)

    def post(self, request, slug):
        restaurant = get_object_or_404(Restaurant, slug=slug, is_active=True)
        form = self.form_class(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user, created = UserProfile.objects.get_or_create(
                    telegram_id=form.cleaned_data['telegram_id'],
                    defaults={'phone_number': form.cleaned_data.get('phone_number', '')}
                )
                order = Order.objects.create(
                    restaurant=restaurant,
                    user=user,
                    table_number=form.cleaned_data['table_number'],
                    delivery_address=form.cleaned_data.get('delivery_address', ''),
                    payment_method=form.cleaned_data['payment_method'],
                    total_price=0  # Keyin hisoblanadi
                )
                total_price = 0
                cart = json.loads(form.cleaned_data['cart'])
                for item_id, quantity in cart.items():
                    menu_item = get_object_or_404(MenuItem, id=item_id, restaurant=restaurant, is_available=True)
                    item_price = menu_item.price * quantity
                    OrderItem.objects.create(
                        order=order,
                        menu_item=menu_item,
                        quantity=quantity,
                        price=item_price
                    )
                    total_price += item_price
                order.total_price = total_price
                order.save()

                # Telegram bot orqali bildirishnoma yuborish
                try:
                    bot.send_message(
                        chat_id=user.telegram_id,
                        text=_("Buyurtmangiz qabul qilindi! Order #%(order_id)s - Summa: %(total_price)s so‘m") % {
                            'order_id': order.id,
                            'total_price': total_price
                        }
                    )
                except telegram.error.TelegramError:
                    messages.warning(request, _("Telegram xabarni yuborishda xatolik yuz berdi."))

                messages.success(request, _("Buyurtmangiz muvaffaqiyatli qabul qilindi!"))
                return redirect(reverse('order_status', args=[order.id]))
        return render(request, self.template_name, {'restaurant': restaurant, 'form': form})

class OrderStatusView(View):
    template_name = 'restaurant/order_status.html'

    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        context = {
            'order': order,
            'items': order.items.all(),
        }
        return render(request, self.template_name, context)

class TelegramWebhookView(View):
    def post(self, request):
        update = telegram.Update.de_json(json.loads(request.body), bot)
        chat_id = update.message.chat_id
        text = update.message.text

        # Botga kirishda restoran menyusini yuborish
        if text == '/start':
            restaurants = Restaurant.objects.filter(is_active=True)
            reply_text = _("Quyidagi restoranlarni tanlang:\n")
            for restaurant in restaurants:
                reply_text += f"{restaurant.name}: /menu_{restaurant.slug}\n"
            bot.send_message(chat_id=chat_id, text=reply_text)
        elif text.startswith('/menu_'):
            slug = text.replace('/menu_', '')
            restaurant = get_object_or_404(Restaurant, slug=slug, is_active=True)
            menu_items = MenuItem.objects.filter(restaurant=restaurant, is_available=True)
            reply_text = f"{restaurant.name} menyusi:\n"
            for item in menu_items:
                reply_text += f"{item.name} - {item.price} so‘m\n"
            reply_text += _("\nBuyurtma berish uchun veb-saytga o‘ting: ") + request.build_absolute_uri(reverse('restaurant_menu', args=[slug]))
            bot.send_message(chat_id=chat_id, text=reply_text)
        return HttpResponseRedirect('/')
