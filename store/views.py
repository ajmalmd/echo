from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import *
from manager.models import *
from .services import generate_otp, send_otp_email, get_new_arrivals
from .validators import *
from django.utils.timezone import now, timedelta
from datetime import datetime, date
from django.views.decorators.cache import never_cache
from django.db.models import Avg, Count, F, Q, Value
from django.db.models.functions import Concat
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import check_password
from django.views.decorators.csrf import csrf_exempt 
from django.conf import settings
import razorpay


def is_customer(user):
    return user.is_authenticated and not user.is_staff

#decorator for preventing non customers to access pages
def customer_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not is_customer(request.user):
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return wrapper


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


def home(request):
    new_arrivals = get_new_arrivals(6)

    return render(request, "store/home.html", {"new_arrivals": new_arrivals})


def products_listing(request):
    brands = Brand.objects.filter(is_active=True)

    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Get filter and sort parameters from POST data
        brand_filter = request.POST.getlist("brand")
        type_filter = request.POST.getlist("type")
        connectivity_filter = request.POST.getlist("connectivity")
        sort_by = request.POST.get("sort", "featured")
        
        # Store filter and sort parameters in session
        request.session['brand_filter'] = brand_filter
        request.session['type_filter'] = type_filter
        request.session['connectivity_filter'] = connectivity_filter
        request.session['sort_by'] = sort_by
        
        return JsonResponse({'reload': True})

    # Get filter and sort parameters from session or GET parameters
    brand_filter = request.session.get('brand_filter') or request.GET.getlist("brand")
    type_filter = request.session.get('type_filter') or request.GET.getlist("type")
    connectivity_filter = request.session.get('connectivity_filter') or request.GET.getlist("connectivity")
    sort_by = request.session.get('sort_by') or request.GET.get("sort", "featured")
    search_query = request.GET.get("search", "")

    # Clear session variables
    request.session.pop('brand_filter', None)
    request.session.pop('type_filter', None)
    request.session.pop('connectivity_filter', None)
    request.session.pop('sort_by', None)

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

    # Apply brand filter
    if brand_filter:
        products = products.filter(product__brand__id__in=brand_filter)

    # Apply type filter
    if type_filter:
        products = products.filter(product__type__in=type_filter)

    # Apply connectivity filter
    if connectivity_filter:
        products = products.filter(product__connectivity__in=connectivity_filter)

    # Apply sorting
    if sort_by == "popularity":
        products = products.annotate(popularity=Count("order_items")).order_by("-popularity")
    elif sort_by == "price_low_high":
        products = products.order_by("price")
    elif sort_by == "price_high_low":
        products = products.order_by("-price")
    elif sort_by == "avg_rating":
        products = products.order_by("-avg_rating")
    elif sort_by == "new_arrivals":
        products = products.order_by("-product__created_at")
    elif sort_by == "name_asc":
        products = products.order_by("product_name")
    elif sort_by == "name_desc":
        products = products.order_by("-product_name")
    else:  # 'featured' or default
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
            "brand_filter": brand_filter,
            "type_filter": type_filter,
            "connectivity_filter": connectivity_filter
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
@customer_required
def profile(request):
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if request.method == "POST":
            user = request.user
            errors = {}

            # Validate fullname
            fullname = request.POST.get("fullname", "").strip()
            if not fullname:
                errors["fullname"] = "Full name is required."
            elif len(fullname) > 25:
                errors["fullname"] = "Full name must be 25 characters or less."

            # Validate mobile number
            mobile_number = request.POST.get("mobile_number", "").strip()
            if mobile_number and not mobile_number.isdigit():
                errors["mobile_number"] = "Mobile number must contain only digits."
            elif len(mobile_number) > 15:
                errors["mobile_number"] = "Mobile number must be 15 digits or less."

            # Validate gender
            gender = request.POST.get("gender", "").strip()
            if gender and gender not in dict(user.GENDER_CHOICES):
                errors["gender"] = "Invalid gender selection."

            # Validate date of birth
            dob = request.POST.get("dob", "").strip()
            if dob:
                try:
                    dob_date = datetime.strptime(dob, "%Y-%m-%d").date()
                    if dob_date > date.today():
                        errors["dob"] = "Date of birth cannot be in the future."
                    elif dob_date.year < 1900:
                        errors["dob"] = "Invalid date of birth."
                except ValueError:
                    errors["dob"] = "Invalid date format. Use YYYY-MM-DD."

            if errors:
                return JsonResponse({"success": False, "errors": errors}, status=400)

            # If no errors, update user profile
            user.fullname = fullname
            user.mobile_number = mobile_number or None
            user.gender = gender or None
            user.dob = dob_date if dob else None
            user.save()
            messages.success(request, "Profile updated successfully.")

            return JsonResponse({"success": True})

    return render(request, "store/profile.html")


