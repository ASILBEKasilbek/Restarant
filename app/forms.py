from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Order

class OrderForm(forms.Form):
    telegram_id = forms.CharField(
        max_length=50,
        label=_("Telegram ID"),
        help_text=_("Sizning Telegram ID raqamingiz")
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        label=_("Telefon raqami"),
        help_text=_("Ixtiyoriy: Yetkazib berish uchun telefon raqami")
    )
    table_number = forms.CharField(
        max_length=10,
        required=False,
        label=_("Stol raqami"),
        help_text=_("Restorandagi stol raqami (agar mavjud bo‘lsa)")
    )
    delivery_address = forms.CharField(
        widget=forms.Textarea,
        required=False,
        label=_("Yetkazib berish manzili"),
        help_text=_("Yetkazib berish uchun manzil (agar kerak bo‘lsa)")
    )
    payment_method = forms.ChoiceField(
        choices=[
            ('cash', _('Naqd')),
            ('card', _('Karta')),
            ('online', _('Onlayn to‘lov'))
        ],
        label=_("To‘lov usuli")
    )
    cart = forms.CharField(
        widget=forms.HiddenInput,
        label=_("Savat"),
        help_text=_("Tanlangan taomlar JSON formatida")
    )

    def clean_cart(self):
        cart = self.cleaned_data['cart']
        try:
            json.loads(cart)
        except ValueError:
            raise forms.ValidationError(_("Savat ma'lumotlari noto‘g‘ri formatda."))
        return cart
