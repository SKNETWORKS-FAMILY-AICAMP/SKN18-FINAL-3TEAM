from django.shortcuts import render
from django.views.generic import TemplateView


class MinjiRunGameView(TemplateView):
    """MinjiRun WebGL 게임 뷰"""
    template_name = 'game/minjirun.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['game_title'] = 'MinjiRun - 경복궁 런게임'
        return context
