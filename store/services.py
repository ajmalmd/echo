from manager.models import Product, ProductImage, ProductVariant
from django.db.models import Prefetch, Subquery, OuterRef
import random
from django.core.mail import send_mail


def generate_otp():
    return str(random.randint(100000, 999999))  # Generate a 6-digit OTP


def send_otp_email(email, otp):
    subject = "Your OTP for Signup in echo."
    message = f"Your OTP is {otp}. It is valid for 5 minutes."
    from_email = "connect.echo.mails@gmail.com"
    recipient_list = [email]
    send_mail(subject, message, from_email, recipient_list)


def get_new_arrivals(limit=None):
    # Subquery to get the first active product variant for each product
    first_active_variant = (
        ProductVariant.objects.filter(product=OuterRef("pk"), is_active=True)
        .order_by("created_at")
        .values("id")[:1]
    )

    # Fetch the first 6 active products with their first active variant and its first image
    new_arrivals = (
        Product.objects.filter(is_active=True, brand__is_active=True)
        .annotate(first_variant_id=Subquery(first_active_variant))
        .prefetch_related(
            Prefetch(
                "variants",
                queryset=ProductVariant.objects.filter(
                    id__in=Subquery(first_active_variant)
                ).prefetch_related(
                    Prefetch(
                        "images",
                        queryset=ProductImage.objects.order_by("id")[:1],
                        to_attr="first_image",
                    )
                ),
                to_attr="first_variant",
            )
        )
        .order_by("-created_at")[:limit]
    )  # Limit to the latest products

    return new_arrivals
