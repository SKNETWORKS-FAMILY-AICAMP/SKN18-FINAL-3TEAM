from rest_framework import serializers
from .models import User


class ProfileSerializer(serializers.ModelSerializer):
    """
    내 프로필 조회/수정용 시리얼라이저
    """
    display_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'nickname',
            'display_name',
            'profile_image',
            'permission',
            'gender',
            'age',
            'sign_up_date',
        ]
        read_only_fields = ['id', 'email', 'permission', 'sign_up_date']


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """
    프로필 수정용 시리얼라이저
    - nickname, profile_image, gender, age만 수정 가능
    """
    class Meta:
        model = User
        fields = ['nickname', 'profile_image', 'gender', 'age']
    
    def validate_nickname(self, value):
        """닉네임 중복 체크 (자기 자신 제외)"""
        if value:
            user = self.context['request'].user
            if User.objects.filter(nickname=value).exclude(id=user.id).exists():
                raise serializers.ValidationError('이미 사용 중인 닉네임입니다.')
        return value


class ProfileImageSerializer(serializers.Serializer):
    """
    프로필 이미지 업로드용 시리얼라이저
    """
    image = serializers.ImageField()
    
    def validate_image(self, value):
        """이미지 파일 검증"""
        # 파일 크기 제한 (5MB)
        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError('이미지 크기는 5MB 이하여야 합니다.')
        
        # 확장자 검증
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
        ext = value.name.split('.')[-1].lower()
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f'허용된 확장자: {", ".join(allowed_extensions)}'
            )
        
        return value


class AdminUserSerializer(serializers.ModelSerializer):
    """
    관리자용 사용자 목록/상세 시리얼라이저
    """
    display_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'nickname',
            'display_name',
            'profile_image',
            'permission',
            'gender',
            'age',
            'sign_up_date',
            'is_active',
            'last_login',
        ]
        read_only_fields = ['id', 'email', 'sign_up_date', 'last_login']


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """
    관리자용 사용자 정보 수정 시리얼라이저
    - permission 변경 가능
    """
    class Meta:
        model = User
        fields = ['nickname', 'permission', 'is_active']