@login_required(login_url="login")
@customer_required
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

        if not is_valid_address(address_line_1):
            messages.error(request, "Invalid Building/Street address.")
            return redirect("addresses")

        if not is_valid_name(address_line_2):
            messages.error(request, "Invalid Town/Locality.")
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
@customer_required
def cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related(
        "product_variant", "product_variant__product"
    ).all()
    
    user_available_coupons = Coupon.objects.filter(
        is_active=True,
        start_date__lte=now().date(),
        end_date__gte=now().date(),
        times_used__lt=models.F('usage_limit')
    ).exclude(usages__user=request.user)
    

    # cart actions
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
            
            #removing coupon from cart on actions
            if cart.applied_coupon:
                cart_total = cart.total_discounted_price()
                if cart_total < cart.applied_coupon.min_purchase_amount:
                    cart.applied_coupon = None
                    cart.save()
            if variant.get_best_offer():
                offer = {
                    "discount_value": variant.get_best_offer().discount_value,
                    "discount_type": variant.get_best_offer().discount_type
                }
            else:
                offer={
                    "discount_value":variant.discount_value,
                    "discount_type":variant.discount_type
                }
                    
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
                    "item_discount_type": offer["discount_type"],
                    "item_discount_value": offer["discount_value"],
                    "coupon_applied": cart.applied_coupon is not None,
                    "coupon_code": cart.applied_coupon.code if cart.applied_coupon else None,
                    "coupon_discount": str(cart.total_coupon_discount()) if cart.applied_coupon else '0.00',
                }
            )

    total_mrp = round(cart.total_price(), 2)
    total_discounted = round(cart.total_discounted_price(), 2)
    # Check if the applied coupon is still valid
    if cart.applied_coupon:
        cart_total = cart.total_discounted_price()
        if cart_total < cart.applied_coupon.min_purchase_amount:
            cart.applied_coupon = None
            cart.save()
    context = {
        "cart_items": cart_items,
        "total": total_discounted,
        "total_mrp": total_mrp,
        "total_discount": total_mrp - total_discounted,
        "coupons": user_available_coupons
    }
    return render(request, "store/cart.html", context)

