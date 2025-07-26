from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache
from django.contrib.auth.models import User


class BaseModel(models.Model):
    """Vaqt belgilari bilan abstrakt asosiy model."""
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Yaratilgan vaqt"),
        help_text=_("Obyekt yaratilgan sana va vaqt")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Yangilangan vaqt"),
        help_text=_("Obyekt oxirgi marta yangilangan sana va vaqt")
    )

    class Meta:
        abstract = True


class Image(models.Model):
    """Rasmlarni izohlar bilan saqlash uchun model."""
    image = models.ImageField(
        upload_to="images/%Y/%m/%d/",
        verbose_name=_("Rasm")
    )
    caption = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Izoh")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Rasm")
        verbose_name_plural = _("Rasmlar")

    def __str__(self):
        return self.caption or f"Rasm {self.id}"


class Restaurant(BaseModel):
    """Restoranni ifodalovchi model."""
    name = models.CharField(
        max_length=100,
        verbose_name=_("Restoran nomi"),
        db_index=True
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name=_("Slug"),
        blank=True
    )
    address = models.TextField(verbose_name=_("Manzil"))
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Telefon raqami"),
        help_text=_("Aloqa telefoni (masalan, +998901234567)"),
        validators=[
            RegexValidator(
                regex=r'^\+?[1-9]\d{1,14}$',
                message=_("To‘g‘ri telefon raqamini kiriting (masalan, +998901234567)")
            )
        ]
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Faol"),
        help_text=_("Restoran hozirda faol ekanligini ko‘rsatadi")
    )
    images = models.ManyToManyField(
        Image,
        related_name="restaurants",
        blank=True,
        verbose_name=_("Rasmlar")
    )
    opening_hours = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Ish vaqti"),
        help_text=_("Masalan, Dush-Shan 09:00-22:00, Yak-Shan 10:00-23:00"),
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z,\- ]+\d{2}:\d{2}-\d{2}:\d{2}(,\s*[A-Za-z,\- ]+\d{2}:\d{2}-\d{2}:\d{2})*$',
                message=_("To‘g‘ri ish vaqtini kiriting (masalan, Dush-Shan 09:00-22:00)")
            )
        ]
    )
    cached_average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=0.0,
        verbose_name=_("Keshlangan o‘rtacha baho"),
        help_text=_("Sharhlardan olingan o‘rtacha baho")
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="owned_restaurants",
        verbose_name=_("Egasi")
    )

    class Meta:
        verbose_name = _("Restoran")
        verbose_name_plural = _("Restoranlar")
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug', 'is_active']),
        ]

    def save(self, *args, **kwargs):
        """Slug bo‘lmasa, noyob slug yaratadi va saqlaydi."""
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        """Restoran nomiga asoslangan noyob slug yaratadi."""
        slug = slugify(self.name)
        original_slug = slug
        counter = 1
        while Restaurant.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{original_slug}-{counter}"
            counter += 1
        return slug

    def __str__(self):
        return self.name

    @property
    def average_rating(self):
        """Restoran uchun o‘rtacha baho olish yoki hisoblash."""
        cache_key = f"restaurant_{self.id}_average_rating"
        avg = cache.get(cache_key)
        if avg is None:
            avg = self.orders.aggregate(avg_rating=models.Avg('reviews__rating'))['avg_rating'] or 0.0
            avg = round(avg, 1)
            cache.set(cache_key, avg, timeout=3600)  # 1 soat keshlash
            self.cached_average_rating = avg
            self.save(update_fields=['cached_average_rating'])
        return avg

    def get_statistics(self):
        """Restoran egasi uchun asosiy statistikani qaytaradi."""
        total_orders = self.orders.count()
        active_orders = self.orders.filter(status__in=['pending', 'accepted', 'preparing']).count()
        total_revenue = self.orders.filter(status='served').aggregate(
            total=models.Sum('total_price')
        )['total'] or 0
        return {
            'jami_buyurtmalar': total_orders,
            'faol_buyurtmalar': active_orders,
            'jami_daromad': total_revenue,
            'ortacha_baho': self.average_rating,
        }


