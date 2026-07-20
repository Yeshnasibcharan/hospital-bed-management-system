from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import StyledLoginForm

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html',
        authentication_form=StyledLoginForm
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('redirect/', views.role_redirect, name='role_redirect'),
]