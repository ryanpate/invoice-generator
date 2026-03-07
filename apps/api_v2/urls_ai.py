from django.urls import path

from apps.api_v2.views.ai import ai_generate_view, ai_voice_generate_view

urlpatterns = [
    path('generate/', ai_generate_view, name='ai-generate'),
    path('voice-generate/', ai_voice_generate_view, name='ai-voice-generate'),
]
