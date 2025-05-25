from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_page, name='home-page'),
    path('list/', views.problem_list, name='problem-list'),
    path('<int:problem_id>/', views.problem_detail, name='problem-detail'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
]
