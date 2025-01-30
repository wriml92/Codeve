from django.shortcuts import render, redirect
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib import messages
import uuid
from datetime import timedelta
from .serializers import (UserSerializer, UserProfileSerializer,
                          PasswordChangeSerializer, PasswordResetRequestSerializer,
                          PasswordResetConfirmSerializer)
from .models import User, SocialAccount, PasswordReset
from chatbots.models import ChatMessage  # ChatMessage import 경로 수정
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
import requests
from rest_framework import serializers
from .utils import generate_unique_username



class SignUpView(APIView):
    permission_classes = [AllowAny]
    template_name = 'accounts/signup.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('main2')
        return render(request, self.template_name)

    def post(self, request):
        # API 요청과 폼 제출 구분
        if request.content_type == 'application/json':
            serializer = UserSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                return Response(UserProfileSerializer(user).data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 폼 제출 처리
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        profile_image = request.FILES.get('profile_image')    
        # 필수 약관 동의 확인
        if not all([
            request.POST.get('agree_age'),
            request.POST.get('agree_terms'),
            request.POST.get('agree_privacy')
        ]):
            messages.error(request, '필수 약관에 모두 동의해주세요.')
            return redirect('accounts:signup')

        # 데이터 유효성 검사
        if not all([email, username, password, password_confirm]):
            messages.error(request, '모든 필드를 입력해주세요.')
            return redirect('accounts:signup')

        if password != password_confirm:
            messages.error(request, '비밀번호가 일치하지 않습니다.')
            return redirect('accounts:signup')

        try:
            validate_password(password)
        except ValidationError as e:
            messages.error(request, e.messages[0])
            return redirect('accounts:signup')

        # 이메일 중복 확인
        if User.objects.filter(email=email).exists():
            messages.error(request, '이미 사용 중인 이메일입니다.')
            return redirect('accounts:signup')

        # 닉네임 중복 확인
        if User.objects.filter(username=username).exists():
            messages.error(request, '이미 사용 중인 닉네임입니다.')
            return redirect('accounts:signup')

        # 사용자 생성
        try:
            user = User.objects.create_user(
                email=email,
                username=username,
                password=password
            )
            # 프로필 이미지 처리
            if profile_image:
                user.profile_image = profile_image
                user.save()
            # 이메일 인증 토큰 생성 및 메일 발송
            verification_token = str(uuid.uuid4())
            # TODO: 이메일 발송 로직 구현

            messages.success(request, '회원가입이 완료되었습니다. 이메일 인증을 진행해주세요.')
            return redirect('accounts:login')

        except Exception as e:
            messages.error(request, '회원가입 중 오류가 발생했습니다.')
            return redirect('accounts:signup')


class LoginView(APIView):
    permission_classes = [AllowAny]
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('main')
        return render(request, self.template_name)

    def post(self, request):
        # 폼 제출 처리
        if not request.content_type == 'application/json':
            email = request.POST.get('email')
            password = request.POST.get('password')
            next_url = request.POST.get('next') or request.GET.get('next')

            if not email or not password:
                messages.error(request, '이메일과 비밀번호를 모두 입력해주세요.')
                return redirect('accounts:login')

            user = authenticate(request, email=email, password=password)
            if not user:
                messages.error(request, '이메일 또는 비밀번호가 올바르지 않습니다.')
                return redirect('accounts:login')

            if user.is_account_locked():
                messages.error(request, '계정이 잠겼습니다. 30분 후에 다시 시도해주세요.')
                return redirect('accounts:login')

            login(request, user)
            user.reset_login_attempts()
            messages.success(request, '로그인되었습니다.')

            # next 파라미터가 있으면 해당 URL로 리다이렉트
            if next_url:
                return redirect(next_url)
            # 기본적으로 Python 코스 페이지로 리다이렉트
            return redirect('courses:course-list')

        # API 요청 처리
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': '이메일과 비밀번호를 모두 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, email=email, password=password)
        if not user:
            if user := User.objects.filter(email=email).first():
                user.increment_login_attempts()
            return Response(
                {'error': '이메일 또는 비밀번호가 올바르지 않습니다.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if user.is_account_locked():
            return Response(
                {'error': '계정이 잠겼습니다. 30분 후에 다시 시도해주세요.'},
                status=status.HTTP_403_FORBIDDEN
            )

        login(request, user)
        user.reset_login_attempts()
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        messages.success(request, '로그아웃되었습니다.')

        response = redirect('main')
        response.delete_cookie('chatHistory')  # 쿠키도 함께 삭제

        # JavaScript 실행을 위한 스크립트 추가
        response.content = """
            <script>
                localStorage.removeItem('chatHistory');
                window.location.href = '/';
            </script>
        """
        return response


def google_login(request):
    return redirect(
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_OAUTH2_KEY}&"
        f"response_type=code&"
        f"redirect_uri={settings.GOOGLE_OAUTH2_REDIRECT_URI}&"
        f"scope={settings.GOOGLE_SCOPE_USERINFO}"
    )

def google_callback(request):
    code = request.GET.get("code")

    token_req = requests.post(
        f"https://oauth2.googleapis.com/token?"
        f"client_id={settings.GOOGLE_OAUTH2_KEY}&"
        f"client_secret={settings.GOOGLE_OAUTH2_SECRET}&"
        f"code={code}&"
        f"grant_type=authorization_code&"
        f"redirect_uri={settings.GOOGLE_OAUTH2_REDIRECT_URI}"
    )
    token_req_json = token_req.json()

    error = token_req_json.get("error")
    if error:
        raise serializers.ValidationError({"error": f"Google Token Error: {error}"})

    google_access_token = token_req_json.get("access_token")

    email_response = requests.get(
        f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={google_access_token}"
    )
    res_status = email_response.status_code

    if res_status != 200:
        raise serializers.ValidationError({"error": "Bad Request: Invalid response status from server."})

    email_res_json = email_response.json()
    email = email_res_json.get("email")
    user_id = email_res_json.get("user_id")

    if not email or not user_id:
        raise serializers.ValidationError({"error": "Invalid user information from Google."})

    try:
        social_account = SocialAccount.objects.get(
            provider="google",
            social_id=user_id
        )
        user = social_account.user
        social_account.access_token = google_access_token
        social_account.save()

    except SocialAccount.DoesNotExist:
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
        else:
            username = generate_unique_username(email)
            user = User.objects.create_user(
                email=email,
                username=username,
                google_id=user_id,
                is_email_verified=True
            )
        SocialAccount.objects.create(
            user=user,
            provider="google",
            social_id=user_id,
            access_token=google_access_token
        )

    login(request, user)
    return redirect('main')


#-----------------
# 깃허브
#-----------------

def github_login(request):
    return redirect(
        f"https://github.com/login/oauth/authorize?"
        f"client_id={settings.GITHUB_OAUTH2_KEY}&"
        f"user:emailstate=state_parameter&"
        f"redirect_uri={settings.GITHUB_OAUTH2_REDIRECT_URI}&"
        f"scope=read:user"
    )

def github_callback(request):
    code = request.GET.get("code")

    response = requests.post(
        url="https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.GITHUB_OAUTH2_KEY,
            "client_secret": settings.GITHUB_OAUTH2_SECRET,
            "code": code,
            "redirect_uri": settings.GITHUB_OAUTH2_REDIRECT_URI,
        },
    )
    token_req_json = response.json()

    error = token_req_json.get("error")
    if error:
        raise serializers.ValidationError({"error": f"Github Token Error: {error}"})

    github_access_token = token_req_json.get("access_token")

    email_response = requests.get(
        f"https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {github_access_token}"
        }
        
    )
    res_status = email_response.status_code

    if res_status != 200:
        raise serializers.ValidationError({"error": "Bad Request: Invalid response status from server."})

    email_res_json = email_response.json()

    user_id = email_res_json.get("id")
    email = email_res_json.get("email")

    if not user_id or not email:
        raise serializers.ValidationError({"error": "Invalid user information from Github."})

    try:
        social_account = SocialAccount.objects.get(
            provider="github",
            social_id=user_id
        )
        user = social_account.user
        social_account.access_token = github_access_token
        social_account.save()

    except SocialAccount.DoesNotExist:
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
        else:
            username = generate_unique_username(email)
            user = User.objects.create_user(
                email=email,
                username=username,
                google_id=user_id,
                is_email_verified=True
            )
        SocialAccount.objects.create(
            user=user,
            provider="github",
            social_id=user_id,
            access_token=github_access_token
        )

    login(request, user)
    return redirect('main')


