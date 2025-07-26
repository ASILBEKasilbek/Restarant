from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import MenuItem, Table, Staff, Order, Category, UserProfile

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MenuItemForm(forms.ModelForm):
    new_images = forms.FileField(
        widget=MultipleFileInput(attrs={'multiple': True}),
        required=False,
        label=_("Yangi rasmlar")
    )


    class Meta:
        model = MenuItem
        fields = ['category', 'name', 'description', 'price', 'discount_price',
                  'is_available', 'dietary_info', 'preparation_time', 'stock_quantity']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'dietary_info': forms.TextInput(attrs={'placeholder': "Masalan, vegetarian, halal"}),
        }
        labels = {
            'category': _("Kategoriya"),
            'name': _("Nomi"),
            'description': _("Tavsif"),
            'price': _("Narx"),
            'discount_price': _("Chegirmali narx"),
            'is_available': _("Mavjud"),
            'dietary_info': _("Dieta ma'lumotlari"),
            'preparation_time': _("Tayyorlash vaqti (daqiqa)"),
            'stock_quantity': _("Zaxira miqdori"),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()

        # Save new images
        new_images = self.files.getlist('new_images')
        for img in new_images:
            image_instance = Image.objects.create(image=img)
            instance.images.add(image_instance)

        return instance

class RegistrationForm(UserCreationForm):
    """Foydalanuvchini ro'yxatdan o'tkazish formasi qo'shimcha profil maydonlari bilan."""

    phone_number = forms.CharField(
        max_length=15,
        label=_("Telefon raqami"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+998901234567'}),
        help_text=_("Masalan: +998901234567")
    )

    language = forms.ChoiceField(
        choices=getattr(UserProfile, 'LANGUAGE_CHOICES', [
            ('uz', _('O‘zbek')),
            ('ru', _('Rus')),
            ('en', _('Ingliz')),
        ]),
        label=_("Til"),
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='uz'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'phone_number', 'language']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Foydalanuvchi nomi'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'misol@email.com'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Parol'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Parolni tasdiqlang'}),
        }
        labels = {
            'username': _("Foydalanuvchi nomi"),
            'email': _("Elektron pochta"),
            'password1': _("Parol"),
            'password2': _("Parolni tasdiqlash"),
        }

    def clean_email(self):
        """Takroriy emaildan saqlanish."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("Bu elektron pochta allaqachon ro'yxatdan o'tgan."))
        return email

    def clean_phone_number(self):
        """Telefon raqami formati va yagona bo'lishini tekshirish."""
        phone_number = self.cleaned_data.get('phone_number')
        if not phone_number.startswith('+'):
            raise forms.ValidationError(_("Telefon raqami + bilan boshlanishi kerak."))
        if not phone_number[1:].isdigit():
            raise forms.ValidationError(_("Telefon raqami faqat raqamlardan iborat bo'lishi kerak."))
        if UserProfile.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError(_("Bu telefon raqami allaqachon ro'yxatdan o'tgan."))
        return phone_number

# class MenuItemForm(forms.ModelForm):
#     """Form to create or update menu items."""
#     images = forms.FileField(
#         widget=forms.ClearableFileInput(attrs={'multiple': True}),
#         required=False,
#         label=_("Rasmlar"),
#         help_text=_("Bir nechta rasm yuklashingiz mumkin")
#     )

#     class Meta:
#         model = MenuItem
#         fields = [
#             'name', 'category', 'description', 'price', 'discount_price',
#             'images', 'is_available', 'dietary_info', 'preparation_time', 'stock_quantity'
#         ]
#         widgets = {
#             'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
#             'name': forms.TextInput(attrs={'class': 'form-control'}),
#             'category': forms.Select(attrs={'class': 'form-control'}),
#             'price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
#             'discount_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
#             'dietary_info': forms.TextInput(attrs={'class': 'form-control'}),
#             'preparation_time': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
#             'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
#             'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
#         }
#         labels = {
#             'name': _("Element nomi"),
#             'category': _("Kategoriya"),
#             'description': _("Tavsif"),
#             'price': _("Narx"),
#             'discount_price': _("Chegirmali narx"),
#             'is_available': _("Mavjud"),
#             'dietary_info': _("Dieta ma'lumotlari"),
#             'preparation_time': _("Tayyorlash vaqti (daqiqa)"),
#             'stock_quantity': _("Zaxira miqdori"),
#         }

#     def __init__(self, *args, **kwargs):
#         restaurant = kwargs.pop('restaurant', None)
#         super().__init__(*args, **kwargs)
#         if restaurant:
#             self.fields['category'].queryset = Category.objects.filter(restaurant=restaurant)

class TableForm(forms.ModelForm):
    """Form to create or update restaurant tables."""
    class Meta:
        model = Table
        fields = ['table_number', 'capacity']
        widgets = {
            'table_number': forms.TextInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
        labels = {
            'table_number': _("Stol raqami"),
            'capacity': _("Sig'im (o'rindiqlar soni)"),
        }

    def clean_table_number(self):
        table_number = self.cleaned_data['table_number']
        restaurant = self.instance.restaurant if self.instance.pk else None
        if restaurant and Table.objects.filter(restaurant=restaurant, table_number=table_number).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_("Bu stol raqami allaqachon mavjud."))
        return table_number

class StaffForm(forms.ModelForm):
    """Form to add or update restaurant staff."""
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_("Foydalanuvchi")
    )

    class Meta:
        model = Staff
        fields = ['user', 'role']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'role': _("Rol"),
        }

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        restaurant = self.instance.restaurant if self.instance.pk else None
        if restaurant and user and Staff.objects.filter(user=user, restaurant=restaurant).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_("Bu foydalanuvchi allaqachon ushbu restoranda xodim sifatida ro'yxatdan o'tgan."))
        return cleaned_data

class OrderStatusForm(forms.ModelForm):
    """Form to update order status."""
    class Meta:
        model = Order
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'status': _("Holat"),
        }