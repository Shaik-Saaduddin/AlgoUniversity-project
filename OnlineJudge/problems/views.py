from django import template
from django.shortcuts import render
from django.http import HttpResponse
from problems.models import Problem

# Create your views here.

def home_page(request):
    return render(request, 'homepage.html')

def problem_list(request):
    problems = Problem.objects.all()
    return render(request, 'problemList.html', {'problems': problems})