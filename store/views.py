from django.shortcuts import render, get_object_or_404
from manager.models import Product

def product_detail(request, pk):
    # Fetch the product
    product = get_object_or_404(Product, pk=pk, is_active=True, is_deleted=False)

    # Fetch related variants
    variants = product.variants.filter(is_active=True, is_deleted=False)

    # Fetch product reviews
    reviews = product.reviews.all()

    # Fetch related products (same category or brand)
    related_products = Product.objects.filter(
        type=product.connectivity, is_active=True, is_deleted=False
    ).exclude(pk=pk)[:4]  # Limit to 4 related products

    context = {
        'product': product,
        'variants': variants,
        'reviews': reviews,
        'related_products': related_products,
    }

    return render(request, 'product_view.html', context)
