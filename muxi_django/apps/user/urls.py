
from django.urls import path
from .views import UserApiView, LoginView, RegisterView, VerifyCodeView, WeiboQrCodeView, WeiboQrCheckView, \
    WeiboCallbackView, CurrentUserInfoView, AvatarUploadView, BackgroundUploadView, PasswordResetVerifyView, \
    PasswordResetView, ModifyPasswordView

urlpatterns = [
    path("", UserApiView.as_view()),
    path("login/", LoginView.as_view()),
    path('register/', RegisterView.as_view()),
    path('verify-code/', VerifyCodeView.as_view()),
    path("weibo/qrcode/", WeiboQrCodeView.as_view()),
    path("weibo/qrcode/check/", WeiboQrCheckView.as_view()),
    path("weibo/callback/", WeiboCallbackView.as_view()),
    path("current/", CurrentUserInfoView.as_view()),
    path("upload/avatar/", AvatarUploadView.as_view()),
    path("upload/background/", BackgroundUploadView.as_view()),
    path('reset-password/verify/', PasswordResetVerifyView.as_view()),
    path('reset-password/', PasswordResetView.as_view()),
    path('update-password/', ModifyPasswordView.as_view()),
]