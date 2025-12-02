from django.urls import path
from . import views

urlpatterns = [
    path('<int:video_id>/', views.video_page, name='video_page'),
]
