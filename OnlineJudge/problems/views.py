from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def problem_list(request):
    return HttpResponse("List of problems")