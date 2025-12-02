from django.urls import path
from . import views

urlpatterns = [
    path('', views.mypage_main, name='mypage'),
]
