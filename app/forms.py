from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _
from .models import Order, OrderItem, Restaurant, MenuItem, UserProfile, Cart, CartItem,Review

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['table_number', 'payment_method', 'notes', 'delivery_address']
        widgets = {
            'table_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _("Table number (if applicable)")
            }),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _("Any special requests?")
            }),
            'delivery_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _("Enter delivery address")
            }),
        }
        labels = {
            'table_number': _("Table Number"),
            'payment_method': _("Payment Method"),
            'notes': _("Additional Notes"),
            'delivery_address': _("Delivery Address"),
        }

    def __init__(self, *args, restaurant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.restaurant = restaurant
        self.user = user

        # Set default delivery address for authenticated users
        if user and user.default_delivery_address:
            self.fields['delivery_address'].initial = user.default_delivery_address

        # Make delivery_address required only for delivery orders
        if not self.initial.get('table_number'):
            self.fields['delivery_address'].required = True
        else:
            self.fields['delivery_address'].required = False

    def clean(self):
        cleaned_data = super().clean()
        table_number = cleaned_data.get('table_number')
        delivery_address = cleaned_data.get('delivery_address')

        # Validate that either table_number or delivery_address is provided
        if not table_number and not delivery_address:
            raise forms.ValidationError(
                _("Either table number or delivery address must be provided.")
            )
        
        return cleaned_data

class OrderItemForm(forms.ModelForm):
    menu_item = forms.ModelChoiceField(
        queryset=MenuItem.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_("Menu Item")
    )

    class Meta:
        model = OrderItem
        fields = ['menu_item', 'quantity']
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'value': 1
            }),
        }
        labels = {
            'quantity': _("Quantity"),
        }

    def __init__(self, *args, **kwargs):
        restaurant = kwargs.pop('restaurant', None)
        super().__init__(*args, **kwargs)
        if restaurant:
            self.fields['menu_item'].queryset = MenuItem.objects.filter(
                restaurant=restaurant,
                is_available=True
            )

    def clean(self):
        cleaned_data = super().clean()
        menu_item = cleaned_data.get('menu_item')
        quantity = cleaned_data.get('quantity')

        if menu_item and not menu_item.is_available:
            raise forms.ValidationError(
                _("{item} is not available.").format(item=menu_item.name)
            )

        if quantity and quantity < 1:
            raise forms.ValidationError(
                _("Quantity must be at least 1.")
            )

        return cleaned_data

OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)

class DeliveryOrderForm(forms.ModelForm):
    restaurant = forms.ModelChoiceField(
        queryset=Restaurant.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_("Restaurant")
    )

    class Meta:
        model = Order
        fields = ['restaurant', 'delivery_address', 'payment_method', 'notes']
        widgets = {
            'delivery_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _("Enter delivery address")
            }),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _("Any special requests?")
            }),
        }
        labels = {
            'restaurant': _("Restaurant"),
            'delivery_address': _("Delivery Address"),
            'payment_method': _("Payment Method"),
            'notes': _("Additional Notes"),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Set default delivery address for authenticated users
        if user and user.default_delivery_address:
            self.fields['delivery_address'].initial = user.default_delivery_address

        self.fields['delivery_address'].required = True

    def clean(self):
        cleaned_data = super().clean()
        restaurant = cleaned_data.get('restaurant')

        if restaurant and not restaurant.is_active:
            raise forms.ValidationError(
                _("{restaurant} is currently not active.").format(restaurant=restaurant.name)
            )

        return cleaned_data

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 5,
                'value': 5
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _("Your feedback")
            }),
        }
        labels = {
            'rating': _("Rating"),
            'comment': _("Comment"),
        }

    def clean_rating(self):
        rating = self.cleaned_data['rating']
        if not 1 <= rating <= 5:
            raise forms.ValidationError(
                _("Rating must be between 1 and 5.")
            )
        return rating