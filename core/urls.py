from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.urls import include
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app.urls')),
    path('oauth/', include('social_django.urls', namespace='social')),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)