class Table(BaseModel):
    """Restorandagi stol va QR kodni ifodalovchi model."""
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="tables",
        verbose_name=_("Restoran")
    )
    table_number = models.CharField(
        max_length=10,
        verbose_name=_("Stol raqami"),
        db_index=True
    )
    qr_code = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("QR kod"),
        help_text=_("Stolga xos menyuni ochish uchun noyob QR kod")
    )
    capacity = models.PositiveIntegerField(
        default=4,
        verbose_name=_("Sig‘im"),
        help_text=_("Stoldagi o‘rindiqlar soni")
    )

    class Meta:
        verbose_name = _("Stol")
        verbose_name_plural = _("Stollar")
        constraints = [
            models.UniqueConstraint(
                fields=['restaurant', 'table_number'],
                name='unique_table_per_restaurant'
            )
        ]

    def __str__(self):
        return f"Stol {self.table_number} ({self.restaurant.name})"

    def save(self, *args, **kwargs):
        """QR kod bo‘lmasa, noyob QR kod yaratadi."""
        if not self.qr_code:
            self.qr_code = self._generate_unique_qr_code()
        super().save(*args, **kwargs)

    def _generate_unique_qr_code(self):
        """Stol uchun noyob QR kod yaratadi."""
        import uuid
        qr_code = f"table-{self.restaurant.id}-{self.table_number}-{uuid.uuid4().hex[:8]}"
        while Table.objects.filter(qr_code=qr_code).exists():
            qr_code = f"table-{self.restaurant.id}-{self.table_number}-{uuid.uuid4().hex[:8]}"
        return qr_code


class Category(BaseModel):
    """Restorandagi menyu elementlarini kategoriyalash uchun model."""
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="categories",
        verbose_name=_("Restoran")
    )
    name = models.CharField(
        max_length=50,
        verbose_name=_("Kategoriya nomi"),
        db_index=True
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Tavsif"),
        help_text=_("Kategoriya uchun ixtiyoriy tavsif")
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Tartib"),
        help_text=_("Restoranda ko‘rsatish tartibi")
    )

    class Meta:
        verbose_name = _("Kategoriya")
        verbose_name_plural = _("Kategoriyalar")
        ordering = ['order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['restaurant', 'name'],
                name='unique_category_per_restaurant'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"


class MenuItem(BaseModel):
    """Restorandagi alohida menyu elementlari uchun model."""
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
    name = models.CharField(
        max_length=100,
        verbose_name=_("Element nomi"),
        db_index=True
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Tavsif"),
        help_text=_("Menyu elementi uchun ixtiyoriy tavsif")
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("Narx")
    )
    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_("Chegirmali narx"),
        help_text=_("Agar mavjud bo‘lsa, chegirmali narx")
    )
    images = models.ManyToManyField(
        Image,
        related_name="menu_items",
        blank=True,
        verbose_name=_("Rasmlar")
    )
    is_available = models.BooleanField(
        default=True,
        verbose_name=_("Mavjud"),
        help_text=_("Menyu elementi hozirda mavjud ekanligini ko‘rsatadi")
    )
    dietary_info = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Dieta ma’lumotlari"),
        help_text=_("Masalan, vegetarian, halol, glyutensiz")
    )
    preparation_time = models.PositiveIntegerField(
        default=15,
        verbose_name=_("Tayyorlash vaqti (daqiqa)"),
        help_text=_("Taxminiy tayyorlash vaqti, daqiqalarda"),
        validators=[MinValueValidator(1)]
    )
    stock_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Zaxira miqdori"),
        help_text=_("Ushbu menyu elementi uchun mavjud zaxira")
    )

    class Meta:
        verbose_name = _("Menyu elementi")
        verbose_name_plural = _("Menyu elementlari")
        ordering = ['name']
        indexes = [
            models.Index(fields=['restaurant', 'is_available']),
            models.Index(fields=['category']),
            models.Index(fields=['name', 'is_available']),
            models.Index(fields=['price', 'discount_price']),
        ]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"

    @property
    def effective_price(self):
        """Chegirmali narx mavjud bo‘lsa, uni qaytaradi, aks holda oddiy narx."""
        return self.discount_price if self.discount_price is not None else self.price

    def reduce_stock(self, quantity):
        """Zaxira miqdorini kamaytiradi va mavjudlikni yangilaydi."""
        if self.stock_quantity >= quantity:
            self.stock_quantity -= quantity
            self.is_available = self.stock_quantity > 0
            self.save(update_fields=['stock_quantity', 'is_available'])
            return True
        return False


