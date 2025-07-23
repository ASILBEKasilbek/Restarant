from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

class BaseModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at"),
        help_text=_("Date and time when the object was created")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated at"),
        help_text=_("Date and time when the object was last updated")
    )

    class Meta:
        abstract = True  # This class is only for inheritance

class Restaurant(BaseModel):
    name = models.CharField(
        max_length=100,
        verbose_name=_("Restaurant name"),
        db_index=True
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name=_("Slug"),
        blank=True
    )
    address = models.TextField(verbose_name=_("Address"))
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Phone number"),
        help_text=_("Contact phone number of the restaurant")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("Indicates if the restaurant is currently active")
    )
    cover_image = models.ImageField(
        upload_to="restaurant_covers/%Y/%m/%d/",
        blank=True,
        null=True,
        verbose_name=_("Cover image")
    )
    opening_hours = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Opening hours"),
        help_text=_("E.g., Mon-Fri 9:00-22:00")
    )

    class Meta:
        verbose_name = _("Restaurant")
        verbose_name_plural = _("Restaurants")
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            original_slug = self.slug
            counter = 1
            while Restaurant.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def average_rating(self):
        avg = self.orders.aggregate(avg_rating=models.Avg('reviews__rating'))['avg_rating']
        return round(avg, 1) if avg else 0

class Category(BaseModel):
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="categories",
        verbose_name=_("Restaurant")
    )
    name = models.CharField(
        max_length=50,
        verbose_name=_("Category name"),
        db_index=True
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Optional description of the category")
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
        help_text=_("Display order within the restaurant")
    )

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
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
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="menu_items",
        verbose_name=_("Restaurant")
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="menu_items",
        verbose_name=_("Category")
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("Item name"),
        db_index=True
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Optional description of the menu item")
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("Price")
    )
    image = models.ImageField(
        upload_to="menu_images/%Y/%m/%d/",
        blank=True,
        null=True,
        verbose_name=_("Image")
    )
    is_available = models.BooleanField(
        default=True,
        verbose_name=_("Available"),
        help_text=_("Indicates if the menu item is currently available")
    )
    dietary_info = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Dietary information"),
        help_text=_("E.g., vegetarian, halal, gluten-free")
    )
    preparation_time = models.PositiveIntegerField(
        default=15,
        verbose_name=_("Preparation time (minutes)"),
        help_text=_("Estimated preparation time in minutes"),
        validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = _("Menu Item")
        verbose_name_plural = _("Menu Items")
        ordering = ['name']
        indexes = [
            models.Index(fields=['restaurant', 'is_available']),
            models.Index(fields=['category']),
            models.Index(fields=['name', 'is_available']),
        ]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"

class UserProfile(BaseModel):
    telegram_id = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Telegram ID"),
        db_index=True
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Phone number")
    )
    loyalty_points = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Loyalty points")
    )
    preferred_language = models.CharField(
        max_length=10,
        choices=[
            ('uz', _('Uzbek')),
            ('ru', _('Russian')),
            ('en', _('English'))
        ],
        default='uz',
        verbose_name=_("Preferred language")
    )
    default_delivery_address = models.TextField(
        blank=True,
        verbose_name=_("Default delivery address")
    )

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")
        ordering = ['telegram_id']

    def __str__(self):
        return f"User {self.telegram_id}"

class Cart(BaseModel):
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="carts",
        verbose_name=_("User")
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="carts",
        verbose_name=_("Restaurant")
    )

    class Meta:
        verbose_name = _("Cart")
        verbose_name_plural = _("Carts")
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'restaurant'],
                name='unique_cart_per_user_restaurant'
            )
        ]

    def __str__(self):
        return f"Cart for {self.user.telegram_id} at {self.restaurant.name}"

    @property
    def total_price(self):
        return sum(item.quantity * item.menu_item.price for item in self.items.all())

class CartItem(BaseModel):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Cart")
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name=_("Menu item")
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("Quantity")
    )

    class Meta:
        verbose_name = _("Cart Item")
        verbose_name_plural = _("Cart Items")
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'menu_item'],
                name='unique_cart_item'
            )
        ]

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name} in cart"

class Order(BaseModel):
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('accepted', _('Accepted')),
        ('preparing', _('Preparing')),
        ('delivered', _('Delivered')),
        ('cancelled', _('Cancelled')),
    ]

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name=_("Restaurant")
    )
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("User")
    )
    table_number = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_("Table number")
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
        verbose_name=_("Total price")
    )
    delivery_address = models.TextField(
        blank=True,
        verbose_name=_("Delivery address")
    )
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('cash', _('Cash')),
            ('card', _('Card')),
            ('online', _('Online payment'))
        ],
        verbose_name=_("Payment method")
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
        help_text=_("Additional customer requests")
    )
    estimated_delivery_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Estimated delivery time")
    )

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['restaurant', 'status']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"Order #{self.id} - {self.restaurant.name}"

    def calculate_estimated_delivery(self):
        max_preparation_time = self.items.aggregate(
            max_time=models.Max('menu_item__preparation_time')
        )['max_time'] or 15
        self.estimated_delivery_time = self.created_at + timezone.timedelta(minutes=max_preparation_time + 15)
        self.save()

class OrderItem(BaseModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Order")
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_items",
        verbose_name=_("Menu item")
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("Quantity")
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("Price"),
        help_text=_("Price per item at the time of order")
    )

    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")
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
        verbose_name=_("Order")
    )
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("User")
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_("Rating")
    )
    comment = models.TextField(
        blank=True,
        verbose_name=_("Comment")
    )

    class Meta:
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
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
    TRANSACTION_TYPES = [
        ('earned', _('Earned')),
        ('spent', _('Spent')),
        ('refunded', _('Refunded')),
    ]

    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="loyalty_transactions",
        verbose_name=_("User")
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Order")
    )
    points = models.IntegerField(
        verbose_name=_("Points")
    )
    description = models.CharField(
        max_length=200,
        verbose_name=_("Description")
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        verbose_name=_("Transaction type")
    )

    class Meta:
        verbose_name = _("Loyalty Transaction")
        verbose_name_plural = _("Loyalty Transactions")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.points} points ({self.transaction_type}) for {self.user.telegram_id}"