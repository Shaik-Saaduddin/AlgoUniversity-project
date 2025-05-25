from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import CodeSubmission
from .forms import CodeSubmissionForm
from problems.models import Problem, TestCase
import subprocess
import os
import tempfile
import time
import json

@login_required
def compiler_form(request):
    """Main compiler form view for submitting code"""
    problem_id = request.GET.get('problem_id')
    problem = None
    
    if problem_id:
        problem = get_object_or_404(Problem, id=problem_id)
    
    if request.method == 'POST':
        form = CodeSubmissionForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.user = request.user
            
            # Get problem from form data
            problem_id = request.POST.get('problem_id')
            if problem_id:
                submission.problem = get_object_or_404(Problem, id=problem_id)
            
            # Execute the code and get results
            result = execute_code(submission)
            
            # Save the submission with results
            submission.output = result.get('output', '')
            submission.error_message = result.get('error', '')
            submission.execution_time = result.get('execution_time', 0)
            submission.is_correct = result.get('is_correct', False)
            submission.save()
            
            # Store result in session for display
            request.session['execution_result'] = result
            request.session['submission_id'] = submission.id
            
            return redirect('result')
    else:
        initial_data = {}
        if problem:
            initial_data['problem'] = problem
        form = CodeSubmissionForm(initial=initial_data)
    
    context = {
        'form': form,
        'problem': problem,
        'problems': Problem.objects.all(),
    }
    
    return render(request, 'compiler_form.html', context)

