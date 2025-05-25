from django import template
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.db.models import Count, Q
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from problems.models import Problem, TestCase
from compiler.forms import CodeSubmissionForm
from compiler.models import CodeSubmission
from .forms import ProblemForm, TestCaseFormSet
import random
from datetime import date

# Create your views here.

def get_problem_of_the_day():
    """
    Get the problem of the day based on current date.
    Uses date as seed to ensure same problem for entire day.
    """
    problems = Problem.objects.all()
    if not problems.exists():
        return None
    
    # Use current date as seed for consistent daily selection
    today = date.today()
    seed = today.year * 10000 + today.month * 100 + today.day
    random.seed(seed)
    
    # Select a random problem based on the seed
    problem_index = random.randint(0, problems.count() - 1)
    return problems[problem_index]

def home_page(request):
    # Get top 5 users for the leaderboard
    top_users = User.objects.annotate(
        solved_count=Count(
            'submissions__problem', 
            filter=Q(submissions__is_correct=True),
            distinct=True
        )
    ).order_by('-solved_count')[:5]
    
    # Get problem of the day
    problem_of_the_day = get_problem_of_the_day()
    
    # Check if current user has solved the problem of the day
    user_solved_potd = False
    if request.user.is_authenticated and problem_of_the_day:
        user_solved_potd = CodeSubmission.objects.filter(
            user=request.user,
            problem=problem_of_the_day,
            is_correct=True
        ).exists()
    
    return render(request, 'homepage.html', {
        'top_users': top_users,
        'problem_of_the_day': problem_of_the_day,
        'user_solved_potd': user_solved_potd
    })

def problem_list(request):
    problems = Problem.objects.all()
    return render(request, 'problemList.html', {'problems': problems})

def problem_detail(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    form = CodeSubmissionForm()
    return render(request, 'problem.html', {'problem': problem, 'form': form})

def leaderboard(request):
    # Get all users with their solved problem count
    users = User.objects.annotate(
        solved_count=Count(
            'submissions__problem', 
            filter=Q(submissions__is_correct=True),
            distinct=True
        )
    ).order_by('-solved_count')
    
    return render(request, 'leaderboard.html', {'users': users})

# Admin-only views
def is_admin(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(is_admin)
def admin_problems_list(request):
    problems = Problem.objects.all().order_by('-id')
    
    # Add pagination
    paginator = Paginator(problems, 10)  # Show 10 problems per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'admin_problems_list.html', {'page_obj': page_obj})

@user_passes_test(is_admin)
def admin_add_problem(request):
    if request.method == 'POST':
        problem_form = ProblemForm(request.POST)
        testcase_formset = TestCaseFormSet(request.POST)
        
        if problem_form.is_valid() and testcase_formset.is_valid():
            problem = problem_form.save()
            testcase_formset.instance = problem
            testcase_formset.save()
            
            messages.success(request, f'Problem "{problem.title}" has been created successfully!')
            return redirect('admin_problems_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        problem_form = ProblemForm()
        testcase_formset = TestCaseFormSet()
    
    return render(request, 'admin_add_problem.html', {
        'problem_form': problem_form,
        'testcase_formset': testcase_formset
    })

@user_passes_test(is_admin)
def admin_edit_problem(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    
    if request.method == 'POST':
        problem_form = ProblemForm(request.POST, instance=problem)
        testcase_formset = TestCaseFormSet(request.POST, instance=problem)
        
        if problem_form.is_valid() and testcase_formset.is_valid():
            problem = problem_form.save()
            testcase_formset.save()
            
            messages.success(request, f'Problem "{problem.title}" has been updated successfully!')
            return redirect('admin_problems_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        problem_form = ProblemForm(instance=problem)
        testcase_formset = TestCaseFormSet(instance=problem)
    
    return render(request, 'admin_edit_problem.html', {
        'problem': problem,
        'problem_form': problem_form,
        'testcase_formset': testcase_formset
    })

@user_passes_test(is_admin)
def admin_delete_problem(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    
    if request.method == 'POST':
        problem_title = problem.title
        problem.delete()
        messages.success(request, f'Problem "{problem_title}" has been deleted successfully!')
        return redirect('admin_problems_list')
    
    return render(request, 'admin_delete_problem.html', {'problem': problem})
