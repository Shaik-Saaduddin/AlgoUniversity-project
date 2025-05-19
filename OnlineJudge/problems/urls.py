from django.urls import path
from problems.views import problem_list, home_page, problem_detail

urlpatterns = [
    path("problemlist/", problem_list, name="problem-list"),
    path('',home_page, name="home-page"),
    path('problems/<int:problem_id>/', problem_detail, name='problem-detail'),
]