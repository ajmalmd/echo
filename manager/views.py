from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from .utils import paginate_items
from .models import *
from store.validators import *
from store.models import *
from datetime import datetime
from django.utils.timezone import localtime
from django.contrib import messages
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.csrf import csrf_exempt 
from cloudinary.uploader import (
    upload as cloudinary_upload,
    destroy as cloudinary_delete,
)
from django.db.models import Avg, Count, F, Q, Value


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
        brands = (
            Brand.objects.filter(name__icontains=search_query)
            .annotate(product_count=Count("products"))
            .order_by("created_at")
        )
    else:
        brands = Brand.objects.annotate(product_count=Count("products")).order_by(
            "created_at"
        )

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
        products = (
            Product.objects.filter(name__icontains=search_query)
            .annotate(variant_count=Count("variants"))
            .order_by("-created_at")
        )
    else:
        products = (
            Product.objects.all()
            .annotate(variant_count=Count("variants"))
            .order_by("-created_at")
        )

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

        if Product.objects.filter(name=name).exists():
            messages.error(request, "Product with this name already exists.")
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

        if Product.objects.filter(name=name).exclude(id=product_id).exists():
            messages.error(request, "Product with this name already exists.")
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
        if stock > 10000:
            messages.error(request, "Max limit of stock is 10000")
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
        if price > 100000:
            messages.error(request, "Max price should under 100000.")
            return redirect("product_view", product_id)
    except ValueError:
        messages.error(request, "Price value must be a number.")
        return redirect("product_view", product_id)

    if discount_type == "fixed":
        if float(discount_value) > float(price):
            messages.error(request, "Discount value must be less than the price.")
            return redirect("product_view", product_id)
    if discount_type == "percentage":
        if float(discount_value) > 100:
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
            if stock > 10000:
                messages.error(request, "Max limit of stock is 10000.")
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
            if price > 100000:
                messages.error(request, "Max price should under 100000.")
                return redirect("edit_variant", variant_id=variant_id)
        except ValueError:
            messages.error(request, "Price value must be a number.")
            return redirect("edit_variant", variant_id=variant_id)

        if discount_type == "fixed":
            if float(discount_value) > float(price):
                messages.error(request, "Discount value must be less than the price.")
                return redirect("product_view", product_id)
        if discount_type == "percentage":
            if float(discount_value) > 100:
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


@user_passes_test(is_staff_user)
def orders(request):
    orders = (
        Order.objects.prefetch_related("items")
        .annotate(total_items=Count("items"))
        .order_by("-created_at")
    )
    page_obj = paginate_items(request, orders, per_page=10)
    context = {"page_obj": page_obj}
    return render(request, "manager/orders.html", context)


