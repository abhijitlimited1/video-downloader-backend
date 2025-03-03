from django.urls import path
from . import views

urlpatterns = [
    path('fetch-video-info/', views.fetch_video_info, name='fetch_video_info'),
    path('stream-video/',views.stream_video, name='stream-video'),
]

