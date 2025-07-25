from django.conf import settings
from django.conf.urls.static import static
from django.urls import include
from django.contrib.auth.views import LoginView, LogoutView
from app.views import home,table_menu
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from app.views import register


urlpatterns = [
    path('', include('app.urls', namespace='restaurant')),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', register, name='register'),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)