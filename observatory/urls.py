from django.urls import path
from . import views
urlpatterns=[path('',views.index),path('health/',views.health),path('api/state',views.state),path('api/connect',views.connect),path('api/chat',views.chat),path('api/new-thread',views.new_thread),path('api/refresh',views.refresh),path('api/complete-task',views.complete_task)]