@login_required
@csrf_exempt
def run_code(request):
    """Run code with custom input and return output via AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '')
            language = data.get('language', 'python')
            custom_input = data.get('input', '')
            
            if not code.strip():
                return JsonResponse({
                    'success': False,
                    'error': 'No code provided'
                })
            
            # Run the code with custom input
            result = run_single_test(code, language, custom_input, '')
            
            return JsonResponse({
                'success': True,
                'output': result['output'],
                'error': result['error'],
                'execution_time': round(result['execution_time'], 3)
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })

def execute_code(submission):
    """Execute code and return results"""
    try:
        language = submission.language
        code = submission.code
        problem = submission.problem
        
        if not problem:
            return {
                'output': '',
                'error': 'No problem selected',
                'execution_time': 0,
                'is_correct': False,
                'test_results': [],
                'verdict': 'No Problem Selected'
            }
        
        # Get test cases for the problem
        test_cases = TestCase.objects.filter(problem=problem)
        
        if not test_cases.exists():
            return {
                'output': '',
                'error': 'No test cases found for this problem',
                'execution_time': 0,
                'is_correct': False,
                'test_results': [],
                'verdict': 'No Test Cases'
            }
        
        test_results = []
        all_passed = True
        total_time = 0
        failed_reason = ""
        
        for i, test_case in enumerate(test_cases, 1):
            result = run_single_test(code, language, test_case.input_data, test_case.expected_output)
            test_results.append({
                'test_number': i,
                'input': test_case.input_data,
                'expected': test_case.expected_output,
                'actual': result['output'],
                'passed': result['passed'],
                'error': result['error'],
                'execution_time': result['execution_time']
            })
            
            total_time += result['execution_time']
            if not result['passed']:
                all_passed = False
                if not failed_reason:
                    if result['error']:
                        if 'Compilation Error' in result['error']:
                            failed_reason = 'Compilation Error'
                        elif 'Time Limit Exceeded' in result['error']:
                            failed_reason = 'Time Limit Exceeded'
                        else:
                            failed_reason = 'Runtime Error'
                    else:
                        failed_reason = 'Wrong Answer'
        
        # Determine verdict
        if all_passed:
            verdict = 'Accepted'
        else:
            verdict = failed_reason
        
        return {
            'output': test_results[0]['actual'] if test_results else '',
            'error': test_results[0]['error'] if test_results and test_results[0]['error'] else '',
            'execution_time': total_time,
            'is_correct': all_passed,
            'test_results': test_results,
            'verdict': verdict,
            'total_tests': len(test_cases),
            'passed_tests': sum(1 for result in test_results if result['passed'])
        }
        
    except Exception as e:
        return {
            'output': '',
            'error': f'Execution error: {str(e)}',
            'execution_time': 0,
            'is_correct': False,
            'test_results': [],
            'verdict': 'System Error'
        }

def run_single_test(code, language, input_data, expected_output):
    """Run code against a single test case"""
    try:
        start_time = time.time()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            if language == 'python':
                result = run_python_code(code, input_data, temp_dir)
            elif language == 'cpp':
                result = run_cpp_code(code, input_data, temp_dir)
            elif language == 'java':
                result = run_java_code(code, input_data, temp_dir)
            elif language == 'c':
                result = run_c_code(code, input_data, temp_dir)
            else:
                return {
                    'output': '',
                    'error': f'Unsupported language: {language}',
                    'passed': False,
                    'execution_time': 0
                }
        
        execution_time = time.time() - start_time
        
        # Check if output matches expected (only if expected_output is provided)
        actual_output = result['output'].strip()
        if expected_output:
            expected_output = expected_output.strip()
            passed = actual_output == expected_output
        else:
            passed = True  # For custom input testing, we don't check correctness
        
        return {
            'output': actual_output,
            'error': result.get('error', ''),
            'passed': passed,
            'execution_time': execution_time
        }
        
    except Exception as e:
        return {
            'output': '',
            'error': str(e),
            'passed': False,
            'execution_time': 0
        }

def run_python_code(code, input_data, temp_dir):
    """Execute Python code"""
    file_path = os.path.join(temp_dir, 'solution.py')
    
    with open(file_path, 'w') as f:
        f.write(code)
    
    try:
        process = subprocess.run(
            ['python', file_path],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        return {
            'output': process.stdout,
            'error': process.stderr if process.returncode != 0 else ''
        }
    except subprocess.TimeoutExpired:
        return {
            'output': '',
            'error': 'Time Limit Exceeded'
        }
    except Exception as e:
        return {
            'output': '',
            'error': str(e)
        }

def run_cpp_code(code, input_data, temp_dir):
    """Execute C++ code"""
    source_file = os.path.join(temp_dir, 'solution.cpp')
    executable = os.path.join(temp_dir, 'solution.exe')
    
    with open(source_file, 'w') as f:
        f.write(code)
    
    try:
        # Compile
        compile_process = subprocess.run(
            ['g++', '-o', executable, source_file],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if compile_process.returncode != 0:
            return {
                'output': '',
                'error': f'Compilation Error: {compile_process.stderr}'
            }
        
        # Execute
        run_process = subprocess.run(
            [executable],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        return {
            'output': run_process.stdout,
            'error': run_process.stderr if run_process.returncode != 0 else ''
        }
        
    except subprocess.TimeoutExpired:
        return {
            'output': '',
            'error': 'Time Limit Exceeded'
        }
    except Exception as e:
        return {
            'output': '',
            'error': str(e)
        }

def run_java_code(code, input_data, temp_dir):
    """Execute Java code"""
    # Extract class name from code
    import re
    class_match = re.search(r'public\s+class\s+(\w+)', code)
    class_name = class_match.group(1) if class_match else 'Solution'
    
    source_file = os.path.join(temp_dir, f'{class_name}.java')
    
    with open(source_file, 'w') as f:
        f.write(code)
    
    try:
        # Compile
        compile_process = subprocess.run(
            ['javac', source_file],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if compile_process.returncode != 0:
            return {
                'output': '',
                'error': f'Compilation Error: {compile_process.stderr}'
            }
        
        # Execute
        run_process = subprocess.run(
            ['java', '-cp', temp_dir, class_name],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        return {
            'output': run_process.stdout,
            'error': run_process.stderr if run_process.returncode != 0 else ''
        }
        
    except subprocess.TimeoutExpired:
        return {
            'output': '',
            'error': 'Time Limit Exceeded'
        }
    except Exception as e:
        return {
            'output': '',
            'error': str(e)
        }

def run_c_code(code, input_data, temp_dir):
    """Execute C code"""
    source_file = os.path.join(temp_dir, 'solution.c')
    executable = os.path.join(temp_dir, 'solution.exe')
    
    with open(source_file, 'w') as f:
        f.write(code)
    
    try:
        # Compile
        compile_process = subprocess.run(
            ['gcc', '-o', executable, source_file],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if compile_process.returncode != 0:
            return {
                'output': '',
                'error': f'Compilation Error: {compile_process.stderr}'
            }
        
        # Execute
        run_process = subprocess.run(
            [executable],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        return {
            'output': run_process.stdout,
            'error': run_process.stderr if run_process.returncode != 0 else ''
        }
        
    except subprocess.TimeoutExpired:
        return {
            'output': '',
            'error': 'Time Limit Exceeded'
        }
    except Exception as e:
        return {
            'output': '',
            'error': str(e)
        }

def result(request):
    """Display execution results"""
    result_data = request.session.get('execution_result')
    submission_id = request.session.get('submission_id')
    
    if not result_data:
        messages.error(request, 'No execution result found.')
        return redirect('compiler')
    
    submission = None
    problem = None
    if submission_id:
        submission = get_object_or_404(CodeSubmission, id=submission_id)
        problem = submission.problem
    
    context = {
        'result': result_data,
        'submission': submission,
        'problem': problem,
        'test_results': result_data.get('test_results', []),
        'verdict': result_data.get('verdict', 'Unknown'),
        'all_passed': result_data.get('is_correct', False),
        'total_tests': result_data.get('total_tests', 0),
        'passed_tests': result_data.get('passed_tests', 0),
    }
    
    return render(request, 'result.html', context)

@login_required
def user_submissions(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    # Check if the user is viewing their own submissions or is staff
    if request.user.id != user_id and not request.user.is_staff:
        return redirect('profile')
    
    # Get filter parameters
    problem_id = request.GET.get('problem')
    language = request.GET.get('language')
    status = request.GET.get('status')
    
    # Base queryset
    submissions = CodeSubmission.objects.filter(user=user).order_by('-submitted_at')
    
    # Apply filters
    if problem_id:
        submissions = submissions.filter(problem_id=problem_id)
    
    if language:
        submissions = submissions.filter(language=language)
    
    if status:
        is_correct = status == 'correct'
        submissions = submissions.filter(is_correct=is_correct)
    
    # Pagination
    paginator = Paginator(submissions, 10)  # 10 submissions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get problems for filter dropdown
    problems = Problem.objects.all()
    
    context = {
        'user_profile': user,
        'page_obj': page_obj,
        'problems': problems,
        'selected_problem': problem_id,
        'selected_language': language,
        'selected_status': status,
        'languages': CodeSubmission.LANGUAGE_CHOICES,
    }
    
    return render(request, 'user_submissions.html', context)

@login_required
def all_submissions(request):
    # Only staff can see all submissions
    if not request.user.is_staff:
        return redirect('user-submissions', user_id=request.user.id)
    
    # Get filter parameters
    username = request.GET.get('username')
    problem_id = request.GET.get('problem')
    language = request.GET.get('language')
    status = request.GET.get('status')
    
    # Base queryset
    submissions = CodeSubmission.objects.all().order_by('-submitted_at')
    
    # Apply filters
    if username:
        submissions = submissions.filter(user__username__icontains=username)
    
    if problem_id:
        submissions = submissions.filter(problem_id=problem_id)
    
    if language:
        submissions = submissions.filter(language=language)
    
    if status:
        is_correct = status == 'correct'
        submissions = submissions.filter(is_correct=is_correct)
    
    # Pagination
    paginator = Paginator(submissions, 15)  # 15 submissions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get problems for filter dropdown
    problems = Problem.objects.all()
    
    context = {
        'page_obj': page_obj,
        'problems': problems,
        'selected_username': username,
        'selected_problem': problem_id,
        'selected_language': language,
        'selected_status': status,
        'languages': CodeSubmission.LANGUAGE_CHOICES,
    }
    
    return render(request, 'all_submissions.html', context)

@login_required
def submission_detail(request, submission_id):
    submission = get_object_or_404(CodeSubmission, id=submission_id)
    
    # Check if the user is viewing their own submission or is staff
    if submission.user != request.user and not request.user.is_staff:
        return redirect('profile')
    
    context = {
        'submission': submission,
    }
    
    return render(request, 'submission_detail.html', context)
