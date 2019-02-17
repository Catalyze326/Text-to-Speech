from django.urls import path, re_path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', views.about, name='home'),
    # path('about/', views.about, name='about'),
    path('login/', views.login, name='login'),
    path('read/', views.read, name='read'),
    path('text/', views.text, name='text'),
    path('upload/', views.model_form_upload, name='upload'),
   ]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
