from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('products/', views.products, name='products'),
    path('brands/', views.brands, name='brands'),
    path('products/view/', views.product_view, name='product_view'),
    # path('products/<int:pk>/', views.product_view, name='product_view'),
]