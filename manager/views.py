from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from .utils import paginate_items
from .models import Brand, Product, ProductVariant
from store.validators import is_valid_name
from store.models import User
from django.contrib import messages
from django.db.models import Count
from django.contrib.auth.decorators import user_passes_test


def is_staff_user(user):
    return user.is_authenticated and user.is_staff and user.is_active


@never_cache
def admin_login(request):

    next_url = request.GET.get("next", "dashboard")

    if request.user.is_authenticated:
        return redirect(next_url)

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)

        if user is not None and user.is_staff and user.is_active:
            login(request, user)
            return redirect(next_url)

        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "manager/login.html", {"next": next_url})


def admin_logout(request):
    logout(request)
    return redirect("admin_login")


@login_required(login_url="admin_login")
@user_passes_test(is_staff_user)
@never_cache
def dashboard(request):
    return render(request, "manager/dashboard.html")


@login_required(login_url="admin_login")
@user_passes_test(is_staff_user)
@never_cache
def users(request):

    search_query = request.GET.get("search", "")

    # Fetch users, filter by search query if provided
    if search_query:
        users = (
            User.objects.filter(name__icontains=search_query)
            .exclude(is_staff=True)
            .order_by("-date_joined")
        )
    else:
        users = User.objects.exclude(is_staff=True).order_by("-date_joined")

    page_obj = paginate_items(request, users, per_page=10)
    # Pass the users data to the template
    return render(request, "manager/users.html", {"page_obj": page_obj})


@user_passes_test(is_staff_user)
def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    # action = "activated" if user.is_active else "deactivated"
    # messages.success(request, f"Product {user.name} has been {action}.")
    return redirect("users")


@login_required(login_url="admin_login")
@user_passes_test(is_staff_user)
@never_cache
def brands(request):

    search_query = request.GET.get("search", "")

    # Fetch brands, filter by search query if provided
    if search_query:
        brands = Brand.objects.filter(name__icontains=search_query).annotate(
            product_count=Count("products")
        )
    else:
        brands = Brand.objects.annotate(product_count=Count("products"))

    page_obj = paginate_items(request, brands, per_page=10)

    return render(request, "manager/brands.html", {"page_obj": page_obj})


@user_passes_test(is_staff_user)
def add_brand(request):
    if request.method == "POST":
        brand_name = request.POST.get("name")
        if not is_valid_name(brand_name):
            messages.error(request, "Invalid name. Use only alphabets and spaces.")
            return redirect("brands")

        if Brand.objects.filter(name=brand_name).exists():
            messages.error(request, "Brand with this name already exists.")
            return redirect("brands")

        # Create the new brand
        Brand.objects.create(name=brand_name)

        messages.success(request, "Brand added successfully.")
        return redirect("brands")  # Redirect to the brand list page

    return redirect("brands")


@user_passes_test(is_staff_user)
def edit_brand(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    if request.method == "POST":
        new_name = request.POST.get("name")

        # Validate the new brand name
        if not is_valid_name(new_name):
            messages.error(request, "Invalid name. Use only alphabets and spaces.")
            return redirect("brands")

        # Check if a different brand already has this name
        if Brand.objects.filter(name=new_name).exclude(id=brand_id).exists():
            messages.error(request, "Brand with this name already exists.")
            return redirect("brands")

        # Update the brand
        try:
            brand.name = new_name
            brand.save()
            messages.success(request, "Brand updated successfully.")
        except Brand.DoesNotExist:
            messages.error(request, "Brand not found.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

        return redirect("brands")

    return redirect("brands")


@user_passes_test(is_staff_user)
def toggle_brand_status(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    brand.is_active = not brand.is_active
    brand.save()
    # action = "activated" if brand.is_active else "deactivated"
    # messages.success(request, f"Product {brand.name} has been {action}.")
    return redirect("brands")


@login_required(login_url="admin_login")
@user_passes_test(is_staff_user)
@never_cache
def products(request):

    search_query = request.GET.get("search", "")

    # Fetch products, filter by search query if provided
    if search_query:
        products = Product.objects.filter(name__icontains=search_query).annotate(
            variant_count=Count("variants")
        )
    else:
        products = Product.objects.all().annotate(variant_count=Count("variants"))

    page_obj = paginate_items(request, products, per_page=10)
    brands = Brand.objects.filter(is_active=True)

    context = {"page_obj": page_obj, "brands": brands, "product": Product}
    return render(request, "manager/products.html", context)


@user_passes_test(is_staff_user)
def toggle_product_status(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = not product.is_active
    product.save()
    # action = "activated" if product.is_active else "deactivated"
    # messages.success(request, f"Product {product.name} has been {action}.")
    return redirect("products")


@login_required(login_url="admin_login")
@user_passes_test(is_staff_user)
@never_cache
def product_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variants = product.variants.all()
    return render(
        request, "manager/product_view.html", {"product": product, "variants": variants}
    )


@user_passes_test(is_staff_user)
def toggle_variant_status(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    variant.is_active = not variant.is_active
    variant.save()
    # action = "activated" if variant.is_active else "deactivated"
    # messages.success(request, f"Variant {variant.name} has been {action}.")
    return redirect("product_view", product_id=variant.product.id)


@user_passes_test(is_staff_user)
def add_product(request):
    if request.method == "POST":
        name = request.POST.get("name")
        brand_id = request.POST.get("brand")
        connectivity = request.POST.get("connectivity")
        product_type = request.POST.get("type")
        description = request.POST.get("description")
        price = request.POST.get("price")

        try:
            brand = Brand.objects.get(id=brand_id)
            product = Product.objects.create(
                name=name,
                brand=brand,
                connectivity=connectivity,
                type=product_type,
                description=description,
                price=price,
                created_by=request.user,
            )
            product.save()
            messages.success(request, "Product added successfully!")
        except Brand.DoesNotExist:
            messages.error(request, "Invalid brand selected.")
        except Exception as e:
            messages.error(request, f"Error adding product: {str(e)}")

        return redirect(reverse("product_view", args=[product.id]))

    return redirect("products")


@user_passes_test(is_staff_user)
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == "POST":
        name = request.POST.get("name")
        brand_id = request.POST.get("brand")
        connectivity = request.POST.get("connectivity")
        product_type = request.POST.get("type")
        description = request.POST.get("description")
        price = request.POST.get("price")

        try:
            brand = Brand.objects.get(id=brand_id)
            product.name = name
            product.brand = brand
            product.connectivity = connectivity
            product.type = product_type
            product.description = description
            product.price = price
            product.updated_by = request.user
            product.save()
            messages.success(request, "Product updated successfully!")
        except Brand.DoesNotExist:
            messages.error(request, "Invalid brand selected.")
        except Exception as e:
            messages.error(request, f"Error adding product: {str(e)}")

        return redirect(reverse("product_view", args=[product.id]))

    return redirect("products")
