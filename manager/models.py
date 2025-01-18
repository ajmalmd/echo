from django.db import models
from store.models import User
from cloudinary.models import CloudinaryField  # Cloudinary image field
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone

# Brand Model
class Brand(models.Model):
    name = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_brands"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="updated_brands"
    )

    def __str__(self):
        return self.name


# Product Model
class Product(models.Model):
    CONNECTIVITY_CHOICES = [
        ("wired", "Wired"),
        ("wireless", "Wireless"),
        ("multi", "Multi-functional"),
    ]

    TYPE_CHOICES = [("in_ear", "In the Ear"), ("over_ear", "Over the Ear")]

    name = models.CharField(max_length=255)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="products")
    description = models.TextField()
    connectivity = models.CharField(max_length=20, choices=CONNECTIVITY_CHOICES)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_products"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="updated_products"
    )

    def __str__(self):
        return self.name


# ProductVariant Model
class ProductVariant(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ("percentage", "Percentage"),
        ("fixed", "Fixed Amount"),
    ]

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_variants"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="updated_variants"
    )

    # Discount fields
    discount_type = models.CharField(
        max_length=20, choices=DISCOUNT_TYPE_CHOICES, null=True, blank=True
    )
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    is_discount_active = models.BooleanField(default=False)

    def discounted_price(self):
        """Returns the price after applying the best offer."""
        best_offer = self.get_best_offer()
        if best_offer:
            if best_offer.discount_type == 'percentage':
                discount_amount = (best_offer.discount_value / 100) * self.price
            else:  # fixed amount
                discount_amount = best_offer.discount_value
            return max(self.price - discount_amount, 0)
        if self.is_discount_active and self.discount_value:
            if self.discount_type == "percentage":
                discount_amount = (self.discount_value / 100) * self.price
                return max(self.price - discount_amount, 0)
            elif self.discount_type == "fixed":
                return max(self.price - self.discount_value, 0)
        return self.price  # No discount applied

    def get_best_offer(self):
        """Determines which offer is applied and returns the best offer."""
        current_time = timezone.now()
        product_offers = self.product.product_offers.filter(
            is_active=True,
            start_date__lte=current_time,
            end_date__gte=current_time
        )
        brand_offers = self.product.brand.brand_offers.filter(
            is_active=True,
            start_date__lte=current_time,
            end_date__gte=current_time
        )
        all_offers = list(product_offers) + list(brand_offers)
        
        if not all_offers:
            return None
        
        best_offer = min(all_offers, key=lambda offer: self.calculate_discounted_price(offer))
        return best_offer

    def calculate_discounted_price(self, offer):
        """Calculates the discounted price for a given offer."""
        if offer.discount_type == 'percentage':
            discount_amount = (offer.discount_value / 100) * self.price
        else:  # fixed amount
            discount_amount = offer.discount_value
        return max(self.price - discount_amount, 0)

    def __str__(self):
        return f"{self.name} - {self.product.name}"

    def get_similar_variants(self):
        """
        Finds product variants from other products with the same type, and connectivity.
        """
        return (
        ProductVariant.objects.filter(
            product__type=self.product.type,
            product__connectivity=self.product.connectivity,
            is_active=True,
            product__is_active=True,
            stock__gt=0
        )
        .exclude(product=self.product)
        .distinct("product")
    )


# Product Image Model
class ProductImage(models.Model):
    product_variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="images"
    )
    image_path = CloudinaryField("image")  # Using Cloudinary for image storage

    def __str__(self):
        return f"Image for {self.product_variant.name}"


# Base Offer Model
class Offer(models.Model):
    OFFER_TYPE_CHOICES = [
        ('product', 'Product Offer'),
        ('brand', 'Brand Offer'),
        # ('referral', 'Referral Offer'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    offer_type = models.CharField(max_length=20, choices=OFFER_TYPE_CHOICES)
    discount_type = models.CharField(max_length=10, choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')])
    discount_value = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    max_usage_limit = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_offers', blank=True, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='brand_offers', blank=True, null=True)

    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError("End date must be after start date.")

    def __str__(self):
        return self.name

# Coupon Model
class Coupon(models.Model):
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField()
    discount_type = models.CharField(max_length=10, choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')])
    discount_value = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(default=1)
    times_used = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError("End date must be after start date.")

    def __str__(self):
        return self.code


# Coupon Usage Model
class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey('store.Order', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('applied', 'Applied'), ('redeemed', 'Redeemed'), ('failed', 'Failed')])

    class Meta:
        unique_together = ('coupon', 'user', 'order')

    def __str__(self):
        return f"{self.user.email} used {self.coupon.code}"


# Referral Redemption Tracking Model
# class ReferralRedemption(models.Model):
#     referral_offer = models.ForeignKey(ReferralOffer, on_delete=models.CASCADE, related_name='redemptions')
#     referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrer_redemptions')
#     referee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referee_redemptions')
#     redeemed_at = models.DateTimeField(auto_now_add=True)
#     status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('redeemed', 'Redeemed')])

#     def __str__(self):
#         return f"Referrer: {self.referrer.email}, Referee: {self.referee.email}"

