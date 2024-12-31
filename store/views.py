from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import *
from manager.models import *
from .services import generate_otp, send_otp_email, get_new_arrivals
from .validators import *
from django.contrib.auth.decorators import user_passes_test
from django.utils.timezone import now, timedelta
from datetime import datetime
from django.views.decorators.cache import never_cache
from django.db.models import Avg, Count, F, Q, Value
from django.db.models.functions import Concat
import json
from django.http import JsonResponse


def is_customer(user):
    return user.is_authenticated and not user.is_staff


@never_cache
def user_login(request):

    next_url = request.GET.get("next", "home")

    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)

        if user:
            if user.is_active and not user.is_staff:
                login(request, user)
                return redirect(next_url)
            else:
                # User is inactive
                messages.error(request, "No permission for staffs")
        else:
            # If authentication fails, check if user exists
            try:
                user = User.objects.get(email=email)
                if not user.is_active:
                    messages.error(
                        request, "Your account is inactive. Please contact support."
                    )
                else:
                    messages.error(request, "Invalid email or password.")
            except User.DoesNotExist:
                messages.error(request, "Invalid email or password.")

    return render(request, "store/login.html")


@never_cache
def user_signup(request):

    next_url = request.GET.get("next", "home")

    if request.user.is_authenticated:
        return redirect(next_url)

    if request.method == "POST":
        fullname = request.POST.get("fullname", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        if User.objects.filter(email=email).exists():
            messages.error(request, "User already exists")
            return redirect("login")

        # Perform validations
        if not is_valid_email(email):
            messages.error(request, "Invalid email address.")
            return render(request, "store/signup.html", {"fullname": fullname})

        if not is_valid_name(fullname):
            messages.error(request, "Invalid name. Use only alphabets and spaces.")
            return render(request, "store/signup.html", {"email": email})

        if not is_valid_password(password):
            messages.error(
                request,
                "Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, a digit, and a special character.",
            )
            return render(
                request, "store/signup.html", {"fullname": fullname, "email": email}
            )

        # Check if the same email is already in session
        session_email = request.session.get("user_signup_data", {}).get("email")
        if session_email and session_email == email:
            messages.info(
                request, "OTP has already been sent to this email. Please verify."
            )
            return redirect("verify_otp")

        # Generate OTP
        otp = generate_otp()

        # Fetch or create an OTP record for the email
        otp_record, created = OTP.objects.get_or_create(email=email)

        # Check resend limit
        if otp_record.resend_count >= 3:
            time_since_first_resend = now() - otp_record.created_at
            if time_since_first_resend <= timedelta(hours=4):
                messages.error(
                    request,
                    "Resend limit exceeded. Try again later.",
                )
                return redirect("signup")
            else:
                otp_record.resend_count = 0  # Reset resend count after 4 hours

        # Send OTP and update the OTP record
        send_otp_email(email, otp)

        otp_record.otp = otp
        otp_record.created_at = now()
        otp_record.resend_count += 1
        otp_record.save()

        # Save OTP sending time in session
        request.session["otp_sent_time"] = datetime.now().isoformat()

        # Temporarily store user data in session for verification
        request.session["user_signup_data"] = {
            "email": email,
            "fullname": fullname,
            "password": password,
        }

        messages.success(request, "OTP sent to your email. Please verify.")
        return redirect("verify_otp")

    return render(request, "store/signup.html")


@never_cache
def verify_otp(request):
    next_url = request.GET.get("next", "home")

    if request.user.is_authenticated:
        return redirect(next_url)

    # Check if the OTP session data exists
    session_key = (
        "user_signup_data"
        if "user_signup_data" in request.session
        else "user_forgot_password_data"
    )
    user_data = request.session.get(session_key, None)

    if not user_data:
        messages.error(request, "No session data found. Please try again.")
        return redirect(
            "signup" if session_key == "user_signup_data" else "forgot_password"
        )

    if request.method == "POST":
        # Combine OTP from individual inputs
        otp = "".join([request.POST.get(f"otp{i+1}", "").strip() for i in range(6)])

        email = user_data["email"]

        # Validate the OTP
        try:
            otp_record = OTP.objects.get(email=email)

            if otp_record.otp != otp:
                messages.error(request, "Invalid OTP.")
                return render(request, "store/verify_otp.html")

            if (now() - otp_record.created_at).total_seconds() > 120:  # 2 minutes
                messages.error(request, "OTP has expired.")
                return render(request, "store/verify_otp.html")

        except OTP.DoesNotExist:
            messages.error(request, "No OTP record found. Please try again.")
            return redirect(
                "signup" if session_key == "user_signup_data" else "forgot_password"
            )

        # OTP is valid
        if session_key == "user_signup_data":
            # Create the user for signup flow
            User.objects.create_user(
                email=email,
                password=user_data["password"],
                fullname=user_data["fullname"],
            )

            # Authenticate and log in the user
            user = authenticate(request, email=email, password=user_data["password"])
            login(request, user)

            messages.success(request, "Your account has been created and verified.")
        else:
            # Redirect to reset password flow for forgot password
            request.session["reset_password_email"] = email
            messages.success(request, "OTP verified. You can now reset your password.")
            return redirect("reset_password")

        # Clean up session and OTP record
        del request.session[session_key]
        del request.session["otp_sent_time"]
        otp_record.delete()

        return redirect("home")

    elif request.method == "GET" and request.GET.get("resend", None) == "true":
        # Resend OTP logic
        otp_sent_time = request.session.get("otp_sent_time")
        if otp_sent_time:
            otp_sent_time = datetime.fromisoformat(otp_sent_time)
            time_since_last_otp = datetime.now() - otp_sent_time

            if time_since_last_otp < timedelta(seconds=59):  # 59 seconds
                messages.error(request, "You must wait before resending the OTP.")
                return redirect("verify_otp")

        try:
            otp_record = OTP.objects.get(email=user_data["email"])

            if otp_record.resend_count >= 3:
                time_since_first_resend = now() - otp_record.created_at

                if time_since_first_resend <= timedelta(hours=4):
                    messages.error(request, "Resend limit exceeded. Try again later.")
                    return redirect(
                        "signup"
                        if session_key == "user_signup_data"
                        else "forgot_password"
                    )

                else:
                    otp_record.resend_count = 0  # Reset resend count after 4 hours

            # Generate and send new OTP
            otp = generate_otp()
            otp_record.otp = otp
            otp_record.created_at = now()
            otp_record.resend_count += 1
            otp_record.save()

            send_otp_email(user_data["email"], otp)

            # Update the session with the new OTP sending time
            request.session["otp_sent_time"] = datetime.now().isoformat()

            messages.success(request, "OTP has been resent.")

        except OTP.DoesNotExist:
            messages.error(request, "No OTP record found. Please try again.")
            return redirect(
                "signup" if session_key == "user_signup_data" else "forgot_password"
            )

    return render(request, "store/verify_otp.html")


def user_logout(request):
    logout(request)
    return redirect("home")


@never_cache
def forgot_password(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()

        if not is_valid_email(email):
            messages.error(request, "Invalid email address.")
            return redirect("forgot_password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "No user found with this email.")
            return redirect("forgot_password")

        # Check if the same email is already in session
        session_email = request.session.get("user_forgot_password_data", {}).get(
            "email"
        )
        if session_email and session_email == email:
            messages.info(
                request, "OTP has already been sent to this email. Please verify."
            )
            return redirect("verify_otp")

        # Generate OTP
        otp = generate_otp()

        # Fetch or create an OTP record for the email
        otp_record, created = OTP.objects.get_or_create(email=email)

        # Check resend limit
        if otp_record.resend_count >= 3:
            time_since_first_resend = now() - otp_record.created_at
            if time_since_first_resend <= timedelta(hours=1):
                messages.error(
                    request,
                    "Resend limit exceeded. Try again later.",
                )
                return redirect("forgot_password")
            else:
                otp_record.resend_count = 0

        # Send OTP and update the OTP record
        send_otp_email(email, otp)

        otp_record.otp = otp
        otp_record.created_at = now()
        otp_record.resend_count += 1
        otp_record.save()

        # Save OTP sending time in session
        request.session["otp_sent_time"] = datetime.now().isoformat()

        # Temporarily store user data in session for verification
        request.session["user_forgot_password_data"] = {
            "email": email,
        }

        messages.success(request, "OTP sent to your email. Please verify.")
        return redirect("verify_otp")

    return render(request, "store/forgot_password.html")


@never_cache
def reset_password(request):

    if request.user.is_authenticated:
        return redirect("home")
    user_data = request.session.get("user_forgot_password_data", None)
    email = user_data["email"]

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if not is_valid_password(password):
            messages.error(
                request,
                "Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, a digit, and a special character.",
            )
            return redirect("reset_password")
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("reset_password")

        user = User.objects.get(email=email)
        user.set_password(password)
        user.save()
        otp_record = OTP.objects.get(email=email)

        # Clean up session and OTP record
        del request.session["user_forgot_password_data"]
        del request.session["otp_sent_time"]
        otp_record.delete()
        return redirect("login")
    return render(request, "store/reset_password.html")


# @user_passes_test(is_customer)
def home(request):
    new_arrivals = get_new_arrivals(6)

    return render(request, "store/home.html", {"new_arrivals": new_arrivals})


def products_listing(request):
    brands = Brand.objects.filter(is_active=True)

    sort_by = request.GET.get("sort", "featured")  # Default to 'featured'
    search_query = request.GET.get("search", "")  # Get the search query

    products = (
        ProductVariant.objects.filter(
            is_active=True,
            product__is_active=True,
            product__brand__is_active=True,
        )
        .select_related("product")
        .prefetch_related("images")
        .annotate(
            product_name=Concat(F("product__name"), Value(" - "), F("name")),
            brand_name=F("product__brand__name"),
            avg_rating=Avg("product__reviews__rating"),
            review_count=Count("product__reviews"),
        )
    )

    # Apply search filter
    if search_query:
        products = products.filter(
            Q(product_name__icontains=search_query)
            | Q(brand_name__icontains=search_query)
            | Q(product__description__icontains=search_query)
        )

    # Apply sorting
    if sort_by == "popularity":
        products = products.annotate(popularity=Count("order_items")).order_by(
            "-popularity"
        )
    elif sort_by == "price_low_high":
        products = sorted(products, key=lambda p: p.discounted_price())
    elif sort_by == "price_high_low":
        products = sorted(products, key=lambda p: p.discounted_price(), reverse=True)
    elif sort_by == "avg_rating":
        products = products.order_by("-avg_rating")
    elif sort_by == "new_arrivals":
        products = products.order_by("-product__created_at")
    elif sort_by == "name_asc":
        products = products.order_by("product_name")
    elif sort_by == "name_desc":
        products = products.order_by("-product_name")
    else:  # 'featured' or default - featuring products with higher stock
        products = products.order_by("-stock")

    return render(
        request,
        "store/products_list.html",
        {
            "brands": brands,
            "productModel": Product,
            "products": products,
            "current_sort": sort_by,
            "search_query": search_query,
        },
    )


def view_variant(request, variant_id):

    variant = get_object_or_404(ProductVariant, id=variant_id)
    discounted_price = variant.discounted_price()
    product = variant.product
    brand = product.brand
    other_variants = product.variants.exclude(id=variant_id)
    variant_images = variant.images.all()
    rating = {"rating": 4.5, "count": 100}
    similar_variants = variant.get_similar_variants()

    context = {
        "variant": variant,
        "discounted_price": discounted_price,
        "product": product,
        "brand": brand,
        "other_variants": other_variants,
        "variant_images": variant_images,
        "rating": rating,
        "similar_variants": similar_variants,
    }

    return render(request, "store/variant_view.html", context)


@login_required(login_url="login")
@user_passes_test(is_customer)
def addresses(request):

    default_address = request.user.addresses.filter(is_default=True).first()
    saved_addresses = request.user.addresses.filter(is_default=False)

    if request.method == "POST":

        # make default address
        address_id = request.POST.get("set_default")
        if address_id:
            try:
                address = request.user.addresses.get(id=address_id)
                # Reset all addresses to non-default
                request.user.addresses.update(is_default=False)
                # Set the selected address as default
                address.is_default = True
                address.save()
                messages.success(request, "Default address updated successfully.")
            except Address.DoesNotExist:
                messages.error(request, "Address not found.")
            return redirect("addresses")

        # delete address
        address_id = request.POST.get("delete")
        if address_id:
            try:
                address = request.user.addresses.get(id=address_id)
                address.delete()
                messages.success(request, "Address deleted successfully.")
            except Address.DoesNotExist:
                messages.error(request, "Address not found.")
            return redirect("addresses")

        name = request.POST.get("name")
        phone = request.POST.get("phone")
        address_line_1 = request.POST.get("address_line_1")
        address_line_2 = request.POST.get("address_line_2")
        city = request.POST.get("city")
        state = request.POST.get("state")
        postal_code = request.POST.get("postal_code")
        country = request.POST.get("country")
        is_default = request.POST.get("is_default")

        # validations
        if not is_valid_name(name):
            messages.error(request, "Invalid name. Use only alphabets and spaces.")
            return redirect("addresses")

        if not is_valid_phone(phone):
            messages.error(request, "Invalid phone number.")
            return redirect("addresses")

        if not is_valid_name(city):
            messages.error(request, "Invalid city name.")
            return redirect("addresses")

        if not is_valid_name(state):
            messages.error(request, "Invalid state name.")
            return redirect("addresses")

        if not is_valid_postalcode(postal_code):
            messages.error(request, "Invalid postal code.")
            return redirect("addresses")

        if not is_valid_name(country):
            messages.error(request, "Invalid country name.")
            return redirect("addresses")

        # edit address
        address_id = request.POST.get("edit")
        if address_id:
            try:
                address = request.user.addresses.get(id=address_id)
                address.name = name
                address.contact = phone
                address.address_line_1 = address_line_1
                address.address_line_2 = address_line_2
                address.city = city
                address.state = state
                address.postal_code = postal_code
                address.country = country
                address.save()
                messages.success(request, "Address updated successfully.")
            except Address.DoesNotExist:
                messages.error(request, "Address not found.")
            return redirect("addresses")

        # add new address
        if is_default == "on":
            is_default = True
        else:
            is_default = False

        new_address = Address(
            user=request.user,
            name=name,
            contact=phone,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            city=city,
            state=state,
            postal_code=postal_code,
            is_default=is_default,
        )
        new_address.save()
        messages.success(request, "Address added successfully.")
        return redirect("addresses")
    return render(
        request,
        "store/addresses.html",
        {"default_address": default_address, "saved_addresses": saved_addresses},
    )


@login_required(login_url="login")
@user_passes_test(is_customer)
def cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related(
        "product_variant", "product_variant__product"
    ).all()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if request.method == "POST":
            action = request.POST.get("action")
            variant_id = request.POST.get("variant_id")
            quantity = int(request.POST.get("quantity", 1))

            variant = ProductVariant.objects.get(id=variant_id)
            max_qty = min(variant.stock, 3)

            if action == "add":
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart, product_variant=variant
                )
                if not created:
                    cart_item.quantity = min(cart_item.quantity + quantity, max_qty)
                cart_item.save()
                message = "Item added to cart successfully"

            elif action == "update":
                cart_item = CartItem.objects.get(cart=cart, product_variant=variant)
                cart_item.quantity = min(quantity, max_qty)
                cart_item.save()
                message = "Quantity updated successfully"

            elif action == "remove":
                CartItem.objects.filter(cart=cart, product_variant=variant).delete()
                message = "Item removed from cart successfully"

            total_mrp = round(cart.total_price(), 2)
            total_discounted = round(cart.total_discounted_price(), 2)
            return JsonResponse(
                {
                    "success": True,
                    "message": message,
                    "total": total_discounted,
                    "total_mrp": total_mrp,
                    "total_discount": total_mrp - total_discounted,
                    "item_count": cart.items.count(),
                    "max_qty": max_qty,
                    "item_price": variant.discounted_price(),
                    "item_old_price": variant.price,
                    "item_discount_type": variant.discount_type,
                    "item_discount_value": variant.discount_value,
                }
            )

    total_mrp = round(cart.total_price(), 2)
    total_discounted = round(cart.total_discounted_price(), 2)
    context = {
        "cart_items": cart_items,
        "total": total_discounted,
        "total_mrp": total_mrp,
        "total_discount": total_mrp - total_discounted,
    }
    return render(request, "store/cart.html", context)


@login_required(login_url="login")
@user_passes_test(is_customer)
def add_to_cart(request):
    if (
        request.method == "POST"
        and request.headers.get("x-requested-with") == "XMLHttpRequest"
    ):
        data = json.loads(request.body)  # Parse JSON data
        variant_id = data.get("variant_id")
        variant = get_object_or_404(ProductVariant, id=variant_id)
        max_qty = min(variant.stock, 3)
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart, product_variant=variant
        )

        if max_qty == 0:
            return JsonResponse(
                {"success": False, "message": "This product is out of stock"},
                status=400,
            )

        if cart_item.quantity >= max_qty:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"You can only add up to {max_qty} units of this product",
                },
                status=400,
            )

        if not item_created:
            cart_item.quantity += 1
            cart_item.save()

        cart_item_count = cart.items.count()

        if cart_item.quantity >= 2:
            return JsonResponse(
                {
                    "success": True,
                    "message": "You have this item in your cart, We have increased the quantity by 1",
                    "cart_item_count": cart_item_count,
                }
            )

        return JsonResponse(
            {
                "success": True,
                "message": "Item added to cart successfully",
                "cart_item_count": cart_item_count,
            }
        )

    return JsonResponse({"success": False, "message": "Invalid request"}, status=400)


