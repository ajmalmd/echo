from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.user_login, name="login"),
    path("signup/", views.user_signup, name="signup"),
    path("logout/", views.user_logout, name='logout'),
    path("verify-otp/", views.verify_otp, name='verify_otp'),
    path("", views.home, name="home"),
    path("products/", views.products_listing, name='store_products'),
    path('variant/<int:variant_id>/', views.view_variant, name='view_variant'),
]
