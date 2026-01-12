from django.urls import path
from .views import MinjiRunGameView

app_name = 'game'

urlpatterns = [
    path('', MinjiRunGameView.as_view(), name='minjirun'),
]
