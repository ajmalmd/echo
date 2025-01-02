from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.utils.timezone import now
from django.core.exceptions import ValidationError


# Custom User Manager
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Creates and returns a superuser with an email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, password, **extra_fields)


# Custom User Model
class User(AbstractBaseUser, PermissionsMixin):
    GENDER_CHOICES = [("male", "Male"), ("female", "Female"), ("other", "Other")]
    fullname = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    mobile_number = models.CharField(max_length=15, blank=True, null=True, default=None)
    gender = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        choices=GENDER_CHOICES,
        default=None
    )
    dob = models.DateField(blank=True, null=True, default=None)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class OTP(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(default=now)
    resend_count = models.IntegerField(default=0)


class Review(models.Model):
    product = models.ForeignKey(
        "manager.Product", on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField()
    review_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.fullname} - {self.product.name}"


# Cart Model
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)

    def total_price(self):
        """Calculates the total price of all items in the cart."""
        return sum(item.total_price() for item in self.items.all())

    def total_discounted_price(self):
        """Calculates the total discounted price for the cart."""
        return sum(item.discounted_price() for item in self.items.all())

    def __str__(self):
        return f"Cart for {self.user.email}"


# CartItem Model
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product_variant = models.ForeignKey(
        "manager.ProductVariant", on_delete=models.CASCADE, related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(default=1)

    def total_price(self):
        """Calculates the total price for this cart item."""
        if (
            not self.product_variant.is_active
            or not self.product_variant.product.is_active
            or not self.product_variant.product.brand.is_active
            or self.product_variant.stock <= 0
        ):
            return 0

        return self.product_variant.price * self.quantity

    def discounted_price(self):
        """Calculates the total discounted price for this cart item."""
        if (
            not self.product_variant.is_active
            or not self.product_variant.product.is_active
            or not self.product_variant.product.brand.is_active
            or self.product_variant.stock <= 0
        ):
            return 0
        return self.product_variant.discounted_price() * self.quantity

    def clean(self):
        """Validate stock availability."""
        if self.quantity > self.product_variant.stock:
            raise ValidationError(
                f"Only {self.product_variant.stock} units of {self.product_variant.name} are available."
            )

    def __str__(self):
        return f"{self.quantity} x {self.product_variant.name} in {self.cart.user.email}'s cart"


# Address Model
class Address(models.Model):
    ADDRESS_TYPE_CHOICES = [
        ("home", "Home"),
        ("work", "Work"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    name = models.CharField(max_length=75)
    contact = models.CharField(max_length=20)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPE_CHOICES)
    is_default = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Ensure only one default address per user
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(
                is_default=False
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.address_type.capitalize()} Address for {self.user.email}"


class Order(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("cod", "Cash on Delivery"),
        # ("razorpay", "Razorpay"),
        # ("upi", "UPI"),
        # ("card", "Card Payment"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, related_name="order_address"
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price_after_discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    order_payment = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, default="cod"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def overall_status(self):
        """Calculate the overall status of the order based on its items."""
        item_statuses = self.items.values_list("status", flat=True)
        if all(status == "delivered" for status in item_statuses):
            return "completed"
        elif any(status == "returned" for status in item_statuses):
            return "partially returned"
        elif any(status == "shipped" for status in item_statuses):
            return "partially shipped"
        elif all(status == "cancelled" for status in item_statuses):
            return "cancelled"
        return "pending"

    def __str__(self):
        return f"Order #{self.id} by {self.user.email}"


# OrderItem Model
class OrderItem(models.Model):
    ORDER_ITEM_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("returned", "Returned"),
        ("cancelled", "Cancelled"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_variant = models.ForeignKey(
        "manager.ProductVariant",
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_after_discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    status = models.CharField(
        max_length=20, choices=ORDER_ITEM_STATUS_CHOICES, default="pending"
    )

    def sub_total(self):
        """
        Calculate the subtotal after applying discounts.
        """
        if self.discount and self.discount < self.price:
            return (self.price - self.discount) * self.quantity
        return self.price * self.quantity

    def total_price(self):
        """
        Calculate the total price without discounts.
        """
        return self.price * self.quantity

    def total_discount(self):
        """
        Calculate the total discount for the order item.
        """
        return self.discount * self.quantity

    def __str__(self):
        return (
            f"{self.quantity} x {self.product_variant.name} in Order #{self.order.id}"
        )