@login_required(login_url="login")
@customer_required
def checkout(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related(
        "product_variant", "product_variant__product"
    ).all()
    
    if (request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest"):
        data = json.loads(request.body)
        coupon_applied = data.get('coupon_applied')
        
        if cart_items.count() == 0:
            messages.error(request, "Your cart is empty.")
            return JsonResponse({'success': False})
        for item in cart_items:
            if (
                item.product_variant.stock < item.quantity
                or item.quantity > 3
                or not item.product_variant.is_active
                or not item.product_variant.product.is_active
                or not item.product_variant.product.brand.is_active
            ):
                messages.error(request, "Product not available")
                return JsonResponse({'success': False})
            
        if coupon_applied:
            return JsonResponse({'success': True})
        cart.applied_coupon = None
        cart.save()
        return JsonResponse({'success': True})
        
    return JsonResponse({'success': False})
    

@login_required(login_url="login")
@customer_required
def apply_coupon(request):
    if (request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest"):
        data = json.loads(request.body)
        coupon_code = data.get('coupon_code')
        
        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)
            coupon_used = CouponUsage.objects.filter(coupon=coupon, user=request.user).first()
            
            if coupon_used:
                return JsonResponse({
                    'success': False,
                    'message': "You already used this coupon",
                })
            if coupon.times_used >= coupon.usage_limit:
                return JsonResponse({
                    'success': False,
                    'message': "Coupon limit exceeds",
                })
                
            cart = Cart.objects.get(user=request.user)
            
            # Check if the coupon is valid
            if coupon.start_date <= timezone.now().date() <= coupon.end_date:
                if coupon.min_purchase_amount <= cart.total_discounted_price():
                    
                    # Save the applied coupon to the cart
                    cart.applied_coupon = coupon
                    cart.save()
                    total_coupon_discount = cart.total_coupon_discount()
                    
                    
                    return JsonResponse({
                        'success': True,
                        'coupon_code': coupon.code,
                        'discount': str(total_coupon_discount),
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': f'Minimum purchase amount of ₹{coupon.min_purchase_amount} required.',
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'This coupon has expired.',
                })
        except Coupon.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invalid coupon code.',
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request.',
    })

@login_required(login_url="login")
@customer_required
def remove_coupon(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart = Cart.objects.get(user=request.user)
        cart.applied_coupon = None
        cart.save()
        
        return JsonResponse({
            'success': True,
        })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request.',
    })