class Staff(BaseModel):
    """Restoran xodimlari (ofitsiantlar, menejerlar) uchun model."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="staff_profiles",
        verbose_name=_("Foydalanuvchi")
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="staff",
        verbose_name=_("Restoran")
    )
    role = models.CharField(
        max_length=50,
        choices=[
            ('waiter', _('Ofitsiant')),
            ('manager', _('Menejer')),
            ('chef', _('Oshpaz'))
        ],
        verbose_name=_("Rol")
    )

    class Meta:
        verbose_name = _("Xodim")
        verbose_name_plural = _("Xodimlar")
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'restaurant'],
                name='unique_staff_per_restaurant'
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.role} at {self.restaurant.name}"


class UserProfile(BaseModel):
    """Foydalanuvchi profillari uchun model."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_profile",
        verbose_name=_("Foydalanuvchi")
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Telefon raqami"),
        validators=[
            RegexValidator(
                regex=r'^\+?[1-9]\d{1,14}$',
                message=_("To‘g‘ri telefon raqamini kiriting (masalan, +998901234567)")
            )
        ]
    )
    loyalty_points = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Sadoqat ballari")
    )
    preferred_language = models.CharField(
        max_length=10,
        choices=[
            ('uz', _('O‘zbek')),
            ('ru', _('Rus')),
            ('en', _('Ingliz'))
        ],
        default='uz',
        verbose_name=_("Afzal til")
    )
    default_delivery_address = models.TextField(
        blank=True,
        verbose_name=_("Standart yetkazib berish manzili")
    )
    notification_preferences = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Bildirishnoma sozlamalari"),
        help_text=_("Masalan, {'email': True, 'sms': False}")
    )

    class Meta:
        verbose_name = _("Foydalanuvchi profili")
        verbose_name_plural = _("Foydalanuvchi profillari")
        ordering = ['user__username']

    def __str__(self):
        return self.user.username

    def award_loyalty_points(self, order):
        """Buyurtma summasiga asoslangan sadoqat ballarini beradi."""
        points = int(order.total_price // 10)  # 10 pul birligiga 1 bal
        LoyaltyTransaction.objects.create(
            user_profile=self,
            order=order,
            points=points,
            description=f"Buyurtma #{order.id} uchun ballar",
            transaction_type='earned'
        )
        self.loyalty_points += points
        self.save(update_fields=['loyalty_points'])


class Cart(BaseModel):
    """Foydalanuvchi savati, restoran va stolga bog‘langan."""
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="carts",
        verbose_name=_("Foydalanuvchi profili")
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="carts",
        verbose_name=_("Restoran")
    )
    table = models.ForeignKey(
        Table,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carts",
        verbose_name=_("Stol")
    )

    class Meta:
        verbose_name = _("Savat")
        verbose_name_plural = _("Savatlar")
        constraints = [
            models.UniqueConstraint(
                fields=['user_profile', 'restaurant', 'table'],
                name='unique_cart_per_user_restaurant_table'
            )
        ]

    def __str__(self):
        return f"{self.user_profile} uchun savat, {self.restaurant.name} (Stol {self.table.table_number if self.table else 'Stol yo‘q'})"

    @property
    def total_price(self):
        """Savatdagi barcha elementlarning umumiy narxini hisoblaydi."""
        return sum(item.quantity * item.menu_item.effective_price for item in self.items.all())


class CartItem(BaseModel):
    """Savatdagi alohida elementlar uchun model."""
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Savat")
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name=_("Menyu elementi")
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("Miqdor")
    )

    class Meta:
        verbose_name = _("Savat elementi")
        verbose_name_plural = _("Savat elementlari")
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'menu_item'],
                name='unique_cart_item'
            )
        ]

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name} savatda"


class Order(BaseModel):
    """Mijoz buyurtmalari uchun model."""
    STATUS_CHOICES = [
        ('pending', _('Kutilmoqda')),
        ('accepted', _('Qabul qilindi')),
        ('preparing', _('Tayyorlanmoqda')),
        ('ready', _('Tayyor')),
        ('served', _('Yetkazildi')),
        ('cancelled', _('Bekor qilindi')),
    ]

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name=_("Restoran")
    )
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("Foydalanuvchi profili")
    )
    table = models.ForeignKey(
        Table,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("Stol")
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_("Holat")
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("Umumiy narx")
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Chegirma summasi")
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
    estimated_delivery_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Taxminiy yetkazib berish vaqti")
    )
    assigned_waiter = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_orders",
        verbose_name=_("Tayinlangan ofitsiant")
    )

    class Meta:
        verbose_name = _("Buyurtma")
        verbose_name_plural = _("Buyurtmalar")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['restaurant', 'status']),
            models.Index(fields=['user_profile', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['table']),
        ]

    def __str__(self):
        return f"Buyurtma #{self.id} - {self.restaurant.name} (Stol {self.table.table_number if self.table else 'Stol yo‘q'})"

    def calculate_estimated_delivery(self):
        """Tayyorlash vaqtiga asoslangan taxminiy yetkazib berish vaqtini hisoblaydi."""
        max_preparation_time = self.items.aggregate(
            max_time=models.Max('menu_item__preparation_time')
        )['max_time'] or 15
        self.estimated_delivery_time = self.created_at + timezone.timedelta(minutes=max_preparation_time)
        self.save(update_fields=['estimated_delivery_time'])

    def apply_discount(self, discount_percentage):
        """Buyurtma summasiga chegirma qo‘llaydi."""
        if 0 <= discount_percentage <= 100:
            self.discount_amount = self.total_price * (discount_percentage / 100)
            self.total_price -= self.discount_amount
            self.save(update_fields=['total_price', 'discount_amount'])

    def update_status(self, new_status, waiter=None):
        """Buyurtma holatini yangilaydi va agar berilgan bo‘lsa, ofitsiantni tayinlaydi."""
        if new_status in dict(self.STATUS_CHOICES):
            self.status = new_status
            if waiter:
                self.assigned_waiter = waiter
            self.save(update_fields=['status', 'assigned_waiter'])
            # Real vaqtda yangilash uchun (Django Channels orqali)
            # Bu views.py da qo‘shimcha amalga oshirishni talab qiladi


