from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_page, name='home-page'),
    path('list/', views.problem_list, name='problem-list'),
    path('<int:problem_id>/', views.problem_detail, name='problem-detail'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),

    path('manage/', views.admin_problems_list, name='admin_problems_list'),
    path('manage/add/', views.admin_add_problem, name='admin_add_problem'),
    path('manage/<int:problem_id>/edit/', views.admin_edit_problem, name='admin_edit_problem'),
    path('manage/<int:problem_id>/delete/', views.admin_delete_problem, name='admin_delete_problem'),
    
    # AI Assist endpoint
    path('<int:problem_id>/assist/', views.ai_assist, name='ai_assist'),
]
