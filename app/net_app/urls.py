from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('core-temp/', views.core_temp, name='core-template'),
    path('thanks/', views.thank_you, name='thank-you'),
    path('int-descriptions/', views.int_descriptions, name='int-descriptions'),
    path('ios-upgrade/', views.ios_up, name='ios-upgrade'),
    path('firewall-auto/tools/initial/', views.ini_fw_auto, name='ini-fw-auto'),
    path('firewall-auto/', views.fw_tools, name='firewall-tools'),
    path('firewall-os-upgrade/', views.fw_os_auto, name='fw-os-auto'),
]