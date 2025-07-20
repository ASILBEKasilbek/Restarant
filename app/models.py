from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

class BaseModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Yaratilgan sana"),
        help_text=_("Obyekt yaratilgan vaqt")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Yangilangan sana"),
        help_text=_("Obyekt oxirgi marta yangilangan vaqt")
    )

    class Meta:
        abstract = True  # Bu sinf faqat meros qilib olish uchun

class Restaurant(BaseModel):
    name = models.CharField(max_length=100, verbose_name=_("Restoran nomi"))
    slug = models.SlugField(max_length=100, unique=True, verbose_name=_("Slug"))
    address = models.TextField(verbose_name=_("Manzil"))
    phone_number = models.CharField(max_length=20, blank=True, verbose_name=_("Telefon raqami"))
    is_active = models.BooleanField(default=True, verbose_name=_("Faol"))

    class Meta:
        verbose_name = _("Restoran")
        verbose_name_plural = _("Restoranlar")
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Category(BaseModel):
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="categories",
        verbose_name=_("Restoran")
    )
    name = models.CharField(max_length=50, verbose_name=_("Kategoriya nomi"))
    description = models.TextField(blank=True, verbose_name=_("Tavsif"))

    class Meta:
        verbose_name = _("Kategoriya")
        verbose_name_plural = _("Kategoriyalar")
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['restaurant', 'name'],
                name='unique_category_per_restaurant'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"

class MenuItem(BaseModel):
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="menu_items",
        verbose_name=_("Restoran")
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="menu_items",
        verbose_name=_("Kategoriya")
    )
    name = models.CharField(max_length=100, verbose_name=_("Taom nomi"))
    description = models.TextField(blank=True, verbose_name=_("Tavsif"))
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("Narx")
    )
    image = models.ImageField(
        upload_to="menu_images/%Y/%m/%d/",
        blank=True,
        null=True,
        verbose_name=_("Rasm")
    )
    is_available = models.BooleanField(default=True, verbose_name=_("Mavjud"))
    dietary_info = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Diyetik ma'lumot"),
        help_text=_("Masalan, vegetarian, halol, glyutensiz")
    )

    class Meta:
        verbose_name = _("Taom")
        verbose_name_plural = _("Taomlar")
        ordering = ['name']
        indexes = [
            models.Index(fields=['restaurant', 'is_available']),
        ]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"

class UserProfile(BaseModel):
    telegram_id = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Telegram ID")
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Telefon raqami")
    )
    loyalty_points = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Sadoqat ballari")
    )
    preferred_language = models.CharField(
        max_length=10,
        choices=[('uz', 'O‘zbek'), ('ru', 'Русский'), ('en', 'English')],
        default='uz',
        verbose_name=_("Tanlangan til")
    )

    class Meta:
        verbose_name = _("Foydalanuvchi profili")
        verbose_name_plural = _("Foydalanuvchi profillari")
        ordering = ['telegram_id']

    def __str__(self):
        return f"User {self.telegram_id}"

class Order(BaseModel):
    STATUS_CHOICES = [
        ('pending', _('Kutilmoqda')),
        ('preparing', _('Tayyorlanmoqda')),
        ('delivered', _('Yetkazib berildi')),
        ('cancelled', _('Bekor qilingan')),
    ]

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name=_("Restoran")
    )
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("Foydalanuvchi")
    )
    table_number = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_("Stol raqami")
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_("Status")
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("Umumiy narx")
    )
    delivery_address = models.TextField(
        blank=True,
        verbose_name=_("Yetkazib berish manzili")
    )
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('cash', _('Naqd')),
            ('card', _('Karta')),
            ('online', _('Onlayn to‘lov'))
        ],
        verbose_name=_("To‘lov usuli")
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Eslatmalar"),
        help_text=_("Mijozning qo‘shimcha talablari")
    )

    class Meta:
        verbose_name = _("Buyurtma")
        verbose_name_plural = _("Buyurtmalar")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['restaurant', 'status']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"Order #{self.id} - {self.restaurant.name}"

class OrderItem(BaseModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Buyurtma")
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_items",
        verbose_name=_("Taom")
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("Miqdor")
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("Narx")
    )

    class Meta:
        verbose_name = _("Buyurtma elementi")
        verbose_name_plural = _("Buyurtma elementlari")
        indexes = [
            models.Index(fields=['order', 'menu_item']),
        ]

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name if self.menu_item else 'Deleted Item'} (Order #{self.order.id})"

class Review(BaseModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("Buyurtma")
    )
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("Foydalanuvchi")
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_("Baholash")
    )
    comment = models.TextField(
        blank=True,
        verbose_name=_("Izoh")
    )

    class Meta:
        verbose_name = _("Sharh")
        verbose_name_plural = _("Sharhlar")
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'user'],
                name='unique_review_per_user_order'
            )
        ]

    def __str__(self):
        return f"Review for Order #{self.order.id} - {self.rating}/5"

class LoyaltyTransaction(BaseModel):
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="loyalty_transactions",
        verbose_name=_("Foydalanuvchi")
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Buyurtma")
    )
    points = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name=_("Ballar")
    )
    description = models.CharField(
        max_length=200,
        verbose_name=_("Tavsif")
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=[('earned', _('Qozonilgan')), ('spent', _('Sarflangan'))],
        verbose_name=_("Tranzaksiya turi")
    )

    class Meta:
        verbose_name = _("Sadoqat tranzaksiyasi")
        verbose_name_plural = _("Sadoqat tranzaksiyalari")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.points} points ({self.transaction_type}) for {self.user.telegram_id}
