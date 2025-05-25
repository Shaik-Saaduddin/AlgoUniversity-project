from django.urls import path
from . import views

urlpatterns = [
    path('', views.compiler_form, name='compiler'),
    path('run/', views.run_code, name='run-code'),
    path('result/', views.result, name='result'),
    path('submissions/', views.all_submissions, name='all-submissions'),
    path('submissions/<int:user_id>/', views.user_submissions, name='user-submissions'),
    path('submission/<int:submission_id>/', views.submission_detail, name='submission-detail'),
]
