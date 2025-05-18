from django.urls import path
from problems.views import problem_list, home_page

urlpatterns = [
    path("problemlist/", problem_list, name="problem-list"),
    path('',home_page, name="home-page")
]