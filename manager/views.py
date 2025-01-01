from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from .utils import paginate_items
from .models import Brand, Product, ProductVariant, ProductImage
from store.validators import *
from store.models import User
from django.contrib import messages
from django.db.models import Count
from django.contrib.auth.decorators import user_passes_test
from cloudinary.uploader import (
    upload as cloudinary_upload,
    destroy as cloudinary_delete,
)


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
        ).order_by("created_at")
    else:
        brands = Brand.objects.annotate(product_count=Count("products")).order_by("created_at")

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
        ).order_by("-created_at")
    else:
        products = Product.objects.all().annotate(variant_count=Count("variants")).order_by("-created_at")

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
    variants = product.variants.all().order_by("-created_at")
    images = {variant.id: variant.images.all() for variant in variants}
    return render(
        request,
        "manager/product_view.html",
        {
            "product": product,
            "variants": variants,
            "images": images,
            "product_variant": ProductVariant,
        },
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
        name = request.POST.get("name", "").strip()
        brand_id = request.POST.get("brand")
        connectivity = request.POST.get("connectivity")
        product_type = request.POST.get("type")
        description = convert_description(request.POST.get("description"))

        try:
            validate_product_name(name)
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect("products")

        try:
            brand = Brand.objects.get(id=brand_id)
            product = Product.objects.create(
                name=name,
                brand=brand,
                connectivity=connectivity,
                type=product_type,
                description=description,
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
        name = request.POST.get("name", "").strip()
        brand_id = request.POST.get("brand")
        connectivity = request.POST.get("connectivity")
        product_type = request.POST.get("type")
        description = convert_description(request.POST.get("description"))

        try:
            validate_product_name(name)
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect("products")

        try:
            brand = Brand.objects.get(id=brand_id)
            product.name = name
            product.brand = brand
            product.connectivity = connectivity
            product.type = product_type
            product.description = description
            product.updated_by = request.user
            product.save()
            messages.success(request, "Product updated successfully!")
        except Brand.DoesNotExist:
            messages.error(request, "Invalid brand selected.")
        except Exception as e:
            messages.error(request, f"Error adding product: {str(e)}")

        return redirect(reverse("product_view", args=[product.id]))

    return redirect("products")

@user_passes_test(is_staff_user)
def add_variant(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Extract form data
    name = request.POST.get("name")
    price = request.POST.get("price")
    stock = request.POST.get("stock")
    discount_type = request.POST.get("discount_type")
    discount_value = request.POST.get("discount_value")
    is_discount_active = True

    # Stock validation
    try:
        stock = int(stock)
        if stock < 0:
            messages.error(request, "Stock value must be a non-negative integer.")
            return redirect("product_view", product_id)
    except ValueError:
        messages.error(request, "Stock value must be an integer.")
        return redirect("product_view", product_id)
    
    # Price validation
    try:
        price = float(price)
        if price < 0:
            messages.error(request, "Price value must be a non-negative integer.")
            return redirect("product_view", product_id)
    except ValueError:
        messages.error(request, "Price value must be a number.")
        return redirect("product_view", product_id)
    
    if discount_type == "fixed":
        if float(discount_value)>float(price):
            messages.error(request, "Discount value must be less than the price.")
            return redirect("product_view", product_id)
    if discount_type == "percentage":
        if float(discount_value)>100:
            messages.error(request, "Discount value must be less than 100.")
            return redirect("product_view", product_id)
    
    
    if discount_type == "none" or not discount_type:
        discount_type = None
        discount_value = None
        is_discount_active = False

    # Convert discount_value to a numeric type if it's provided
    if discount_value:
        try:
            discount_value = float(discount_value)
        except ValueError:
            discount_value = None
            is_discount_active = False

    if not is_valid_name(name):
        messages.error(request, "Invalid name. Use only alphabets and spaces.")
        return redirect("product_view", product_id)

    try:
        # Create the variant
        variant = ProductVariant.objects.create(
            product=product,
            name=name,
            price=price,
            stock=stock,
            discount_type=discount_type,
            discount_value=discount_value,
            is_discount_active=is_discount_active,
            created_by=request.user,
        )

        # Handle images
        images = request.FILES.getlist("product_images")
        if len(images) < 3:
            messages.error(request, "You must upload at least 3 images.")
            variant.delete()  # Clean up the created variant
            return redirect("product_view", product_id)

        for image in images[:7]:  # Allow up to 7 images
            uploaded_image = cloudinary_upload(image)
            ProductImage.objects.create(
                product_variant=variant, image_path=uploaded_image["secure_url"]
            )

        messages.success(request, "Variant added successfully!")
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect("product_view", product_id)

    return redirect("product_view", product_id=product.id)

@user_passes_test(is_staff_user)
def edit_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product_id = variant.product.id
    existing_images = ProductImage.objects.filter(product_variant=variant)

    if request.method == "POST":
        name = request.POST.get("name")
        price = request.POST.get("price")
        stock = request.POST.get("stock")
        discount_type = request.POST.get("discount_type")
        discount_value = request.POST.get("discount_value")
        is_discount_active = True

        # Stock validation
        try:
            stock = int(stock)
            if stock < 0:
                messages.error(request, "Stock value must be a non-negative integer.")
                return redirect("edit_variant", variant_id=variant_id)
        except ValueError:
            messages.error(request, "Stock value must be an integer.")
            return redirect("edit_variant", variant_id=variant_id)
        
        # Price validation
        try:
            price = float(price)
            if price < 0:
                messages.error(request, "Price value must be a non-negative integer.")
                return redirect("edit_variant", variant_id=variant_id)
        except ValueError:
            messages.error(request, "Price value must be a number.")
            return redirect("edit_variant", variant_id=variant_id)
        
        if discount_type == "fixed":
            if float(discount_value)>float(price):
                messages.error(request, "Discount value must be less than the price.")
                return redirect("product_view", product_id)
        if discount_type == "percentage":
            if float(discount_value)>100:
                messages.error(request, "Discount value must be less than 100.")
                return redirect("product_view", product_id)

        if discount_type == "none":
            discount_type = None
            discount_value = None
            is_discount_active = False

        if discount_type and discount_value:
            try:
                discount_value = float(discount_value)
                if discount_value <= 0:
                    messages.error(request, "Discount value must be greater than 0.")
                    return redirect("edit_variant", variant_id=variant_id)
            except ValueError:
                messages.error(request, "Invalid discount value.")
                return redirect("edit_variant", variant_id=variant_id)

        if not name or not price:
            messages.error(request, "All fields are required.")
            return redirect("edit_variant", variant_id=variant_id)
        if not is_valid_name(name):
            messages.error(request, "Invalid name. Use only alphabets and spaces.")
            return redirect("edit_variant", variant_id=variant_id)

        try:
            variant.name = name
            variant.price = price
            variant.stock = stock
            variant.discount_type = discount_type
            variant.discount_value = discount_value
            variant.is_discount_active = is_discount_active
            variant.updated_by = request.user
            variant.save()

            # Handle image deletions
            images_to_delete = request.POST.getlist("delete_images")
            images_to_delete_objects = ProductImage.objects.filter(
                id__in=images_to_delete
            )

            # Handle new image uploads
            new_images = request.FILES.getlist("product_images")
            total_images = (
                len(existing_images) - len(images_to_delete) + len(new_images)
            )

            if total_images < 3:
                messages.error(request, "You must have at least 3 images.")
                return redirect("edit_variant", variant_id=variant_id)

            if total_images > 7:
                messages.error(request, "You can have a maximum of 7 images.")
                return redirect("edit_variant", variant_id=variant_id)

            for image in images_to_delete_objects:
                # Delete from Cloudinary
                cloudinary_delete(str(image.image_path).split("/")[-1].split(".")[0])

                image.delete()

            for image in new_images:
                uploaded_image = cloudinary_upload(image)
                ProductImage.objects.create(
                    product_variant=variant, image_path=uploaded_image["secure_url"]
                )

            messages.success(request, "Variant updated successfully!")
            return redirect("product_view", product_id)
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

    context = {
        "variant": variant,
        "existing_images": existing_images,
    }
    return render(request, "manager/edit_variant.html", context)
