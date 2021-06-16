import re

from django.shortcuts import render, redirect

# Create your views here.
from django.urls import reverse

from django.views import View
from django.http.response import HttpResponseBadRequest
from users.models import User
from django.db import DatabaseError
import re
#注册视图
class RegisterView(View):
    def get(self,request):
        return render(request,'register.html')
    def post(self,request):
        """
        1.接收数据
        2.验证数据
            2.1参数是否齐全
            2.2手机号的格式是否正确
            2.3密码是否符合格式
            2.4密码和确认密码是否一致
            2.5短信验证码是否和redis中的一致
        3.保存注册信息
        4.返回响应跳转到指定页面
        :param request:
        :return:
        """
        # 1.接收数据
        mobile=request.POST.get('mobile')
        password=request.POST.get('password')
        password2=request.POST.get('password2')
        smscode=request.POST.get('sms_code')
        # 2.验证数据
        #     2.1参数是否齐全
        if not all([mobile,password,password2,smscode]):
            return  HttpResponseBadRequest('缺少必要的参数')
        #     2.2手机号的格式是否正确
        if not re.match(r'^1[3-9]\d{9}$',mobile):
            return HttpResponseBadRequest('手机号不符合规则')
        #     2.3密码是否符合格式
        if not re.match(r'^[0-9A-Za-z]{8,20}$',password):
            return HttpResponseBadRequest('请输入8-20位数字或字母组成的密码')
        #     2.4密码和确认密码是否一致
        if password!=password2:
            return HttpResponseBadRequest('两次密码不一致')
        #     2.5短信验证码是否和redis中的一致
        redis_conn=get_redis_connection('default')
        redis_sms_code=redis_conn.get('sms:%s'%mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if smscode !=redis_sms_code.decode():
            return HttpResponseBadRequest('短信验证码错误')
        # 3.保存注册信息
        # create_user可以使用系统的方法来对密码进行加密
        try:
            user=User.objects.create_user(username=mobile,mobile=mobile,password=password)
        except  DatabaseError as e:
            logger.error(e)
            return HttpResponseBadRequest('注册失败')
        from django.contrib.auth import login
        login(request,user)
        # 4.返回响应跳转到指定页面
        # 暂时返回一个注册成功的信息，后期再实现跳转到指定界面
        # redirect进行重定向
        # reverse是可以通过namespace：name来获取到视图所对应的路由
        respone = redirect(reverse('home:index'))
        # return HttpResponse('注册成功，重定向到首页')
        # 设置cookie信息，以方便首页中用户信息展示的判断和用户信息的展示
        respone.set_cookie('is_login',True)
        respone.set_cookie('username',user.username,max_age=7*24*3600)
        return respone

from django.http.response import HttpResponseBadRequest
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from django.http import HttpResponse

class ImageCodeView(View):
    def get(self,request):
        """
        # 1.接受前端传递过来的uuid
        # 2.判断uuid是否获取到
        # 3.通过调用captcha来生成图片验证码（图片二进制和图片内容）
        # 4.将图片内容保存到redis中
        #     uuid做为key，图片内容作为一个value同时我们还需要设置一个时效
        # 5.返回图片二进制
        :param request:
        :return:
        """
        # 1.接受前端传递过来的uuid
        uuid=request.GET.get('uuid')
        # 2.判断uuid是否获取到
        if uuid is None:
            return HttpResponseBadRequest('没有传递uuid')
        # 3.通过调用captcha来生成图片验证码（图片二进制和图片内容）
        text,image=captcha.generate_captcha()
        # 4.将图片内容保存到redis中
        #     uuid做为key，图片内容作为一个value同时我们还需要设置一个时效
        redis_conn=get_redis_connection('default')
        # key设置为uuid
        # seconds 过期秒数 300s 5分钟过期
        # value text
        redis_conn.setex('img:%s'%uuid,300,text)
        # 5.返回图片二进制
        return HttpResponse(image,content_type='image/jpeg')

from django.http.response import JsonResponse
from utils.response_code import RETCODE
import logging
logger=logging.getLogger('django')
from random import randint
from libs.yuntongxun.sms import CCP

class SmsCodeView(View):
    def get (self,request):
        """
        # 1.接收参数
        # 2.参数的验证
        #     2.1 验证参数是否齐全
        #     2.2 图片验证码的验证
        #         连接redis，获取redis中的图片验证码
        #         判断图片验证码是否存在
        #         如果图片验证码未过期，获取到之后就可以删除图片验证码
        #         比对图片验证码
        # 3.生成短信验证码
        # 4.保存短信验证码到redis中
        # 5.发送短信
        # 6.返回响应
        :param request:
        :return:
        """
        # 1.接收参数（查寻字符串的形式传递过来）
        mobile=request.GET.get('mobile')
        image_code=request.GET.get('image_code')
        uuid=request.GET.get('uuid')
        # 2.参数的验证
        #     2.1 验证参数是否齐全
        if not all([mobile,image_code,uuid]):
            return JsonResponse({'code':RETCODE.NECESSARYPARAMERR,'errmsg':'缺少必要的参数'})
        #     2.2 图片验证码的验证
        #         连接redis，获取redis中的图片验证码
        redis_conn=get_redis_connection('default')
        redis_image_code=redis_conn.get('img:%s'%uuid)
        #         判断图片验证码是否存在
        if redis_image_code is None:
            return JsonResponse({'code':RETCODE.IMAGECODEERR,'errmsg':'图片验证码已过期'})
        #         如果图片验证码未过期，获取到之后就可以删除图片验证码
        try:
            redis_conn.delete('img:%s'%uuid)
        except Exception as e:
            logger.error(e)

        #         比对图片验证码注意大小写，redis的数据是byte类型
        if redis_image_code.decode().lower() != image_code.lower():
            return JsonResponse({'code':RETCODE.IMAGECODEERR,'errmsg':'图片验证码已过期'})
        # 3.生成短信验证码
        sms_code='%06d'%randint(0,999999)
        #为了后期比对方便，我们可以将短信验证码记录到日志中
        logger.info(sms_code)
        # 4.保存短信验证码到redis中
        redis_conn.setex('sms:%s'%mobile,300,sms_code)
        # 5.发送短信
            # 参数1：测试手机号
            # 参数2（列表）：您的验证码是{1}}请在{2}分钟内正确输入
            # {1}短信验证码
            # {2}短信验证码有效期
            # 参数3：免费开发测试模板为1
        CCP().send_template_sms(mobile,[sms_code,5],1)
        # 6.返回响应
        return JsonResponse({'code':RETCODE.OK,'errmsg':'短信发送成功'})

class LoginView(View):
    def get(self,request):
        """
        1.接收参数
        2.参数的验证
            2.1验证手机号是否符合规则
            2.2验证密码是否符合规则
        3.用户认证登录
        4.状态的保持
        5.根据用户选择的是否记住登录状态来判断
        6.为了首页显示我们需要设置一些cookie信息
        7.返回响应
        :param request:
        :return:
        """
        return render(request,'login.html')
    def post(self,request):
        """
        1.接收参数
        2.参数的验证
            2.1验证手机号是否符合规则
            2.2验证密码是否符合规则
        3.用户认证登录
        4.状态的保持
        5.根据用户选择的是否记住登录状态来判断
        6.为了首页显示我们需要设置一些cookie信息
        7.返回响应
        :param request:
        :return:
        """
        # 1.接收参数
        mobile = request.POST.get('mobile')
        password= request.POST.get('password')
        remember= request.POST.get('remember')
        # 2.参数的验证
        #     2.1验证手机号是否符合规则
        if not re.match(r'^1[3-9]\d{9}$',mobile):
            return HttpResponseBadRequest('手机号不符合规则')
        #     2.2验证密码是否符合规则
        if not re.match(r'^[0-9A-Za-z]{8,20}$',password):
            return HttpResponseBadRequest('密码不符合规则')
        # 3.用户认证登录
        # 采用系统自带的认证方法进行认证
        # 如果我们的用户名和密码正确，会返回user
        # 如果我们的用户名或密码正确，会返回None
        from django.contrib.auth import authenticate,login
        # 默认的认证方式是针对于username字段进行用户名的判断
        # 当前的判断信息是手机号，所以所以我们需要修改一下认证字段
        # 我们需要到User模型中进行修改，等测试出现问题的时候，我们在修改
        user=authenticate(mobile=mobile,password=password,)

        if user is None:
            return HttpResponseBadRequest('用户名或密码错误')
        # 4.状态的保持
        login(request,user,)
        # 5.根据用户选择的是否记住登录状态来判断
        # 6.为了首页显示我们需要设置一些cookie信息
        next_page=request.GET.get('next')
        if next_page :
            response=redirect(next_page)
        else:
            response=redirect(reverse('home:index'))
        if remember !='on':#没有记住用户信息（浏览器关闭之后）
            request.session.set_expiry(0)
            response.set_cookie('is_login',True)
            response.set_cookie('username',user.username,max_age=14*24*3600)
        else:              #记住用户信息(默认是记住14天)
            request.session.set_expiry(None)
            response.set_cookie('is_login',True,max_age=14*24*3600)
            response.set_cookie('username',user.username,max_age=14*24*3600)
        # 7.返回响应
        return response

from django.contrib.auth import logout
class LogoutView(View):
    def get(self,request):
        # session 数据的清除
        logout(request)
        # 删除部分cookie数据
        respone=redirect(reverse('home:index'))
        respone.delete_cookie('is_login')
        # 跳转到首页
        return respone

class ForgetPasswordView(View):
    def get(self,request):
        return render(request,'forget_password.html')
    def post(self,request):
        """
        1.接收数据
        2.数据验证
            2.1判断参数是否齐全
            2.2手机号是否符合规则
            2.3判断密码是否符合规则
            2.4判断确认密码和密码是否一致
            2.5判断短信验证码是否正确
        3.根据手机号进行用户星系的查询
        4.如果手机号查询出用户信息则进行用户密码修改
        5.如果手机号未查询出用户信息则进行新用户的注册
        6.进行页面跳转
        :param request:
        :return:
        """
        # 1.接收数据
        mobile=request.POST.get('mobile')
        password=request.POST.get('password')
        password2=request.POST.get('password2')
        smscode=request.POST.get('sms_code')
        # 2.数据验证
        #     2.1判断参数是否齐全
        if not all([mobile,password,password2,smscode]):
            return HttpResponseBadRequest('参数不全')
        #     2.2手机号是否符合规则
        if re.match(r'^1[3-9]\d[9]$',mobile):
            return HttpResponseBadRequest('手机号不符合规则')
        #     2.3判断密码是否符合规则
        if re.match(r'^[0-9A-Za-z]{8-20}$',password):
            return HttpResponseBadRequest('密码不符合规则')
        #     2.4判断确认密码和密码是否一致
        if password2 !=password:
            return HttpResponseBadRequest('两次密码不一致')
        #     2.5判断短信验证码是否正确
        redis_conn=get_redis_connection('default')
        redis_sms_code=redis_conn.get('sms:%s'%mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if redis_sms_code.decode() !=smscode:
            return HttpResponseBadRequest('短信验证码错误')
        # 3.根据手机号进行用户星系的查询
        try:
            user=User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            # 5.如果手机号未查询出用户信息则进行新用户的注册
            try:
                User.objects.create_user(username=mobile,
                                     mobile=mobile,
                                     password=password)
            except Exception:
                return HttpResponseBadRequest('修改失败，请稍后再试。')
        else:
            # 4.如果手机号查询出用户信息则进行用户密码修改
            user.set_password(password)
            # 注意保存用户信息
            user.save()
        # 6.进行页面跳转
        response=redirect(reverse('users:login'))
        # 7.返回响应
        return response

from django.contrib.auth.mixins import LoginRequiredMixin

# LoginRequiredMixin
# 如果用户未登录的话，则会进行默认的跳转
# 默认的跳转链接是：accounts/login/?next=XXX
class UserCenterView(LoginRequiredMixin,View):
    def get(self,request):
        #获得登录用户的信息
        user=request.user
        # 组织获取用户的信息
        context={
            'username':user.username,
            'mobile':user.mobile,
            'avatar':user.avatar.url if user.avatar else None,
            'user_desc':user.user_desc
        }
        return render(request, 'center.html',context=context)

    def post(self,request):
        """
        1.接收参数
        2.将参数保存
        3.更新cookie中的username信息
        4.刷新当前页面（重定向操作）
        5.返回响应
        :param request:
        :return:
        """
        user=request.user
        # 1.接收参数
        username=request.POST.get('username',user.username)
        user_desc=request.POST.get('desc',user.user_desc)
        avatar=request.FILES.get('avatar')
        # 2.将参数保存
        try:
            user.username=username
            user.user_desc=user_desc
            if avatar :
                user.avatar=avatar
            user.save()
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('修改失败，请稍后再试。')
        # 3.更新cookie中的username信息
        # 4.刷新当前页面（重定向操作）
        response=redirect(reverse('users:center'))
        response.set_cookie('username',user.username,max_age=14*24*3600)
        # 5.返回响应
        return response

from home.models import ArticleCategory,Article

class WriteBlogView(LoginRequiredMixin,View):
    def get(self,request):
        #查询所有分类模型
        categories=ArticleCategory.objects.all()
        context={
            'categories':categories
        }
        return render(request,'write_blog.html',context=context)

    def post(self,request):
        """
        1.接受数据
        2.验证数据
        3.数据入库
        4.天转到指定页面（暂时首页）
        :param request:
        :return:
        """
        # 1.接受数据
        avatar=request.FILES.get('avatar')
        title=request.POST.get('title')
        category_id=request.POST.get('category')
        tags=request.POST.get('tags')
        sumary=request.POST.get('sumary')
        content=request.POST.get('content')
        user=request.user
        # 2.验证数据
        # 2.1参数是否齐全
        if not all([avatar,title,category_id,sumary,content]):
            return HttpResponseBadRequest('参数不全')
        # 2.2判断分类id
        try:
            category=ArticleCategory.objects.get(id=category_id)
        except ArticleCategory.DoesNotExist:
            return HttpResponseBadRequest('没有此分类')
        # 3.数据入库
        try:
            article=Article.objects.create(
                author=user,
                avatar=avatar,
                category=category,
                title=title,
                tags=tags,
                sumary=sumary,
                content=content
            )
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('发布失败,请稍后子再试.')
        # 4.天转到指定页面（暂时首页）
        return redirect(reverse('home:index'))