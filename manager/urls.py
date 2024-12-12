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
    
    path('products/', views.products, name='products'),
    path("product/<int:product_id>/toggle-status/", views.toggle_product_status, name="toggle_product_status"),
    
    path('products/view/<int:product_id>/', views.product_view, name='product_view'),
    path("variant/<int:variant_id>/toggle-status/", views.toggle_variant_status, name="toggle_variant_status"),
    
    path('products/add/', views.add_product, name='add_product'),
]