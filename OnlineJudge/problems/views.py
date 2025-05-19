from django import template
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from problems.models import Problem

# Create your views here.

def home_page(request):
    return render(request, 'homepage.html')

def problem_list(request):
    problems = Problem.objects.all()
    return render(request, 'problemList.html', {'problems': problems})

def problem_detail(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    return render(request, 'problem.html', {'problem': problem})