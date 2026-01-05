from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class UserManager(BaseUserManager):
    """
    커스텀 User 모델 매니저
    - 소셜 로그인 사용자: set_unusable_password()
    - 관리자: set_password()
    """
    
    def create_user(self, email, **extra_fields):
        """
        일반 사용자 생성 (소셜 로그인용 - 패스워드 없음)
        allauth가 소셜 로그인 시 이 메서드 호출
        """
        if not email:
            raise ValueError('이메일은 필수입니다')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_unusable_password()  # 소셜 로그인 전용 - 패스워드 로그인 불가
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        관리자 생성 (Django createsuperuser 명령어용)
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('permission', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # 관리자는 패스워드 설정
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    """
    init.sql 기반 커스텀 User 모델
    
    init.sql 테이블: "user"
    Django가 테이블 생성 및 마이그레이션 관리
    allauth의 socialaccount 테이블들이 이 모델을 참조
    """
    
    # Django 기본 권한 시스템 비활성화
    # - 우리는 permission 필드로 직접 권한 관리
    # - user_groups, user_user_permissions 테이블 불필요
    groups = None
    user_permissions = None
    
    PERMISSION_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
    ]
    
    # init.sql 필드들 (id는 Django 기본 pk 사용)
    nickname = models.CharField(
        max_length=30, 
        unique=True,
        null=True, 
        blank=True,
        verbose_name='닉네임'
    )
    profile_image = models.TextField(
        null=True,
        blank=True,
        verbose_name='프로필 이미지 URL'
    )
    sign_up_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='가입일'
    )
    email = models.EmailField(
        max_length=255, 
        unique=True,
        verbose_name='이메일'
    )
    permission = models.CharField(
        max_length=50, 
        choices=PERMISSION_CHOICES, 
        default='user',
        verbose_name='권한'
    )
    gender = models.BooleanField(
        null=True, 
        blank=True,
        verbose_name='성별'
    )
    age = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(120)],
        verbose_name='나이'
    )
    
    # Django 인증 시스템 필수 필드
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성화 여부'
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name='스태프 여부'
    )
    
    # 커스텀 매니저
    objects = UserManager()
    
    # 로그인에 사용할 필드
    USERNAME_FIELD = 'email'
    
    # createsuperuser 시 추가 입력 필드 (email은 자동)
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'user'
        managed = True  # Django가 테이블 생성 및 마이그레이션 관리
        verbose_name = '사용자'
        verbose_name_plural = '사용자들'
    
    def __str__(self):
        return self.email
    
    @property
    def display_name(self):
        """닉네임이 없으면 이메일 앞부분 반환"""
        return self.nickname or self.email.split('@')[0]
    
    @property
    def is_admin(self):
        """관리자 여부 확인"""
        return self.permission == 'admin'
