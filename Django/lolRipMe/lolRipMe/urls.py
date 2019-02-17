from django.contrib import admin
from django.urls import path, re_path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pages.urls')),
    path('microsoft/', include('microsoft_auth.urls', namespace='microsoft')),
    ]
