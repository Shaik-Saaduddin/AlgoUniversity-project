from django.urls import path
from problems.views import problem_list

urlpatterns = [
    path("", problem_list, name="problem-list"),
]