class OrderItem(BaseModel):
    """Buyurtmadagi alohida elementlar uchun model."""
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
        verbose_name=_("Menyu elementi")
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("Miqdor")
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("Narx"),
        help_text=_("Buyurtma vaqtidagi har bir elementning narxi")
    )

    class Meta:
        verbose_name = _("Buyurtma elementi")
        verbose_name_plural = _("Buyurtma elementlari")
        indexes = [
            models.Index(fields=['order', 'menu_item']),
        ]

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name if self.menu_item else 'O‘chirilgan element'} (Buyurtma #{self.order.id})"


class Review(BaseModel):
    """Buyurtmalar uchun mijoz sharhlari modeli."""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("Buyurtma")
    )
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("Foydalanuvchi profili")
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_("Baho")
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
                fields=['order', 'user_profile'],
                name='unique_review_per_user_order'
            )
        ]

    def __str__(self):
        return f"Buyurtma #{self.order.id} uchun sharh - {self.rating}/5"


class LoyaltyTransaction(BaseModel):
    """Sadoqat ballari operatsiyalarini kuzatish uchun model."""
    TRANSACTION_TYPES = [
        ('earned', _('Topilgan')),
        ('spent', _('Sarflangan')),
        ('refunded', _('Qaytarilgan')),
    ]

    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="loyalty_transactions",
        verbose_name=_("Foydalanuvchi profili")
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Buyurtma")
    )
    points = models.IntegerField(
        verbose_name=_("Ballar")
    )
    description = models.CharField(
        max_length=200,
        verbose_name=_("Tavsif")
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        verbose_name=_("Operatsiya turi")
    )

    class Meta:
        verbose_name = _("Sadoqat operatsiyasi")
        verbose_name_plural = _("Sadoqat operatsiyalari")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.points} ballar ({self.transaction_type}) {self.user_profile} uchun"


class InventoryTransaction(BaseModel):
    """Menyu elementlari zaxirasini kuzatish uchun model."""
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name="inventory_transactions",
        verbose_name=_("Menyu elementi")
    )
    quantity = models.IntegerField(
        verbose_name=_("Miqdor"),
        help_text=_("Zaxirani to‘ldirish uchun musbat, sarf qilish uchun manfiy")
    )
    description = models.CharField(
        max_length=200,
        verbose_name=_("Tavsif"),
        help_text=_("Masalan, '50 dona to‘ldirildi', 'Buyurtma #123 uchun ishlatildi'")
    )

    class Meta:
        verbose_name = _("Inventar operatsiyasi")
        verbose_name_plural = _("Inventar operatsiyalari")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.quantity} dona {self.menu_item.name} uchun - {self.description}"


class AdminDashboard(BaseModel):
    """Admin paneli statistikasi uchun model."""
    total_restaurants = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Jami restoranlar")
    )
    total_users = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Jami foydalanuvchilar")
    )
    total_orders = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Jami buyurtmalar")
    )
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_("Jami daromad")
    )

    class Meta:
        verbose_name = _("Admin paneli")
        verbose_name_plural = _("Admin panellari")

    def __str__(self):
        return f"Admin paneli {self.id}"

    def update_statistics(self):
        """Admin paneli statistikasini yangilaydi."""
        self.total_restaurants = Restaurant.objects.count()
        self.total_users = UserProfile.objects.count()
        self.total_orders = Order.objects.count()
        self.total_revenue = Order.objects.filter(status='served').aggregate(
            total=models.Sum('total_price')
        )['total'] or 0
        self.save()

        