# 进行users子应用的视图路由
from django.urls import path
from users.views import RegisterView, ImageCodeView, LoginView, ForgetPasswordView,LogoutView,UserCenterView,WriteBlogView
from users.views import SmsCodeView
# from users.views import LogoutView

urlpatterns = [
    # 参数1：路由
    # 参数2：视图函数
    # 参数3：路由名，方便通过reverse来获取路由
    path('register/', RegisterView.as_view(), name='register'),

    # 图片验证码得路由
    path('imagecode/', ImageCodeView.as_view(), name='imagecode'),
    # 短信发送
    path('smscode/', SmsCodeView.as_view(), name='smscode'),
    #登录路由
    path('login/', LoginView.as_view(), name='login'),
    # 退出登录
    path('logout/', LogoutView.as_view(), name='logout'),
    # 忘记密码
    path('forgetpassword/', ForgetPasswordView.as_view(), name='forgetpassword'),
    # 个人中心
    path('center/', UserCenterView.as_view(), name='center'),
    # 写博客
    path('writeblog/', WriteBlogView.as_view(), name='writeblog'),


]
# 图片访问你的路由
from django.conf import settings
from django.conf.urls.static import static
urlpatterns +=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
