from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from rest_framework_simplejwt.tokens import RefreshToken
from urllib.parse import urlencode
import os


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter for Google OAuth login.
    Generates JWT tokens and redirects to React frontend with tokens as URL parameters.
    """

    def on_authentication_error(
        self, request, provider, error=None, exception=None, extra_context=None
    ):
        """
        OAuth 인증 실패 시 처리 (취소 버튼 클릭, 에러 발생 등)
        기본 에러 페이지 대신 프론트엔드로 리다이렉트
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[OAuth] Authentication error - provider: {provider}, error: {error}, exception: {exception}, extra_context: {extra_context}")

        # 프론트엔드 메인 페이지로 리다이렉트 (에러 파라미터 없이)
        from django.shortcuts import redirect
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        logger.info(f"[OAuth] Redirecting to frontend due to error: {frontend_url}")
        return redirect(frontend_url)

    def populate_user(self, request, sociallogin, data):
        """
        소셜 로그인 시 사용자 정보 채우기
        - Google에서 이름을 가져와서 nickname에 저장
        """
        user = super().populate_user(request, sociallogin, data)
        # email은 Google에서 자동으로 가져옴
        
        # Google에서 이름 가져오기
        # Google OAuth는 보통 'given_name' 또는 'name' 필드를 제공
        name = (
            data.get('given_name') or 
            data.get('name') or 
            data.get('first_name')
        )
        
        # 디버깅을 위한 로깅
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Google 소셜 로그인 데이터: {data}")
        logger.info(f"가져온 이름: {name}, 현재 닉네임: {user.nickname}")
        
        # 새 사용자인 경우 또는 닉네임이 이메일 앞부분인 경우 Google 이름으로 설정
        if name:
            # 닉네임이 없거나, 닉네임이 이메일 앞부분과 같은 경우 (기본값인 경우)
            if not user.nickname or user.nickname == user.email.split('@')[0]:
                user.nickname = name
                logger.info(f"닉네임을 Google 이름으로 설정: {name}")
        
        return user

    def _generate_token_redirect_url(self, user):
        """
        Helper method to generate JWT tokens and create redirect URL
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            logger.info(f"[OAuth] Generating tokens for user: {user.email}")

            # Generate JWT refresh token using SimpleJWT
            refresh = RefreshToken.for_user(user)

            # Extract access and refresh tokens as strings
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            logger.info(f"[OAuth] Tokens generated successfully")

            # React frontend URL from environment variable
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
            logger.info(f"[OAuth] FRONTEND_URL: {frontend_url}")

            if not frontend_url.endswith('/'):
                frontend_url += '/'

            # Encode tokens as URL parameters
            params = urlencode({
                'access': access_token,
                'refresh': refresh_token,
            })

            # Return final redirect URL with tokens
            redirect_url = f"{frontend_url}?{params}"
            logger.info(f"[OAuth] Redirect URL generated: {redirect_url[:100]}...")
            return redirect_url
        except Exception as exc:
            logger.error(f"[OAuth] ERROR in _generate_token_redirect_url: {exc}", exc_info=True)
            raise

    def get_login_redirect_url(self, request):
        """
        Called after successful login (existing user)
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[OAuth] get_login_redirect_url called, user authenticated: {request.user.is_authenticated}")

        if request.user.is_authenticated:
            logger.info(f"[OAuth] User is authenticated: {request.user.email}")
            return self._generate_token_redirect_url(request.user)
        logger.warning(f"[OAuth] User is NOT authenticated, using default redirect")
        return super().get_login_redirect_url(request)

    def get_signup_redirect_url(self, request):
        """
        Called after successful signup (new user - 처음 소셜 로그인)
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[OAuth] get_signup_redirect_url called, user authenticated: {request.user.is_authenticated}")

        if request.user.is_authenticated:
            logger.info(f"[OAuth] New user signup: {request.user.email}")
            return self._generate_token_redirect_url(request.user)
        logger.warning(f"[OAuth] User is NOT authenticated during signup, using default redirect")
        return super().get_signup_redirect_url(request)

    def get_connect_redirect_url(self, request, socialaccount):
        """
        Called when connecting additional social account
        """
        user = socialaccount.user
        return self._generate_token_redirect_url(user)


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Redirect after login (including social login) with JWT tokens in querystring.
    Ensures /accounts/profile/ 404가 아니라 프런트엔드로 토큰을 실어 보냄.
    """

    def clean_username(self, username, shallow=False):
        """
        username 검증 건너뛰기
        - 우리 User 모델은 username 필드가 없음
        - email을 사용하므로 username 검증 불필요
        """
        return username  # 검증 없이 그대로 반환

    def populate_username(self, request, user):
        """
        username 생성 건너뛰기
        - 우리 User 모델은 username 필드가 없음
        """
        pass  # 아무것도 하지 않음

    def _generate_token_redirect_url(self, user):
        """
        Helper method to generate JWT tokens and create redirect URL
        """
        refresh = RefreshToken.for_user(user)
        params = urlencode(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        if not frontend_url.endswith('/'):
            frontend_url += '/'
        return f"{frontend_url}?{params}"

    def get_login_redirect_url(self, request):
        if request.user.is_authenticated:
            return self._generate_token_redirect_url(request.user)
        return super().get_login_redirect_url(request)

    def get_signup_redirect_url(self, request):
        if request.user.is_authenticated:
            return self._generate_token_redirect_url(request.user)
        return super().get_signup_redirect_url(request)