@user_passes_test(is_staff_user)
def order_view(request, order_id):
    statuses = {
        "pending": [
            ("confirmed", "Confirmed"),
            ("shipped", "Shipped"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
        ],
        "confirmed": [
            ("shipped", "Shipped"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
        ],
        "shipped": [("delivered", "Delivered"), ("cancelled", "Cancelled")],
        "delivered": [],
        "return_requested": [
            ("return_approved", "Returned"),
            ("return_rejected", "Return Rejected"),
        ],
        "return_approved": [],
        "return_rejected": [],
        "cancelled": [],
    }
    order_items = OrderItem.objects.filter(order=order_id)
    for item in order_items:
        item.allowed_statuses = statuses[item.status]

    if (
        request.method == "POST"
        and request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        item_id = request.POST.get("item_id")
        current_status = order_items.get(id=item_id).status
        new_status = request.POST.get("status")

        if statuses[current_status]:
            if new_status not in [status[0] for status in statuses[current_status]]:
                messages.error(request, "Invalid status.")
                return JsonResponse(
                    {"success": False, "error": "Invalid status"}, status=400
                )
        else:
            messages.error(request, "Invalid status.")
            return JsonResponse(
                {"success": False, "error": "Invalid status"}, status=400
            )

        try:
            order_item = OrderItem.objects.get(id=item_id)
            order_item.status = new_status
            if new_status == "cancelled":
                variant = ProductVariant.objects.get(id=order_item.product_variant.id)
                variant.stock += order_item.quantity
                
                #Refund to customer wallet on cancellation
                if order_item.order.order_payment == 'wallet' or (order_item.order.order_payment == 'razorpay' and order_item.order.razorpay_payment_status == 'paid'):
                    customer_wallet, created = Wallet.objects.get_or_create(user=order_item.order.user.id)
                    WalletTransaction.objects.create(
                        wallet=customer_wallet,
                        amount=order_item.sub_total(),
                        transaction_type='credit',
                        transaction_purpose='refund',
                        description = f"Refund for {order_item}",
                        order=order_item.order
                        )
                    
                variant.save()
            order_item.save()
            messages.success(request, "Order item status updated successfully.")
            return JsonResponse({"success": True})
        except OrderItem.DoesNotExist:
            messages.error(request, "Order item not found.")
            return JsonResponse(
                {"success": False, "error": "Order item not found"}, status=404
            )
    context = {"order_items": order_items, "order_id": order_id, "statuses": statuses}
    return render(request, "manager/order_view.html", context)


@user_passes_test(is_staff_user)
@require_http_methods(["GET", "POST"])
def offers(request):
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        data = request.POST

        # Field validations
        name = data.get('name')
        description = data.get('description')
        offer_type = data.get('offer_type')
        discount_type = data.get('discount_type')
        discount_value = data.get('discount_value')
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if not all([name, description, offer_type, discount_type, discount_value, start_date, end_date]):
            return JsonResponse({"success": False, "message": "All fields are required."})

        if discount_type not in ["fixed", "percentage"]:
            return JsonResponse({"success": False, "message": "Invalid discount type. Must be 'fixed' or 'percentage'."})
        
        try:
            validate_product_name(name)
        except ValidationError as e:
            return JsonResponse({"success": False, "message": str(e)})

        if Offer.objects.filter(Q(start_date__lte=end_date, end_date__gte=start_date), name=name).exists():
            return JsonResponse({"success": False, "message": "An offer with this name and overlapping period already exists."})

        try:
            discount_value = Decimal(discount_value)
            if discount_type == "percentage" and (discount_value < 0 or discount_value > 100):
                return JsonResponse({"success": False, "message": "Percentage discount must be between 0 and 100."})
        except (ValueError, Decimal.InvalidOperation):
            return JsonResponse({"success": False, "message": "Invalid discount value."})

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            today = now().date()

            if start_date < today:
                return JsonResponse({"success": False, "message": "Start date must be today or later."})
            if end_date < start_date:
                return JsonResponse({"success": False, "message": "End date must be after the start date."})
        except ValueError:
            return JsonResponse({"success": False, "message": "Invalid date format. Use YYYY-MM-DD."})

        offer = Offer(
            name=name,
            description=description,
            offer_type=offer_type,
            discount_type=discount_type,
            discount_value=discount_value,
            start_date=start_date,
            end_date=end_date,
        )

        if offer.offer_type == 'product':
            offer.product_id = data.get('product')
        elif offer.offer_type == 'brand':
            offer.brand_id = data.get('brand')

        try:
            offer.save()
            messages.success(request, "Offer added successfully.")
            return JsonResponse({"success": True, "message": "Offer added successfully."})
        except ValidationError as e:
            return JsonResponse({"success": False, "message": str(e)})

    products = Product.objects.filter(is_active=True, brand__is_active=True)
    brands = Brand.objects.filter(is_active=True)
    offers = Offer.objects.all().order_by('-created_at')
    page_obj = paginate_items(request, offers, per_page=10)
    context = {
        "brands": brands,
        "products": products,
        "page_obj": page_obj
    }
    return render(request, "manager/offers.html", context)


@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def edit_offer(request):
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        data = request.POST

        offer_id = data.get('offer_id')
        name = data.get('name')
        description = data.get('description')
        offer_type = data.get('offer_type')
        discount_type = data.get('discount_type')
        discount_value = data.get('discount_value')
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        offer = get_object_or_404(Offer, id=offer_id)

        # Validate mandatory fields
        if not all([name, description, offer_type, discount_type, discount_value, start_date, end_date]):
            return JsonResponse({"success": False, "message": "All fields are required."})

        # Validate discount type
        if discount_type not in ["fixed", "percentage"]:
            return JsonResponse({"success": False, "message": "Invalid discount type. Must be 'fixed' or 'percentage'."})
        
        try:
            validate_product_name(name)
        except ValidationError as e:
            return JsonResponse({"success": False, "message": str(e)})

        # Check if a different offer already has this name
        if Offer.objects.filter(Q(start_date__lte=end_date, end_date__gte=start_date), name=name).exclude(id=offer_id).exists():
            return JsonResponse({"success": False, "message": "An offer with this name and overlapping period already exists."})

        # Validate discount value
        try:
            discount_value = Decimal(discount_value)
            if discount_type == "percentage" and (discount_value < 0 or discount_value > 100):
                return JsonResponse({"success": False, "message": "Percentage discount must be between 0 and 100."})
        except (ValueError, Decimal.InvalidOperation):
            return JsonResponse({"success": False, "message": "Invalid discount value."})

        # Validate start and end dates
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            today = now().date()  # Convert to date for consistent comparison

            # Determine valid range for start date based on existing start date
            if offer.start_date < today:
                # Existing start date is before today
                if start_date < today or start_date > end_date:
                    return JsonResponse({
                        "success": False,
                        "message": "Start date must be between today and the end date."
                    })
            else:
                # Existing start date is today or later
                if start_date < offer.start_date or start_date > end_date:
                    return JsonResponse({
                        "success": False,
                        "message": f"Start date must be between {offer.start_date} and the end date."
                    })

            # Ensure end date is valid
            if end_date < start_date:
                return JsonResponse({
                    "success": False,
                    "message": "End date must be after the start date."
                })
        except ValueError:
            return JsonResponse({"success": False, "message": "Invalid date format. Use YYYY-MM-DD."})


        offer.name = name
        offer.description = description
        offer.offer_type = offer_type
        offer.discount_type = discount_type
        offer.discount_value = discount_value
        offer.start_date = start_date
        offer.end_date = end_date

        if offer.offer_type == 'product':
            offer.product_id = data.get('product')
            offer.brand = None
        elif offer.offer_type == 'brand':
            offer.brand_id = data.get('brand')
            offer.product = None

        try:
            offer.save()
            messages.success(request, "Offer updated successfully.")
            return JsonResponse({"success": True, "message": "Offer updated successfully."})
        except ValidationError as e:
            return JsonResponse({"success": False, "message": str(e)})

    return JsonResponse({"success": False, "message": "Invalid request method"})

@require_http_methods(["POST"])
@csrf_exempt
def get_offer_details(request):
    data = json.loads(request.body)
    offer_id=data.get('offer_id')
    offer = get_object_or_404(Offer, id=offer_id)

    data = {
        "id": offer.id,
        "name": offer.name,
        "description": offer.description,
        "offer_type": offer.offer_type,
        "discount_type": offer.discount_type,
        "discount_value": str(offer.discount_value),
        "start_date": localtime(offer.start_date).strftime('%Y-%m-%d'),
        "end_date": localtime(offer.end_date).strftime('%Y-%m-%d'),
        "is_active": offer.is_active,
    }

    if offer.offer_type == 'product':
        data['product_id'] = offer.product_id
    elif offer.offer_type == 'brand':
        data['brand_id'] = offer.brand_id

    return JsonResponse(data)

@user_passes_test(is_staff_user)
@csrf_exempt
def toggle_offer_status(request):
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        data = json.loads(request.body)
        offer_id = data.get('offer_id')
        offer = get_object_or_404(Offer, id=offer_id)
        offer.is_active = not offer.is_active
        offer.save()
        return JsonResponse({"success": True, "offer_status": f"{'active' if offer.is_active else 'inactive'}", "message": f"Offer status changed to {'active' if offer.is_active else 'inactive'}."})
    else:
        return JsonResponse({"success": False, "message": "Invalid Request."})


@login_required(login_url="admin_login")
@user_passes_test(is_staff_user)
@never_cache
def coupons(request):
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        data = request.POST

        # Field validations
        code = data.get('code')
        description = data.get('description')
        discount_type = data.get('discount_type')
        discount_value = data.get('discount_value')
        min_purchase_amount = data.get('min_purchase')
        max_discount_amount = data.get('max_discount')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        usage_limit = data.get('usage_limit')

        if not all([code, description, discount_type, discount_value, min_purchase_amount, start_date, end_date, usage_limit]):
            return JsonResponse({"success": False, "message": "All fields are required."})

        if discount_type not in ["fixed", "percentage"]:
            return JsonResponse({"success": False, "message": "Invalid discount type. Must be 'fixed' or 'percentage'."})

        if Coupon.objects.filter(code=code).exists():
            return JsonResponse({"success": False, "message": "A coupon with this code already exists."})

        if not usage_limit or int(usage_limit) < 1:
            return JsonResponse({"success": False, "message": "Usage limit must be at least 1."})

        try:
            discount_value = Decimal(discount_value)
            min_purchase_amount = Decimal(min_purchase_amount)
            max_discount_amount = Decimal(max_discount_amount) if max_discount_amount else None

            if discount_type == "percentage" and (discount_value < 0 or discount_value > 100):
                return JsonResponse({"success": False, "message": "Percentage discount must be between 0 and 100."})
            if min_purchase_amount < 0:
                return JsonResponse({"success": False, "message": "Minimum purchase amount cannot be negative."})
            if max_discount_amount and max_discount_amount < 0:
                return JsonResponse({"success": False, "message": "Maximum discount amount cannot be negative."})
        except (ValueError, Decimal.InvalidOperation):
            return JsonResponse({"success": False, "message": "Invalid numeric value."})

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            today = now().date()

            if start_date < today:
                return JsonResponse({"success": False, "message": "Start date must be today or later."})
            if end_date < start_date:
                return JsonResponse({"success": False, "message": "End date must be after the start date."})
        except ValueError:
            return JsonResponse({"success": False, "message": "Invalid date format. Use YYYY-MM-DD."})

        coupon = Coupon(
            code=code,
            description=description,
            discount_type=discount_type,
            discount_value=discount_value,
            min_purchase_amount=min_purchase_amount,
            max_discount_amount=max_discount_amount,
            start_date=start_date,
            end_date=end_date,
            usage_limit=usage_limit,
        )

        try:
            coupon.save()
            messages.success(request, "Coupon added successfully.")
            return JsonResponse({"success": True, "message": "Coupon added successfully."})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})

    coupons = Coupon.objects.all().order_by('-created_at')
    page_obj = paginate_items(request, coupons, per_page=10)
    context = {
        "page_obj": page_obj
    }
    return render(request, "manager/coupons.html", context)

@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def edit_coupon(request):
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        data = request.POST

        coupon_id = data.get('coupon_id')
        code = data.get('code')
        description = data.get('description')
        discount_type = data.get('discount_type')
        discount_value = data.get('discount_value')
        min_purchase_amount = data.get('min_purchase')
        max_discount_amount = data.get('max_discount')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        usage_limit = data.get('usage_limit')

        coupon = get_object_or_404(Coupon, id=coupon_id)

        if not all([code, description, discount_type, discount_value, min_purchase_amount, start_date, end_date, usage_limit]):
            return JsonResponse({"success": False, "message": "All fields are required."})

        if discount_type not in ["fixed", "percentage"]:
            return JsonResponse({"success": False, "message": "Invalid discount type. Must be 'fixed' or 'percentage'."})

        if Coupon.objects.filter(code=code).exclude(id=coupon_id).exists():
            return JsonResponse({"success": False, "message": "A coupon with this code already exists."})

        if not usage_limit or int(usage_limit) < 1:
            return JsonResponse({"success": False, "message": "Usage limit must be at least 1."})

        try:
            discount_value = Decimal(discount_value)
            min_purchase_amount = Decimal(min_purchase_amount)
            max_discount_amount = Decimal(max_discount_amount) if max_discount_amount else None

            if discount_type == "percentage":
                if not max_discount_amount:
                    return JsonResponse({"success": False, "message": "Max discount amount is required for percentage discounts."})
            else:
                max_discount_amount = None

            if discount_type == "percentage" and (discount_value < 0 or discount_value > 100):
                return JsonResponse({"success": False, "message": "Percentage discount must be between 0 and 100."})
            if min_purchase_amount < 0:
                return JsonResponse({"success": False, "message": "Minimum purchase amount cannot be negative."})
            if max_discount_amount and max_discount_amount < 0:
                return JsonResponse({"success": False, "message": "Maximum discount amount cannot be negative."})
        except (ValueError, Decimal.InvalidOperation):
            return JsonResponse({"success": False, "message": "Invalid numeric value."})

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            today = now().date()

            if coupon.start_date <= today:
                if start_date != coupon.start_date:
                    return JsonResponse({"success": False, "message": "Cannot change start date for an active or past coupon."})
            else:
                if start_date < today:
                    return JsonResponse({"success": False, "message": "Start date must be today or later."})

            if end_date < start_date:
                return JsonResponse({"success": False, "message": "End date must be after the start date."})
        except ValueError:
            return JsonResponse({"success": False, "message": "Invalid date format. Use YYYY-MM-DD."})

        coupon.code = code
        coupon.description = description
        coupon.discount_type = discount_type
        coupon.discount_value = discount_value
        coupon.min_purchase_amount = min_purchase_amount
        coupon.max_discount_amount = max_discount_amount
        coupon.start_date = start_date
        coupon.end_date = end_date
        coupon.usage_limit = usage_limit

        try:
            coupon.save()
            messages.success(request, "Coupon updated successfully.")
            return JsonResponse({"success": True, "message": "Coupon updated successfully."})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})

    return JsonResponse({"success": False, "message": "Invalid request method"})

