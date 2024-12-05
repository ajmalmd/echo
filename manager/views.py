from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.core.paginator import Paginator
from .utils import paginate_items


@never_cache
def admin_login(request):
    next_url = request.GET.get("next", "dashboard")
    if request.user.is_authenticated:
        return redirect(next_url)
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            return redirect(next_url)
        else:
            messages.error(request, "Invalid email or password.")
    return render(request, "login.html", {"next": next_url})


def admin_logout(request):
    logout(request)
    return redirect("admin_login")


@login_required(login_url="admin_login")
@never_cache
def dashboard(request):
    return render(request, "dashboard.html")


@login_required(login_url="admin_login")
@never_cache
def products(request):
    product_list = [
        {
            "name": " Sony Wireless Headphones",
            "brand_name": "Sony",
            "no_of_variants": 3,
            "connectivity_type": "Wireless",
            "wear_type": "Over the Ear",
            "is_active": True,
        },
        {
            "name": "Sennheiser Headset",
            "brand_name": "Sennheiser",
            "no_of_variants": 2,
            "connectivity_type": "Wired",
            "wear_type": "Over the Ear",
            "is_active": False,
        },
        {
            "name": "Sports Earbuds",
            "brand_name": "Brand C",
            "no_of_variants": 4,
            "connectivity_type": "Wireless",
            "wear_type": "In the Ear",
            "is_active": True,
        },
        {
            "name": "Studio Headphones",
            "brand_name": "Brand D",
            "no_of_variants": 1,
            "connectivity_type": "Wired",
            "wear_type": "Over the Ear",
            "is_active": True,
        },
        {
            "name": "Compact Earbuds",
            "brand_name": "Brand E",
            "no_of_variants": 5,
            "connectivity_type": "Multi-functional",
            "wear_type": "In the Ear",
            "is_active": False,
        },
    ]

    page_obj = paginate_items(request, product_list, per_page=10)

    return render(request, "products.html", {"page_obj": page_obj})


@login_required(login_url="admin_login")
@never_cache
def brands(request):
    # Sample data for demonstration
    brand_list = [
        {"name": "Sony", "product_count": 50, "is_active": True},
        {"name": "Bose", "product_count": 30, "is_active": False},
        {"name": "JBL", "product_count": 70, "is_active": True},
        {"name": "Sennheiser", "product_count": 20, "is_active": False},
        {"name": "Beats", "product_count": 40, "is_active": True},
    ]

    # Pass the brands data to the template
    return render(request, "brands.html", {"brands": brand_list})


@login_required(login_url="admin_login")
@never_cache
def product_view(request):
    return render(request, "product_view.html")
