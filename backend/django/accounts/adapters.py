from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from rest_framework_simplejwt.tokens import RefreshToken
from urllib.parse import urlencode


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter for Google OAuth login.
    Generates JWT tokens and redirects to React frontend with tokens as URL parameters.
    """

    def _generate_token_redirect_url(self, user):
        """
        Helper method to generate JWT tokens and create redirect URL
        """
        # Generate JWT refresh token using SimpleJWT
        refresh = RefreshToken.for_user(user)

        # Extract access and refresh tokens as strings
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # React frontend URL
        frontend_url = "http://localhost:3000/"

        # Encode tokens as URL parameters
        params = urlencode({
            'access': access_token,
            'refresh': refresh_token,
        })

        # Return final redirect URL: http://localhost:3000/?access=xxx&refresh=yyy
        return f"{frontend_url}?{params}"

    def get_login_redirect_url(self, request):
        """
        Called after successful login (existing user)
        """
        if request.user.is_authenticated:
            return self._generate_token_redirect_url(request.user)
        return super().get_login_redirect_url(request)

    def get_signup_redirect_url(self, request):
        """
        Called after successful signup (new user - 처음 소셜 로그인)
        """
        if request.user.is_authenticated:
            return self._generate_token_redirect_url(request.user)
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
        frontend_url = "http://localhost:3000/"
        return f"{frontend_url}?{params}"

    def get_login_redirect_url(self, request):
        if request.user.is_authenticated:
            return self._generate_token_redirect_url(request.user)
        return super().get_login_redirect_url(request)

    def get_signup_redirect_url(self, request):
        if request.user.is_authenticated:
            return self._generate_token_redirect_url(request.user)
        return super().get_signup_redirect_url(request)
