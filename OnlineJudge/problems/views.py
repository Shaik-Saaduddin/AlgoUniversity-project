from django import template
from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

def home_page(request):
    return render(request, 'homepage.html')

def problem_list(request):
    return render(request, 'problemList.html')