#-----------------
# 네이버
#-----------------
def naver_login(request):
    return redirect(
        f"https://nid.naver.com/oauth2.0/authorize?"
        f"response_type=code&"
        f"client_id={settings.NAVER_OAUTH2_KEY}&"
        f"state=state_parameter&"
        f"redirect_uri={settings.NAVER_OAUTH2_REDIRECT_URI}"
    )


def naver_callback(request):
    code = request.GET.get("code")
    state = request.GET.get("state")

    response = requests.post(
        url="https://nid.naver.com/oauth2.0/token",
        headers={"Accept": "application/json"},
        data={
            "grant_type": "authorization_code",
            "client_id": settings.NAVER_OAUTH2_KEY,
            "client_secret": settings.NAVER_OAUTH2_SECRET,
            "code": code,
            "state": state,
            "redirect_uri": settings.NAVER_OAUTH2_REDIRECT_URI,
        },
    )
    token_req_json = response.json()

    error = token_req_json.get("error", None)
    if error:
        raise serializers.ValidationError({"error": f"Naver Token Error: {error}"})

    naver_access_token = token_req_json.get("access_token")

    user_info_response = requests.get(
        "https://openapi.naver.com/v1/nid/me",
        headers={"Authorization": f"Bearer {naver_access_token}"}
    )

    if user_info_response.status_code != 200:
        raise serializers.ValidationError({"error": "Invalid response from Naver API"})

    user_info_json = user_info_response.json().get("response", {})
    user_id = user_info_json.get("id")
    email = user_info_json.get("email")

    if not user_id or not email:
        raise serializers.ValidationError({"error": "Invalid user information from Naver"})

    try:
        social_account = SocialAccount.objects.get(provider="naver", social_id=user_id)
        user = social_account.user
        social_account.access_token = naver_access_token
        social_account.save()

    except SocialAccount.DoesNotExist:
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
        else:
            username = generate_unique_username(email)
            user = User.objects.create_user(
                email=email,
                username=username,
                is_email_verified=True
            )
        SocialAccount.objects.create(
            user=user,
            provider="naver",
            social_id=user_id,
            access_token=naver_access_token
        )

    login(request, user)
    return redirect("main")



