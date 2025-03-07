from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    path('users/', views.users, name='users'),
    path("user/<int:user_id>/toggle-status/", views.toggle_user_status, name="toggle_user_status"),
    
    path('brands/', views.brands, name='brands'),
    path("brand/<int:brand_id>/toggle-status/", views.toggle_brand_status, name="toggle_brand_status"),
    path('add-brand/', views.add_brand, name='add_brand'),
    path("brand/edit/<int:brand_id>/", views.edit_brand, name="edit_brand"),
    
    path('products/', views.products, name='products'),
    path('products/add/', views.add_product, name='add_product'),
    path("products/edit/<int:product_id>/", views.edit_product, name="edit_product"),
    path("product/<int:product_id>/toggle-status/", views.toggle_product_status, name="toggle_product_status"),
    
    path('product/<int:product_id>/', views.product_view, name='product_view'),
    path("variant/<int:variant_id>/toggle-status/", views.toggle_variant_status, name="toggle_variant_status"),
    path("products/<int:product_id>/add-variant/", views.add_variant, name="add_variant"),
    path('variant/<int:variant_id>/edit', views.edit_variant, name='edit_variant'),
    
    path('orders/', views.orders, name='orders'),
    path('order/<int:order_id>/', views.order_view, name='order_view'),
    
    path('offers/', views.offers, name='offers'),
    path('edit-offer/', views.edit_offer, name='edit_offer'),
    path('get-offer-details/', views.get_offer_details, name='get_offer_details'),
    path('toggle-offer-status/', views.toggle_offer_status, name='toggle_offer_status'),
    
    path('coupons/', views.coupons, name='coupons'),
    path('edit-coupon/', views.edit_coupon, name='edit_coupon'),
    path('get-coupon-details/', views.get_coupon_details, name='get_coupon_details'),
    path('toggle-coupon-status/', views.toggle_coupon_status, name='toggle_coupon_status'),
    
    path('report/', views.report, name="report"),
    path('download-report/', views.download_report, name='download_report'),
]