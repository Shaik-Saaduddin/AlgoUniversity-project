from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.template import loader
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Case, When, IntegerField, Q
from compiler.models import CodeSubmission
from problems.models import Problem
from datetime import datetime, timedelta
from django.utils import timezone

# Create your views here.
def register_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = User.objects.filter(username=username)

        if user.exists():
            messages.error(request, 'User with this username already exists')
            return redirect("/auth/register/")
        
        user = User.objects.create_user(username=username)
        user.set_password(password)
        user.save()
        
        messages.success(request, 'User created successfully')
        return redirect('/problems/')
    
    template = loader.get_template('register.html')
    context = {}
    return HttpResponse(template.render(context, request))

def login_user(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not User.objects.filter(username=username).exists():
            messages.error(request, 'User with this username does not exist')
            return redirect('/auth/login/')
        
        user = authenticate(username=username, password=password)

        if user is None:
            messages.error(request, 'invalid password')
            return redirect('/auth/login')
        
        login(request, user)
        # Clear all previous messages
        list(messages.get_messages(request))
        # Now add the new message
        messages.success(request, 'login successful')

        return redirect('/problems/')
    
    template = loader.get_template('login.html')
    context = {}
    return HttpResponse(template.render(context, request))

def logout_user(request):
    logout(request)
    list(messages.get_messages(request))  # Clear all previous messages
    messages.success(request, 'Logout successful')
    return redirect('/auth/login/')

@login_required
def profile(request):
    if request.user.is_authenticated:
        # Get all user submissions
        user_submissions = CodeSubmission.objects.filter(user=request.user)
        submission_count = user_submissions.count()
        
        # Count distinct problems solved (correct submissions only)
        solved_problems_query = user_submissions.filter(is_correct=True).values('problem').distinct()
        solved_count = solved_problems_query.count()
        
        # Calculate acceptance rate
        if submission_count > 0:
            correct_submissions = user_submissions.filter(is_correct=True).count()
            acceptance_rate = round((correct_submissions / submission_count) * 100)
        else:
            acceptance_rate = 0
        
        # Get problems solved by difficulty
        solved_problem_ids = [sub['problem'] for sub in solved_problems_query if sub['problem']]
        solved_problems_by_difficulty = Problem.objects.filter(
            id__in=solved_problem_ids
        ).values('difficulty').annotate(count=Count('id'))
        
        difficulty_stats = {'Easy': 0, 'Medium': 0, 'Hard': 0}
        for stat in solved_problems_by_difficulty:
            difficulty_stats[stat['difficulty']] = stat['count']
        
        # Get language usage statistics
        language_stats = user_submissions.values('language').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Get most used language
        favorite_language = language_stats.first()['language'] if language_stats else 'None'
        
        # Get recent submissions (limit to 5) - Fixed field name
        recent_submissions = user_submissions.select_related('problem').order_by('-submitted_at')[:5]
        
        # Calculate solving streak (consecutive days with at least one correct submission)
        today = timezone.now().date()
        current_streak = 0
        check_date = today
        
        while True:
            day_submissions = user_submissions.filter(
                is_correct=True,
                submitted_at__date=check_date  # Fixed field name
            ).exists()
            
            if day_submissions:
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break
            
            # Limit check to prevent infinite loop
            if current_streak > 365:
                break
        
        # Get total problems available
        total_problems = Problem.objects.count()
        
        # Calculate progress percentage
        progress_percentage = round((solved_count / total_problems * 100)) if total_problems > 0 else 0
        
        context = {
            'submission_count': submission_count,
            'solved_count': solved_count,
            'acceptance_rate': acceptance_rate,
            'recent_submissions': recent_submissions,
            'difficulty_stats': difficulty_stats,
            'language_stats': language_stats,
            'favorite_language': favorite_language,
            'current_streak': current_streak,
            'total_problems': total_problems,
            'progress_percentage': progress_percentage,
        }
        
        template = loader.get_template('profile.html')
        return HttpResponse(template.render(context, request))
    else:
        messages.error(request, 'You are not logged in')
        return redirect('/auth/login/')