@login_required(login_url="login")
@customer_required
def add_to_cart(request):
    if (
        request.method == "POST"
        and request.headers.get("x-requested-with") == "XMLHttpRequest"
    ):
        data = json.loads(request.body)  # Parse JSON data
        variant_id = data.get("variant_id")
        variant = get_object_or_404(ProductVariant, id=variant_id)

        if (
            not variant.is_active
            or not variant.product.is_active
            or not variant.product.brand.is_active
        ):
            return JsonResponse(
                {"success": False, "message": "This product is not available"},
                status=400,
            )

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

        if not item_created:
            if cart_item.quantity >= max_qty:
                return JsonResponse(
                    {
                        "success": False,
                        "message": f"You can only add up to {max_qty} units of this product",
                    },
                    status=400,
                )
            cart_item.quantity += 1
            cart_item.save()

        cart_item_count = cart.items.count()

        if cart_item.quantity >= 2:
            return JsonResponse(
                {
                    "success": True,
                    "message": "Increased the quantity by 1",
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


# select address to checkout order
@login_required(login_url="login")
@customer_required
def select_address(request):
    default_address = request.user.addresses.filter(is_default=True).first()
    saved_addresses = request.user.addresses.filter(is_default=False)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related(
        "product_variant", "product_variant__product"
    ).all()
    if cart_items.count() == 0:
        messages.error(request, "Your cart is empty.")
        return redirect("cart")
    for item in cart_items:
        if (
            item.product_variant.stock < item.quantity
            or item.quantity > 3
            or not item.product_variant.is_active
            or not item.product_variant.product.is_active
            or not item.product_variant.product.brand.is_active
        ):
            messages.error(request, "Product not available")
            return redirect("cart")
    total_mrp = round(cart.total_price(), 2)
    coupon_discount  = cart.total_coupon_discount()
    total_discounted = round(cart.total_discounted_price(), 2)
    total_discount = total_mrp - total_discounted

    if request.method == "POST":
        checkout_address_id = request.POST.get("checkout_address_id")
        request.session["selected_address_id"] = checkout_address_id
        return redirect("checkout_payment")

    context = {
        "default_address": default_address,
        "saved_addresses": saved_addresses,
        "total_mrp": total_mrp,
        "total_discount": total_discount,
        "coupon_discount": coupon_discount,
        "total": total_discounted - coupon_discount,
    }
    return render(request, "store/select_address.html", context)


@require_POST
@login_required(login_url="login")
@customer_required
def delete_address(request):
    data = json.loads(request.body)  # Parse JSON data
    address_id = data.get("address_id")
    try:
        address = Address.objects.get(id=address_id, user=request.user)
        address.delete()
        return JsonResponse({"success": True})
    except Address.DoesNotExist:
        return JsonResponse({"success": False}, status=400)


@require_POST
@login_required(login_url="login")
@customer_required
def set_default_address(request):
    data = json.loads(request.body)  # Parse JSON data
    address_id = data.get("address_id")
    try:
        address = Address.objects.get(id=address_id, user=request.user)
        Address.objects.filter(user=request.user, is_default=True).update(
            is_default=False
        )
        address.is_default = True
        address.save()
        return JsonResponse({"success": True})
    except Address.DoesNotExist:
        return JsonResponse({"success": False}, status=400)


@require_POST
@login_required(login_url="login")
@customer_required
def save_address(request):
    address_id = request.POST.get("edit")
    if address_id:
        address = get_object_or_404(Address, id=address_id, user=request.user)
    else:
        address = Address(user=request.user)

    address.name = request.POST.get("name")
    address.contact = request.POST.get("phone")
    address.address_line_1 = request.POST.get("address_line_1")
    address.address_line_2 = request.POST.get("address_line_2")
    address.city = request.POST.get("city")
    address.state = request.POST.get("state")
    address.postal_code = request.POST.get("postal_code")
    address.country = request.POST.get("country")
    address.is_default = request.POST.get("is_default") == "on"

    if not is_valid_name(address.name):
        return JsonResponse({"success": False, "message": "Invalid name."}, status=400)
    if not is_valid_phone(address.contact):
        return JsonResponse(
            {"success": False, "message": "Invalid phone number."}, status=400
        )
    if not is_valid_address(address.address_line_1):
        return JsonResponse(
            {"success": False, "message": "Invalid Building/Street address."},
            status=400,
        )
    if not is_valid_name(address.address_line_2):
        return JsonResponse(
            {"success": False, "message": "Invalid Town/Locality."}, status=400
        )
    if not is_valid_name(address.city):
        return JsonResponse(
            {"success": False, "message": "Invalid city name."}, status=400
        )
    if not is_valid_name(address.state):
        return JsonResponse(
            {"success": False, "message": "Invalid state name."}, status=400
        )
    if not is_valid_postalcode(address.postal_code):
        return JsonResponse(
            {"success": False, "message": "Invalid postal code."}, status=400
        )
    if not is_valid_name(address.country):
        return JsonResponse(
            {"success": False, "message": "Invalid country name."}, status=400
        )

    address.save()

    if address.is_default:
        Address.objects.filter(user=request.user).exclude(id=address.id).update(
            is_default=False
        )

    return JsonResponse({"success": True})


@login_required(login_url="login")
@customer_required
def checkout_payment(request):
    selected_address_id = request.session.get("selected_address_id")
    if not selected_address_id:
        messages.error(request, "Please select an address before proceeding to payment.")
        return redirect("checkout_address")

    address = get_object_or_404(Address, id=selected_address_id, user=request.user)
    cart = Cart.objects.get(user=request.user)
    cart_items = cart.items.select_related("product_variant", "product_variant__product").all()

    if cart_items.count() == 0:
        del request.session["selected_address_id"]
        messages.error(request, "Your cart is empty.")
        return redirect("cart")

    for item in cart_items:
        if (
            item.product_variant.stock < item.quantity
            or item.quantity > 3
            or not item.product_variant.is_active
            or not item.product_variant.product.is_active
            or not item.product_variant.product.brand.is_active
        ):
            del request.session["selected_address_id"]
            messages.error(request, "Product not available")
            return redirect("cart")

    total_mrp = round(cart.total_price(), 2)
    total_discounted = round(cart.total_discounted_price(), 2)
    total_discount = total_mrp - total_discounted
    applied_coupon = cart.applied_coupon
    coupon_discount = 0

    if applied_coupon and applied_coupon.is_active and applied_coupon.times_used < applied_coupon.usage_limit:
        if applied_coupon.start_date <= now().date() <= applied_coupon.end_date:
            if applied_coupon.min_purchase_amount <= cart.total_discounted_price():
                coupon_discount = cart.total_coupon_discount()
            else:
                cart.applied_coupon = None
                cart.save()
        else:
            cart.applied_coupon = None
            cart.save()
    else:
        cart.applied_coupon = None
        cart.save()

    user_wallet, created = Wallet.objects.get_or_create(user=request.user)
    if user_wallet.balance >= (total_discounted-coupon_discount):
        payment_methods = Order.PAYMENT_METHOD_CHOICES
    else:
        payment_methods = [
            method for method in Order.PAYMENT_METHOD_CHOICES if method[0] != 'wallet'
        ]

    if request.method == "POST":
        payment_method = request.POST.get("payment_method")
        if payment_method not in dict(payment_methods):
            messages.error(request, "Invalid payment method selected.")
            return redirect("checkout_payment")
        if payment_method == 'wallet' and user_wallet.balance < (total_discounted-coupon_discount):
            messages.error(request, "Insufficient balance in your wallet.")
            return redirect("checkout_payment")

        try:
            with transaction.atomic():
                # Create the order
                order = Order.objects.create(
                    user=request.user,
                    delivery_address_name=address.name,
                    delivery_address_contact=address.contact,
                    delivery_address_line_1=address.address_line_1,
                    delivery_address_line_2=address.address_line_2,
                    delivery_city=address.city,
                    delivery_state=address.state,
                    delivery_country=address.country,
                    delivery_postal_code=address.postal_code,
                    delivery_address_type=address.address_type,
                    total_price=total_mrp,
                    total_discount=total_discount,
                    total_price_after_discount=total_discounted-coupon_discount,
                    order_payment=payment_method,
                    applied_coupon = cart.applied_coupon
                )

                # Create order items
                for cart_item in cart_items:
                    variant = cart_item.product_variant
                    discount = variant.price - variant.discounted_price()
                    discounted_price = variant.discounted_price()
                    item_coupon_discount = cart_item.coupon_discount()
                    OrderItem.objects.create(
                        order=order,
                        product_variant=cart_item.product_variant,
                        quantity=cart_item.quantity,
                        price=variant.price,
                        discount=discount,
                        price_after_discount=discounted_price-item_coupon_discount,
                        coupon_discount=item_coupon_discount
                    )
                    # Update stock
                    cart_item.product_variant.stock -= cart_item.quantity
                    cart_item.product_variant.save()
                
                if coupon_discount:
                    coupon = Coupon.objects.get(id=cart.applied_coupon.id)
                    CouponUsage.objects.create(
                        coupon=coupon,
                        user=request.user,
                        order=order
                    )
                    coupon.times_used+=1
                    coupon.save()

                # Clear the cart
                cart.applied_coupon=None
                cart.save()
                cart.items.all().delete()

                if payment_method == "razorpay":
                    razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                    # Create Razorpay order
                    razorpay_order = razorpay_client.order.create({
                        'amount': int((total_discounted-coupon_discount) * 100),  # Amount in paise
                        'currency': 'INR',
                        'payment_capture': '1'
                    })
                    order.razorpay_order_id = razorpay_order['id']
                    order.razorpay_payment_status = "created"
                    order.save()

                    return JsonResponse({
                        'order_id': order.id,
                        'razorpay_order_id': razorpay_order['id'],
                        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                        'amount': int((total_discounted-coupon_discount) * 100),
                    })
                    
                if payment_method == 'wallet':
                    WalletTransaction.objects.create(
                        wallet=user_wallet,
                        amount=total_discounted-coupon_discount,
                        transaction_type='debit',
                        transaction_purpose='purchase',
                        description = f"Purchase of order #{order.id}",
                        order=order
                        )


            messages.success(request, "Order placed successfully!")
            del request.session["selected_address_id"]
            return redirect("my_orders")
        except Exception as e:
            messages.error(request, f"An error occurred while placing your order: {str(e)}")
            return redirect("checkout_payment")

    context = {
        "total_mrp": total_mrp,
        "total_discount": total_discount,
        "coupon_discount": coupon_discount,
        "total": total_discounted - coupon_discount,
        "payment_methods": payment_methods,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
    }
    return render(request, "store/checkout_payment.html", context)

@csrf_exempt
def razorpay_payment_success(request):
    razorpay_payment_id = request.GET.get('razorpay_payment_id')
    razorpay_order_id = request.GET.get('razorpay_order_id')
    razorpay_signature = request.GET.get('razorpay_signature')

    try:
        order = Order.objects.get(razorpay_order_id=razorpay_order_id)
        razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        # Verify the payment signature
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        razorpay_client.utility.verify_payment_signature(params_dict)

        order.razorpay_payment_id = razorpay_payment_id
        order.razorpay_payment_status = "paid"
        order.save()

        messages.success(request, "Payment successful!")
        return redirect("my_orders")
    except:
        messages.error(request, "Payment verification failed.")
        return redirect('my_orders')


def get_razorpay_order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    return JsonResponse({
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'amount': int(order.total_price_after_discount * 100),  # Amount in paise
        'currency': 'INR',
        'name': request.user.fullname,
        'email': request.user.email,
    })
    

#only using when payment failed
@require_POST
def cancel_razorpay_order(request):
    if request.method=='POST':
        data = json.loads(request.body)
        order_id = data.get("order_id")
        order = get_object_or_404(Order, id=order_id, user=request.user)
        if order.razorpay_order_id and order.razorpay_payment_status == 'created':
            try:
                # Update the order status in your database
                order.razorpay_payment_status = 'cancelled'
                order.save()
                
                # Cancel all order items
                for item in order.items.all():
                    item.status = 'cancelled'
                    variant = get_object_or_404(ProductVariant,id=item.product_variant.id)
                    variant.stock+=item.quantity
                    variant.save()
                    item.save()
                
                return JsonResponse({'success': True})
            except razorpay.errors.BadRequestError as e:
                return JsonResponse({'success': False, 'error': str(e)})
            except Exception as e:
                return JsonResponse({'success': False, 'error': 'An unexpected error occurred'})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid order or payment status'})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required(login_url="login")
@customer_required
def change_password(request):
    has_password = request.user.has_usable_password()
    context = {"has_password": has_password}
    if request.method == "POST":
        if has_password:
            old_password = request.POST.get("old_password")

        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password and confirm_password:
            if has_password:
                if not check_password(old_password, request.user.password):
                    messages.error(request, "The old password is incorrect.")
                elif new_password == old_password:
                    messages.error(
                        request, "New password cannot be the same as the old password."
                    )
            if new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
            elif not is_valid_password(new_password):
                messages.error(
                    request,
                    "Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, a digit, and a special character.",
                )
            else:
                # Update the password
                request.user.set_password(new_password)
                request.user.save()

                # Keep the user logged in after password change
                update_session_auth_hash(request, request.user)

                messages.success(
                    request, "Your password has been successfully changed."
                )
                return redirect(
                    "profile"
                )  # Redirect to a relevant page (e.g., profile)
        else:
            messages.error(request, "All fields are required.")

    return render(request, "store/change_password.html", context)


@login_required(login_url="login")
@customer_required
def orders(request):
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items")
        .order_by("-created_at")
    )
    for order in orders:
        order_items = order.items.all()
        order.order_items = order_items

    if (
        request.method == "POST"
        and request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        item_id = request.POST.get("item_id")
        order_id = request.POST.get("order_id")
        action = request.POST.get("action")

        order = get_object_or_404(Order, id=order_id, user=request.user)
        order_item = get_object_or_404(order.items, id=item_id)

        if action == "cancel":
            if order_item.status in ["pending", "confirmed"]:
                order_item.status = "cancelled"
                
                #refund to wallet on cancellation
                if order.order_payment == 'wallet' or (order.order_payment == 'razorpay' and order.razorpay_payment_status == 'paid'):
                    user_wallet = get_object_or_404(Wallet, user=request.user)
                    WalletTransaction.objects.create(
                        wallet=user_wallet,
                        amount=order_item.sub_total(),
                        transaction_type='credit',
                        transaction_purpose='refund',
                        description = f"Refund for {order_item}",
                        order=order
                        )
                    
                variant = order_item.product_variant
                variant.stock += order_item.quantity
                variant.save()
                order_item.save()
                return JsonResponse(
                    {"success": True, "message": "Order item cancelled successfully"}
                )
            else:
                return JsonResponse(
                    {"success": False, "message": "Cannot cancel this order item"},
                    status=400,
                )

        elif action == "return":
            if order_item.status == "delivered":
                order_item.status = "return_requested"
                order_item.save()
                return JsonResponse(
                    {"success": True, "message": "Return request created successfully"}
                )
            else:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Cannot create return request for this order item",
                    },
                    status=400,
                )

        elif action == "cancel_return":
            if (
                order_item.status == "return_requested"
                or order_item.status == "return_accepted"
            ):
                order_item.status = "delivered"
                order_item.save()
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Return request cancelled successfully",
                    }
                )
            else:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Cannot cancel return request for this order item",
                    },
                    status=400,
                )

    context = {
        "orders": orders,
    }
    return render(request, "store/orders.html", context)


