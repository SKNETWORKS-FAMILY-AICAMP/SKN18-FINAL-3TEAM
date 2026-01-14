"""
S3 Storage Backends for Django

각 버킷별로 별도의 스토리지 클래스 제공:
- ProfileStorage: 프로필 이미지용 (skn18-3-dev-profiles)
- VideoStorage: 영상 파일용 (skn18-3-dev-videos)
- ThumbnailStorage: 썸네일 이미지용 (skn18-3-dev-thumbnails)
"""
import os
import uuid
import boto3
from botocore.exceptions import ClientError
from django.conf import settings


def get_s3_client():
    """S3 클라이언트 생성 (ECS Task Role 또는 환경변수 인증)"""
    # ECS Task Role 사용 시 자격 증명이 자동으로 제공됨
    # 로컬 테스트용으로 환경변수 인증도 지원
    kwargs = {
        'region_name': getattr(settings, 'AWS_S3_REGION_NAME', 'ap-northeast-2')
    }

    # 환경변수에 AWS 자격 증명이 있으면 사용 (로컬 테스트용)
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
        kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY

    return boto3.client('s3', **kwargs)


def upload_to_s3(file_obj, bucket_name, key, content_type=None):
    """
    파일을 S3에 업로드

    Args:
        file_obj: 업로드할 파일 객체 (Django UploadedFile 또는 bytes)
        bucket_name: S3 버킷 이름
        key: S3 객체 키 (경로/파일명)
        content_type: MIME 타입 (선택)

    Returns:
        str: 업로드된 파일의 S3 URL
        None: 업로드 실패 시
    """
    try:
        s3_client = get_s3_client()

        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type

        # Django UploadedFile인 경우
        if hasattr(file_obj, 'read'):
            s3_client.upload_fileobj(file_obj, bucket_name, key, ExtraArgs=extra_args)
        else:
            # bytes인 경우
            s3_client.put_object(Body=file_obj, Bucket=bucket_name, Key=key, **extra_args)

        # S3 URL 반환
        region = getattr(settings, 'AWS_S3_REGION_NAME', 'ap-northeast-2')
        return f"https://{bucket_name}.s3.{region}.amazonaws.com/{key}"

    except ClientError as e:
        print(f"S3 업로드 실패: {e}")
        return None


def delete_from_s3(bucket_name, key):
    """
    S3에서 파일 삭제

    Args:
        bucket_name: S3 버킷 이름
        key: S3 객체 키

    Returns:
        bool: 삭제 성공 여부
    """
    try:
        s3_client = get_s3_client()
        s3_client.delete_object(Bucket=bucket_name, Key=key)
        return True
    except ClientError as e:
        print(f"S3 삭제 실패: {e}")
        return False


def extract_s3_key_from_url(url, bucket_name):
    """
    S3 URL에서 객체 키 추출

    Args:
        url: S3 전체 URL
        bucket_name: 버킷 이름

    Returns:
        str: 객체 키 (예: "profiles/user_1_abc123.jpg")
        None: 파싱 실패 시
    """
    if not url:
        return None

    region = getattr(settings, 'AWS_S3_REGION_NAME', 'ap-northeast-2')
    prefix = f"https://{bucket_name}.s3.{region}.amazonaws.com/"

    if url.startswith(prefix):
        return url[len(prefix):]

    # 경로만 저장된 경우
    if not url.startswith('http'):
        return url

    return None


# ============================================
# 프로필 이미지 관련 함수
# ============================================
def upload_profile_image(file_obj, user_id, filename=None):
    """
    프로필 이미지를 S3에 업로드

    Args:
        file_obj: 업로드할 이미지 파일
        user_id: 사용자 ID
        filename: 원본 파일명 (확장자 추출용)

    Returns:
        str: S3 URL 또는 로컬 경로
    """
    if not getattr(settings, 'USE_S3', False):
        # 로컬 저장소 사용 (기존 로직)
        return None

    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME_PROFILES', 'skn18-3-dev-profiles')

    # 파일명 생성
    ext = filename.split('.')[-1].lower() if filename else 'jpg'
    key = f"profiles/user_{user_id}_{uuid.uuid4().hex[:8]}.{ext}"

    # Content-Type 결정
    content_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp',
    }
    content_type = content_types.get(ext, 'image/jpeg')

    return upload_to_s3(file_obj, bucket_name, key, content_type)


def delete_profile_image(url_or_path):
    """
    프로필 이미지를 S3에서 삭제

    Args:
        url_or_path: S3 URL 또는 로컬 경로

    Returns:
        bool: 삭제 성공 여부
    """
    if not getattr(settings, 'USE_S3', False):
        return False

    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME_PROFILES', 'skn18-3-dev-profiles')
    key = extract_s3_key_from_url(url_or_path, bucket_name)

    if key:
        return delete_from_s3(bucket_name, key)
    return False


# ============================================
# 영상 파일 관련 함수
# ============================================
def upload_video(file_obj, filename=None, video_id=None):
    """
    영상 파일을 S3에 업로드

    Args:
        file_obj: 업로드할 영상 파일 (bytes 또는 file object)
        filename: 파일명
        video_id: 영상 ID (선택)

    Returns:
        str: S3 URL
    """
    if not getattr(settings, 'USE_S3', False):
        return None

    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME_VIDEOS', 'skn18-3-dev-final-videos')

    # 파일명 생성
    ext = filename.split('.')[-1].lower() if filename else 'mp4'
    unique_id = video_id or uuid.uuid4().hex[:12]
    key = f"videos/{unique_id}_{uuid.uuid4().hex[:8]}.{ext}"

    # Content-Type 결정
    content_types = {
        'mp4': 'video/mp4',
        'webm': 'video/webm',
        'mov': 'video/quicktime',
        'avi': 'video/x-msvideo',
    }
    content_type = content_types.get(ext, 'video/mp4')

    return upload_to_s3(file_obj, bucket_name, key, content_type)


def delete_video(url_or_path):
    """영상 파일을 S3에서 삭제"""
    if not getattr(settings, 'USE_S3', False):
        return False

    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME_VIDEOS', 'skn18-3-dev-final-videos')
    key = extract_s3_key_from_url(url_or_path, bucket_name)

    if key:
        return delete_from_s3(bucket_name, key)
    return False


# ============================================
# 썸네일 이미지 관련 함수
# ============================================
def upload_thumbnail(file_obj, filename=None, video_id=None):
    """
    썸네일 이미지를 S3에 업로드

    Args:
        file_obj: 업로드할 이미지 파일 (bytes 또는 file object)
        filename: 파일명
        video_id: 영상 ID (선택)

    Returns:
        str: S3 URL
    """
    if not getattr(settings, 'USE_S3', False):
        return None

    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME_THUMBNAILS', 'skn18-3-dev-thumbnails')

    # 파일명 생성
    ext = filename.split('.')[-1].lower() if filename else 'jpg'
    unique_id = video_id or uuid.uuid4().hex[:12]
    key = f"thumbnails/{unique_id}_{uuid.uuid4().hex[:8]}.{ext}"

    # Content-Type 결정
    content_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp',
    }
    content_type = content_types.get(ext, 'image/jpeg')

    return upload_to_s3(file_obj, bucket_name, key, content_type)


def delete_thumbnail(url_or_path):
    """썸네일 이미지를 S3에서 삭제"""
    if not getattr(settings, 'USE_S3', False):
        return False

    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME_THUMBNAILS', 'skn18-3-dev-thumbnails')
    key = extract_s3_key_from_url(url_or_path, bucket_name)

    if key:
        return delete_from_s3(bucket_name, key)
    return False
