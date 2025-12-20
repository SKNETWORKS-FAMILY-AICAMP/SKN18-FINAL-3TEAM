"""
커스텀 미들웨어
"""

class CorsMediaMiddleware:
    """
    Media 파일(/media/)에 대한 CORS 헤더 추가
    S3로 마이그레이션할 때도 프론트엔드 코드 수정 없이 사용 가능
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # /media/ 경로에 대한 요청에만 CORS 헤더 추가
        if request.path.startswith('/media/'):
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Range'
            response['Access-Control-Expose-Headers'] = 'Content-Length, Content-Range, Accept-Ranges'

        return response