#-----------------
# 카카오
#-----------------


def kakao_login(request):
    return redirect(
        f"https://kauth.kakao.com/oauth/authorize?"
        f"client_id={settings.KAKAO_OAUTH2_KEY }&"
        f"response_type=code&"
        f"redirect_uri={settings.KAKAO_OAUTH2_REDIRECT_URI}"
    )

def kakao_callback(request):
    code = request.GET.get("code")

    response = requests.post(
        url="https://kauth.kakao.com/oauth/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "authorization_code",
            "client_id": settings.KAKAO_OAUTH2_KEY,
            "client_secret": settings.KAKAO_OAUTH2_SECRET,
            "code": code,
            "redirect_uri": settings.KAKAO_OAUTH2_REDIRECT_URI,
        },
    )

    token_req_json = response.json()

    error = token_req_json.get("error", None)
    if error:
        raise serializers.ValidationError({"error": f"Kakao Token Error: {error}"})

    kakao_access_token = token_req_json.get("access_token")

    user_info_response = requests.get(
        "https://kapi.kakao.com/v2/user/me",
        headers={"Authorization": f"Bearer {kakao_access_token}"}
    )

    if user_info_response.status_code != 200:
        raise serializers.ValidationError({"error": "Invalid response from Kakao API"})

    user_info_json = user_info_response.json()
    user_id = user_info_json.get("id")
    kakao_account = user_info_json.get("kakao_account", {})
    email = kakao_account.get("email")

    if not user_id or not email:
        raise serializers.ValidationError({"error": "Invalid user information from Kakao"})

    try:
        social_account = SocialAccount.objects.get(provider="kakao", social_id=user_id)
        user = social_account.user
        social_account.access_token = kakao_access_token
        social_account.save()

    except SocialAccount.DoesNotExist:
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
        else:
            username = generate_unique_username(email)
            user = User.objects.create_user(
                email=email,
                username=username,
                is_email_verified=True
            )
        SocialAccount.objects.create(
            user=user,
            provider="kakao",
            social_id=user_id,
            access_token=kakao_access_token
        )

    login(request, user)
    return redirect("main")

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({'error': '현재 비밀번호가 올바르지 않습니다.'},
                                status=status.HTTP_400_BAD_REQUEST)

            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': '비밀번호가 변경되었습니다.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.filter(
                email=email, is_email_verified=True).first()

            # 이메일이 존재하고 인증된 경우에만 실제로 이메일 발송
            if user:
                try:
                    # 토큰 생성 및 저장
                    token = str(uuid.uuid4())
                    expires_at = timezone.now() + timedelta(hours=24)
                    PasswordReset.objects.create(
                        user=user,
                        token=token,
                        expires_at=expires_at
                    )

                    reset_url = f"http://localhost:8000/accounts/password-reset-confirm/{token}/"

                    # 이메일 발송
                    email_sent = send_mail(
                        subject='Codeve - 비밀번호 재설정',
                        message=f'''안녕하세요, {user.username}님.

                        비밀번호 재설정 요청이 있었습니다.
                        아래 링크를 클릭하여 새로운 비밀번호를 설정해주세요:

                        {reset_url}

                        본인이 요청하지 않았다면 이 이메일을 무시하셔도 됩니다.
                        계정의 비밀번호는 변경되지 않은 상태로 유지됩니다.

                        감사합니다.
                        Codeve 팀 드림''',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )

                    if email_sent == 0:  # 이메일 발송 실패
                        return Response(
                            {'error': '이메일 발송에 실패했습니다. 잠시 후 다시 시도해주세요.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )

                except Exception as e:
                    return Response(
                        {'error': '이메일 발송 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

            # 이메일 존재 여부와 관계없이 동일한 메시지 반환
            return Response({
                'message': '입력하신 이메일 주소로 비밀번호 재설정 안내를 발송했습니다. 메일이 오지 않은 경우 스팸함을 확인해주세요.'
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            password_reset = PasswordReset.objects.filter(token=token).first()

            if not password_reset or not password_reset.is_valid():
                return Response({'error': '유효하지 않거나 만료된 토큰입니다.'},
                                status=status.HTTP_400_BAD_REQUEST)

            user = password_reset.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()

            password_reset.is_used = True
            password_reset.save()

            return Response({'message': '비밀번호가 재설정되었습니다.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyPageView(APIView):
    permission_classes = [IsAuthenticated]
    template_name = 'accounts/additional-info.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        nickname = request.POST.get('nickname')
        profile_image = request.FILES.get('profile_image')
        user = request.user
        changed = False
        
        if nickname:
            if user.username == nickname:
                messages.warning(request, '현재 닉네임과 동일합니다.')
            elif User.objects.filter(username=nickname).exists():
                messages.error(request, '이미 사용 중인 닉네임입니다.')    
            else:
                user.username = nickname
                changed = True
        if profile_image:
            user.profile_image = profile_image
            changed = True
        if changed:
            user.save()
            messages.success(request, '프로필이 성공적으로 수정되었습니다.')
        return redirect('accounts:my_page')


class DeleteAccountView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            user = request.user

            # 1. 소셜 계정 연동 정보 삭제
            SocialAccount.objects.filter(user=user).delete()

            # 2. 채팅 메시지 삭제
            ChatMessage.objects.filter(user=user).delete()

            # 3. 비밀번호 재설정 토큰 삭제
            PasswordReset.objects.filter(user=user).delete()

            # 4. 사용자 계정 삭제 전에 로그아웃 처리
            logout(request)

            # 5. 사용자 계정 삭제
            user.delete()

            messages.success(request, '회원 탈퇴가 완료되었습니다.')
            return redirect('main')

        except ChatMessage.DoesNotExist:
            # 채팅 메시지가 없는 경우 무시하고 계속 진행
            pass
        except Exception as e:
            print(f"회원 탈퇴 중 오류 발생: {str(e)}")  # 콘솔에 오류 출력
            messages.error(request, '회원 탈퇴 중 오류가 발생했습니다. 다시 시도해주세요.')
            return redirect('accounts:my_page')
