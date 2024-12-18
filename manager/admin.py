from django.contrib import admin
from .models import Brand, Product, ProductVariant, ProductImage


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # Allows adding multiple images at once
    fields = ("image_path",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "is_active", "created_at", "updated_at")
    list_filter = ("brand", "is_active", "connectivity", "type")
    search_fields = ("name", "description")
    raw_id_fields = ("created_by", "updated_by")
    fieldsets = (
        (None, {"fields": ("name", "brand", "description", "connectivity", "type")}),
        ("Status", {"fields": ("is_active",)}),
        (
            "Audit Info",
            {"fields": ("created_by", "updated_by", "created_at", "updated_at")},
        ),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("name", "product", "price", "stock", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "product__name")
    raw_id_fields = ("created_by", "updated_by")
    fieldsets = (
        (None, {"fields": ("name", "product", "price", "stock")}),
        (
            "Discount Info",
            {"fields": ("discount_type", "discount_value", "is_discount_active")},
        ),
        ("Status", {"fields": ("is_active",)}),
        (
            "Audit Info",
            {"fields": ("created_by", "updated_by", "created_at", "updated_at")},
        ),
    )
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProductImageInline]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product_variant", "image_path")
    search_fields = ("product_variant__name", "product_variant__product__name")
    list_filter = ("product_variant__product__brand", "product_variant__product__type")