@login_required(login_url="login")
@customer_required
def view_order(request, item_id):
    order_item = get_object_or_404(OrderItem, id=item_id)
    if not request.user == order_item.order.user:
        messages.error(request, "Order not found")
        return redirect("my_orders")
    variant = get_object_or_404(ProductVariant, id=order_item.product_variant.id)
    other_items = OrderItem.objects.filter(order=order_item.order.id).exclude(
        id=order_item.id
    )

    context = {"variant": variant, "order_item": order_item, "other_items": other_items}

    return render(request, "store/view_order.html", context)


@login_required(login_url="login")
@customer_required
def wishlist(request):
    wishlist_items = (
        Wishlist.objects.filter(user=request.user)
        .prefetch_related("product_variant")
        .order_by("-added_at")
    )
    context = {"wishlist_items": wishlist_items}
    return render(request, "store/wishlist.html", context)


@login_required(login_url="login")
@customer_required
def toggle_wishlist(request):
    if (
        request.method == "POST"
        and request.headers.get("x-requested-with") == "XMLHttpRequest"
    ):
        data = json.loads(request.body)  # Parse JSON data
        variant_id = data.get("variant_id")
        variant = get_object_or_404(ProductVariant, id=variant_id)

        wishlist, wishlist_created = Wishlist.objects.get_or_create(
            user=request.user, product_variant=variant
        )

        if not wishlist_created:
            wishlist.delete()
            return JsonResponse(
                {
                    "success": True,
                    "action": "removed",
                    "message": "Removed item from wishlist.",
                }
            )
        return JsonResponse(
            {"success": True, "action": "added", "message": "Item added to wishlist."}
        )
    return JsonResponse({"success": False, "message": "Invalid request"}, status=400)


@login_required(login_url="login")
@customer_required
def wallet(request):
    user_wallet, created = Wallet.objects.get_or_create(user=request.user)
    transactions = WalletTransaction.objects.filter(wallet=user_wallet).order_by('-created_at')
    
    context = {
        'wallet': user_wallet,
        'transactions': transactions,
    }
    return render(request, "store/wallet.html", context)