# select address to order
@login_required(login_url="login")
@user_passes_test(is_customer)
def select_address(request):
    default_address = request.user.addresses.filter(is_default=True).first()
    saved_addresses = request.user.addresses.filter(is_default=False)
    cart = Cart.objects.get(user=request.user)
    total_mrp = round(cart.total_price(), 2)
    total_discounted = round(cart.total_discounted_price(), 2)

    if request.method == "POST":

        # make default address
        address_id = request.POST.get("set_default")
        if address_id:
            try:
                address = request.user.addresses.get(id=address_id)
                # Reset all addresses to non-default
                request.user.addresses.update(is_default=False)
                # Set the selected address as default
                address.is_default = True
                address.save()
                messages.success(request, "Default address updated successfully.")
            except Address.DoesNotExist:
                messages.error(request, "Address not found.")
            return redirect("checkout_address")

        # delete address
        address_id = request.POST.get("delete")
        if address_id:
            try:
                address = request.user.addresses.get(id=address_id)
                address.delete()
                messages.success(request, "Address deleted successfully.")
            except Address.DoesNotExist:
                messages.error(request, "Address not found.")
            return redirect("checkout_address")

        name = request.POST.get("name")
        phone = request.POST.get("phone")
        address_line_1 = request.POST.get("address_line_1")
        address_line_2 = request.POST.get("address_line_2")
        city = request.POST.get("city")
        state = request.POST.get("state")
        postal_code = request.POST.get("postal_code")
        country = request.POST.get("country")
        is_default = request.POST.get("is_default")

        # validations
        if not is_valid_name(name):
            messages.error(request, "Invalid name. Use only alphabets and spaces.")
            return redirect("checkout_address")

        if not is_valid_phone(phone):
            messages.error(request, "Invalid phone number.")
            return redirect("checkout_address")

        if not is_valid_name(city):
            messages.error(request, "Invalid city name.")
            return redirect("checkout_address")

        if not is_valid_name(state):
            messages.error(request, "Invalid state name.")
            return redirect("checkout_address")

        if not is_valid_postalcode(postal_code):
            messages.error(request, "Invalid postal code.")
            return redirect("checkout_address")

        if not is_valid_name(country):
            messages.error(request, "Invalid country name.")
            return redirect("checkout_address")

        # edit address
        address_id = request.POST.get("edit")
        if address_id:
            try:
                address = request.user.addresses.get(id=address_id)
                address.name = name
                address.contact = phone
                address.address_line_1 = address_line_1
                address.address_line_2 = address_line_2
                address.city = city
                address.state = state
                address.postal_code = postal_code
                address.country = country
                address.save()
                messages.success(request, "Address updated successfully.")
            except Address.DoesNotExist:
                messages.error(request, "Address not found.")
            return redirect("checkout_address")

        # add new address
        if is_default == "on":
            is_default = True
        else:
            is_default = False

        new_address = Address(
            user=request.user,
            name=name,
            contact=phone,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            city=city,
            state=state,
            postal_code=postal_code,
            is_default=is_default,
        )
        new_address.save()
        messages.success(request, "Address added successfully.")
        return redirect("checkout_address")
    return render(
        request,
        "store/select_address.html",
        {
            "default_address": default_address,
            "saved_addresses": saved_addresses,
            "total_mrp": total_mrp,
            "total_discount": total_mrp - total_discounted,
        },
    )
