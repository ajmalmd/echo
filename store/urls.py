from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.user_login, name="login"),
    path("signup/", views.user_signup, name="signup"),
    path("logout/", views.user_logout, name="logout"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("reset-password/", views.reset_password, name="reset_password"),
    path("", views.home, name="home"),
    path("products/", views.products_listing, name="store_products"),
    path("variant/<int:variant_id>/", views.view_variant, name="view_variant"),
    # profile
    path("profile/", views.profile, name="profile"),
    path("addresses/", views.addresses, name="addresses"),
    path("orders/", views.orders, name="my_orders"),
    path("order/<int:item_id>/", views.view_order, name="view_order"),
    path("wallet/", views.wallet, name="wallet"),
    path("change-password/", views.change_password, name="change_password"),
    path("save-address/", views.save_address, name="save_address"),
    path("delete-address/", views.delete_address, name="delete_address"),
    path("set-default-address/", views.set_default_address, name="set_default_address"),
    path("delete_address/", views.delete_address, name="delete_address"),
    
    path("wishlist/", views.wishlist, name="wishlist"),
    path("toggle-wishlist", views.toggle_wishlist, name="toggle_wishlist"),
    path("cart/", views.cart, name="cart"),
    path("add-to-cart/", views.add_to_cart, name="add_to_cart"),
    path("checkout/address/", views.select_address, name="checkout_address"),
    path("checkout/payment/", views.checkout_payment, name="checkout_payment"),
    path('razorpay-payment-success/', views.razorpay_payment_success, name='razorpay_payment_success'),
    path('get-razorpay-order-details/<int:order_id>/', views.get_razorpay_order_details, name='get_razorpay_order_details'),
    path('cancel-razorpay-order/', views.cancel_razorpay_order, name='cancel_razorpay_order'),
]
