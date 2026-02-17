from django.urls import path
from .views import (
    ForgotPasswordConfirmView,
    ForgotPasswordRequestView,
    GoogleAuthView,
    LoginView,
    LogoutView,
    MeView,
    SendOTPView,
    VerifyOTPAndRegisterView,
)
from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = [
    path("send-otp/", SendOTPView.as_view(), name="send-otp"),
    path("verify-otp-and-register/", VerifyOTPAndRegisterView.as_view(), name="verify-otp-and-register"),
    path("forgot-password/send-otp/", ForgotPasswordRequestView.as_view(), name="forgot-password-send-otp"),
    path("forgot-password/reset/", ForgotPasswordConfirmView.as_view(), name="forgot-password-reset"),

    path('login/', LoginView.as_view(), name='login'),
    path('google/', GoogleAuthView.as_view(), name='google-auth'),
    
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path("me/", MeView.as_view(), name="auth-me"),
]