@user_passes_test(is_staff_user)
def toggle_coupon_status(request):
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        data = json.loads(request.body)
        coupon_id = data.get('coupon_id')
        coupon = get_object_or_404(Coupon, id=coupon_id)
        coupon.is_active = not coupon.is_active
        coupon.save()
        return JsonResponse({
            "success": True,
            "coupon_status": 'active' if coupon.is_active else 'inactive',
            "message": f"Coupon status changed to {'active' if coupon.is_active else 'inactive'}."
        })
    else:
        return JsonResponse({"success": False, "message": "Invalid Request."})

@require_http_methods(["POST"])
def get_coupon_details(request):
    data = json.loads(request.body)
    coupon_id = data.get('coupon_id')
    coupon = get_object_or_404(Coupon, id=coupon_id)

    data = {
        "id": coupon.id,
        "code": coupon.code,
        "description": coupon.description,
        "discount_type": coupon.discount_type,
        "discount_value": str(coupon.discount_value),
        "min_purchase_amount": str(coupon.min_purchase_amount),
        "max_discount_amount": str(coupon.max_discount_amount) if coupon.max_discount_amount else None,
        "start_date": coupon.start_date.strftime('%Y-%m-%d'),
        "end_date": coupon.end_date.strftime('%Y-%m-%d'),
        "is_active": coupon.is_active,
        "usage_limit": coupon.usage_limit,
    }

    return JsonResponse(data)