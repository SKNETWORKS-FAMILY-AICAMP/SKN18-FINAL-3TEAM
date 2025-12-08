from django.urls import path
from . import views

urlpatterns = [
    # 유니티가 /api/generate 로 접속하면 views.generate_scenario 실행
    path('generate', views.generate_scenario, name='generate_scenario'),
]
