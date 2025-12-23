from rest_framework import serializers
from video.models import Video


class VideoSearchSerializer(serializers.ModelSerializer):
    """
    검색 결과용 영상 Serializer
    """
    class Meta:
        model = Video
        fields = [
            'id',
            'title',
            'video_url',
            'thumbnail_url',
            'upload_date',
            'tags',
            'likes_count',
            'comments_count'
        ]
        read_only_fields = fields
