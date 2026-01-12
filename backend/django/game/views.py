from django.shortcuts import render
from django.views.generic import TemplateView
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from pathlib import Path
import os


@method_decorator(xframe_options_exempt, name='dispatch')
class MinjiRunGameView(TemplateView):
    """MinjiRun WebGL 게임 뷰"""
    template_name = 'game/minjirun.html'


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['game_title'] = 'MinjiRun - 경복궁 런게임'

        # WebGL 빌드 파일 자동 감지
        build_info = self._detect_build_files()
        context.update(build_info)

        return context

    def _detect_build_files(self):
        """
        Unity WebGL 빌드 폴더에서 실제 빌드 파일명을 자동으로 감지합니다.
        빌드 이름이 'WebGL', 'MinjiRun', 'Build' 등 어떤 이름이든 자동으로 찾습니다.
        """
        # static/game/webgl/Build 폴더 경로
        webgl_static_path = Path(settings.BASE_DIR) / 'game' / 'static' / 'game' / 'webgl' / 'Build'

        build_info = {
            'build_found': False,
            'build_name': 'WebGL',  # 기본값
            'has_brotli': False,
            'has_gzip': False,
            'compression': '',  # 압축 확장자 (.br, .gz, 또는 빈 문자열)
        }

        if not webgl_static_path.exists():
            return build_info

        # Build 폴더에서 .loader.js 파일 찾기
        loader_files = list(webgl_static_path.glob('*.loader.js'))

        if loader_files:
            # 파일명에서 빌드 이름 추출 (예: "WebGL.loader.js" -> "WebGL")
            loader_file = loader_files[0]
            build_name = loader_file.stem.replace('.loader', '')
            build_info['build_name'] = build_name
            build_info['build_found'] = True

            # 압축 형식 확인
            data_br = webgl_static_path / f'{build_name}.data.br'
            data_gz = webgl_static_path / f'{build_name}.data.gz'

            if data_br.exists():
                build_info['has_brotli'] = True
                build_info['compression'] = '.br'
            elif data_gz.exists():
                build_info['has_gzip'] = True
                build_info['compression'] = '.gz'
            else:
                # 압축 없음
                build_info['compression'] = ''

        return build_info
