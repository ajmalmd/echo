from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.user_login, name="login"),
    path("signup/", views.user_signup, name="signup"),
    path("logout/", views.user_logout, name='logout'),
    path("verify-otp/", views.verify_otp, name='verify_otp'),
    path("forgot-password/", views.forgot_password, name='forgot_password'),
    path("reset-password/", views.reset_password, name='reset_password'),
    
    path("", views.home, name="home"),
    path("products/", views.products_listing, name='store_products'),
    path('variant/<int:variant_id>/', views.view_variant, name='view_variant'),
    
    #profile
    path("addresses/", views.addresses, name='addresses'),
    
    path("cart/", views.cart, name='cart'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
]
