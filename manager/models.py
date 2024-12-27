from django.db import models
from store.models import User
from cloudinary.models import CloudinaryField  # Cloudinary image field


# Brand Model
class Brand(models.Model):
    name = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)

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
        """Returns the price after applying the variant-level discount."""
        if self.is_discount_active and self.discount_value:
            if self.discount_type == "percentage":
                discount_amount = (self.discount_value / 100) * self.price
                return max(self.price - discount_amount, 0)
            elif self.discount_type == "fixed":
                return max(self.price - self.discount_value, 0)
        return self.price  # No discount applied

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
