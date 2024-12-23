from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from .models import User, OTP
from manager.models import Brand, Product, ProductVariant
from .services import generate_otp, send_otp_email, get_new_arrivals
from .validators import is_valid_email, is_valid_name, is_valid_password
from django.contrib.auth.decorators import user_passes_test
from django.utils.timezone import now, timedelta
from datetime import datetime
from django.views.decorators.cache import never_cache
from django.db.models import F


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


def verify_otp(request):

    next_url = request.GET.get("next", "home")

    if request.user.is_authenticated:
        return redirect(next_url)

    # Check if user signup data exists in the session
    user_signup_data = request.session.get("user_signup_data", None)
    if not user_signup_data:
        messages.error(request, "No signup session found. Please sign up again.")
        return redirect("signup")

    if request.method == "POST":
        # Combine OTP from individual inputs
        otp = "".join([request.POST.get(f"otp{i+1}", "").strip() for i in range(6)])

        email = user_signup_data["email"]

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
            messages.error(request, "No OTP record found. Please sign up again.")
            return redirect("signup")

        # OTP is valid; create the user
        User.objects.create_user(
            email=email,
            password=user_signup_data["password"],
            fullname=user_signup_data["fullname"],
        )

        # Clean up session and OTP record
        del request.session["user_signup_data"]
        del request.session["otp_sent_time"]
        otp_record.delete()

        messages.success(
            request, "OTP verified successfully. Your account has been created."
        )

        # Authenticate and Login verified user
        user = authenticate(request, email=email, password=user_signup_data["password"])
        login(request, user)
        return redirect("home")

    elif request.method == "GET" and request.GET.get("resend", None) == "true":
        # Resend OTP logic
        user_signup_data = request.session.get("user_signup_data", None)
        if not user_signup_data:
            messages.error(request, "No signup session found. Please sign up again.")
            return redirect("signup")

        email = user_signup_data["email"]

        # Check if resend is allowed based on the session's OTP sending time
        otp_sent_time = request.session.get("otp_sent_time")
        if otp_sent_time:
            otp_sent_time = datetime.fromisoformat(otp_sent_time)
            time_since_last_otp = datetime.now() - otp_sent_time

            if time_since_last_otp < timedelta(seconds=59):  # 59 seconds
                messages.error(request, "You must wait before resending the OTP.")
                return redirect("verify_otp")

        try:
            otp_record = OTP.objects.get(email=email)

            if otp_record.resend_count >= 3:
                time_since_first_resend = now() - otp_record.created_at

                if time_since_first_resend <= timedelta(hours=4):
                    messages.error(request, "Resend limit exceeded. Try again later.")
                    return redirect("signup")

                else:
                    otp_record.resend_count = 0  # Reset resend count after 4 hours

            # Generate and send new OTP
            otp = generate_otp()
            otp_record.otp = otp
            otp_record.created_at = now()
            otp_record.resend_count += 1
            otp_record.save()

            send_otp_email(email, otp)

            # Update the session with the new OTP sending time
            request.session["otp_sent_time"] = datetime.now().isoformat()

            messages.success(request, "OTP has been resend.")

        except OTP.DoesNotExist:
            messages.error(request, "No OTP record found. Please sign up again.")
            return redirect("signup")

    return render(request, "store/verify_otp.html")


def user_logout(request):
    logout(request)
    return redirect("home")


# @user_passes_test(is_customer)
def home(request):
    new_arrivals = get_new_arrivals(6)

    return render(request, "store/home.html", {"new_arrivals": new_arrivals})


def products_listing(request):
    brands = Brand.objects.filter(is_active=True)
    products = (
        ProductVariant.objects.filter(
            is_active=True,
            product__is_active=True,
            product__brand__is_active=True,
        )
        .select_related("product")
        .prefetch_related("images")
        .annotate(product_name=F("product__name"), brand_name=F("product__brand__name"))
    )
    return render(
        request,
        "store/products_list.html",
        {"brands": brands, "productModel": Product, "products": products},
    )


def view_variant(request, variant_id):

    variant = get_object_or_404(ProductVariant, id=variant_id)
    discounted_price = variant.discounted_price()
    product = variant.product
    brand = product.brand
    other_variants = product.variants.exclude(id=variant_id)
    variant_images = variant.images.all()
    rating={"rating":4.5,"count":100}
    similar_variants = product.get_similar_variants(exclude_variant=variant)

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
