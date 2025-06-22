from django import template
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Q
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from problems.models import Problem, TestCase
from compiler.forms import CodeSubmissionForm
from compiler.models import CodeSubmission
from .forms import ProblemForm, TestCaseFormSet
import random
import json
import os
from datetime import date

# Try to import requests, handle gracefully if not available
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests module not available. AI assistance will use fallback mode.")

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
    
    # Get solved problems for the current user
    solved_problems = []
    if request.user.is_authenticated:
        solved_problems = list(
            CodeSubmission.objects.filter(
                user=request.user,
                is_correct=True
            ).values_list('problem_id', flat=True).distinct()
        )
    
    return render(request, 'problemList.html', {
        'problems': problems,
        'solved_problems': solved_problems
    })

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

# AI Assistance feature
@require_http_methods(["POST"])
def ai_assist(request, problem_id):
    print(f"AI assist called for problem {problem_id}")
    
    if not request.user.is_authenticated:
        print("User not authenticated")
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    
    try:
        problem = get_object_or_404(Problem, id=problem_id)
        print(f"Problem found: {problem.title}")
        
        data = json.loads(request.body)
        print(f"Parsed data: {data}")
        
        # Get language, mode, and user code from request
        language = data.get('language', 'python')
        mode = data.get('mode', 'review')  # 'review' or 'feedback'
        user_code = data.get('user_code', '')
        
        print(f"Language: {language}, Mode: {mode}, Code length: {len(user_code)}")
        
        # Check if GEMINI_API_KEY is set
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            print("GEMINI_API_KEY not set in environment variables")
        
        # Generate AI code review based on the problem and user code
        assistance_html = generate_ai_assistance(problem, language, mode, user_code)
        print(f"Generated assistance length: {len(assistance_html)}")
        
        return JsonResponse({
            'success': True,
            'assistance': assistance_html,
            'mode': mode,
            'language': language
        })
    except Exception as e:
        print(f"Error in ai_assist: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def generate_ai_assistance(problem, language, mode, user_code=""):
    """
    Generate AI-powered code review and feedback using Gemini API.
    """
    print(f"Generating code review for problem: {problem.title}, mode: {mode}, language: {language}")
    
    # First, try to use Gemini API
    if REQUESTS_AVAILABLE:
        api_key = os.environ.get('GEMINI_API_KEY')
        if api_key:
            print("Using Gemini API for code review")
            try:
                return generate_gemini_code_review(problem, language, mode, user_code, api_key)
            except Exception as e:
                print(f"Gemini API failed: {str(e)}, falling back to dynamic fallback")
        else:
            print("No Gemini API key found, using dynamic fallback")
    else:
        print("Requests module not available, using dynamic fallback")
    
    # Use dynamic fallback for code review
    return generate_dynamic_code_review(problem, language, mode, user_code)

def generate_gemini_assistance(problem, language, mode, api_key):
    """
    Generate assistance using Gemini API with the actual problem content.
    """
    # Clean the problem description for better API processing
    problem_description = problem.description
    if hasattr(problem_description, 'replace'):
        # Remove HTML tags for cleaner text
        import re
        problem_description = re.sub('<[^<]+?>', '', problem_description)
        problem_description = problem_description.replace('&nbsp;', ' ').strip()
    
    # Prepare the prompt based on mode
    if mode == 'solution':
        prompt = f"""
You are an expert programming tutor. Provide a complete, working solution to this coding problem.

PROBLEM DETAILS:
Title: {problem.title}
Difficulty: {problem.difficulty}
Description: {problem_description}

REQUIREMENTS:
- Programming Language: {language}
- Provide a complete, working solution
- Include clear comments explaining the logic
- Add time and space complexity analysis
- Make sure the code is syntactically correct and follows best practices

FORMAT YOUR RESPONSE AS HTML:
- Use <h4> for section headers
- Use <p> for explanations
- Wrap code in: <div class="ai-code"><div class="ai-code-header"><h5>Solution in {language}</h5><button class="ai-code-copy">Copy Code</button></div><pre>YOUR_CODE_HERE</pre></div>

Focus on solving this specific problem with the exact requirements mentioned in the description.
"""
    else:  # hints mode
        prompt = f"""
You are an expert programming tutor. Provide helpful hints and guidance for this coding problem WITHOUT giving the complete solution.

PROBLEM DETAILS:
Title: {problem.title}
Difficulty: {problem.difficulty}
Description: {problem_description}

REQUIREMENTS:
- Programming Language: {language}
- Provide hints and guidance, NOT the complete solution
- Help break down the problem approach
- Give language-specific tips for {language}
- Suggest algorithmic approaches
- Mention important edge cases

FORMAT YOUR RESPONSE AS HTML:
- Use <h4> for section headers
- Use <p> for explanations
- Focus on teaching and guiding, not solving

Analyze this specific problem and provide targeted hints based on its unique requirements and constraints.
"""

    # Gemini API endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
    
    # Request payload
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 2048,
        }
    }
    
    print(f"Sending request to Gemini API...")
    
    # Make API request
    response = requests.post(url, json=payload, timeout=20)
    
    if response.status_code == 200:
        result = response.json()
        if 'candidates' in result and len(result['candidates']) > 0:
            ai_text = result['candidates'][0]['content']['parts'][0]['text']
            
            print(f"Received response from Gemini API (length: {len(ai_text)})")
            
            # Format the response
            if mode == 'solution':
                formatted_response = f'''
                <div class="ai-hint">
                    <h4>🎯 AI-Generated Solution</h4>
                    <p>Here's a complete solution for "{problem.title}" in {language}:</p>
                </div>
                {ai_text}
                <div class="ai-hint">
                    <h4>💡 Study This Solution</h4>
                    <p>Make sure you understand each part of this solution before using it. Try to trace through the logic with the given examples!</p>
                </div>
                '''
            else:
                formatted_response = f'''
                <div class="ai-hint">
                    <h4>💡 AI-Generated Hints</h4>
                    <p>Here are personalized hints for "{problem.title}":</p>
                </div>
                {ai_text}
                <div class="ai-hint">
                    <h4>🚀 Next Steps</h4>
                    <p>Use these hints to implement your solution. If you're still stuck, try the "Solution" tab for the complete answer!</p>
                </div>
                '''
            
            return formatted_response
        else:
            raise Exception("No candidates in Gemini response")
    else:
        raise Exception(f"Gemini API error: {response.status_code} - {response.text}")

def generate_gemini_code_review(problem, language, mode, user_code, api_key):
    """
    Generate code review using Gemini API with the user's actual code.
    """
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    
    # Clean the problem description for better API processing
    problem_description = problem.description
    if hasattr(problem_description, 'replace'):
        # Remove HTML tags for cleaner text
        import re
        problem_description = re.sub('<[^<]+?>', '', problem_description)
        problem_description = problem_description.replace('&nbsp;', ' ').strip()
    
    # Prepare the prompt based on mode
    if mode == 'review':
        prompt = f"""
You are an expert programming mentor reviewing a student's code. Analyze the following code submission for a coding problem.

PROBLEM DETAILS:
Title: {problem.title}
Difficulty: {problem.difficulty}
Description: {problem_description}

STUDENT'S CODE ({language}):
\`\`\`{language}
{user_code}
\`\`\`

REVIEW REQUIREMENTS:
- Analyze the correctness of the logic
- Check if the solution addresses the problem requirements
- Identify potential bugs or edge cases not handled
- Evaluate code efficiency and time/space complexity
- Suggest improvements for code quality and readability
- Check for proper input/output handling

FORMAT YOUR RESPONSE AS HTML:
- Use <h4> for section headers
- Use <p> for explanations
- Use <div class="ai-code"> for code examples
- Be constructive and educational in your feedback

Provide a comprehensive review focusing on correctness, efficiency, and best practices.
"""
    else:  # feedback mode
        prompt = f"""
You are an expert programming mentor providing detailed feedback on a student's code approach.

PROBLEM DETAILS:
Title: {problem.title}
Difficulty: {problem.difficulty}
Description: {problem_description}

STUDENT'S CODE ({language}):
\`\`\`{language}
{user_code}
\`\`\`

FEEDBACK REQUIREMENTS:
- Evaluate the overall approach and algorithm choice
- Provide specific suggestions for improvement
- Highlight what the student did well
- Suggest alternative approaches if applicable
- Give tips for debugging and testing
- Provide guidance for next steps

FORMAT YOUR RESPONSE AS HTML:
- Use <h4> for section headers
- Use <p> for explanations
- Focus on learning and improvement
- Be encouraging while being honest about issues

Provide constructive feedback that helps the student learn and improve.
"""

    # Gemini API endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
    
    # Request payload
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 2048,
        }
    }
    
    print(f"Sending code review request to Gemini API...")
    
    # Make API request
    response = requests.post(url, json=payload, timeout=20)
    
    if response.status_code == 200:
        result = response.json()
        if 'candidates' in result and len(result['candidates']) > 0:
            ai_text = result['candidates'][0]['content']['parts'][0]['text']
            
            print(f"Received code review from Gemini API (length: {len(ai_text)})")
            
            # Format the response
            if mode == 'review':
                formatted_response = f'''
                <div class="ai-hint">
                    <h4>🔍 AI Code Review</h4>
                    <p>Here's a detailed review of your code for "{problem.title}":</p>
                </div>
                {ai_text}
                <div class="ai-hint">
                    <h4>💡 Next Steps</h4>
                    <p>Consider the feedback above and make improvements to your code. Test with different inputs to ensure correctness!</p>
                </div>
                '''
            else:
                formatted_response = f'''
                <div class="ai-hint">
                    <h4>📝 AI Feedback</h4>
                    <p>Here's constructive feedback on your approach for "{problem.title}":</p>
                </div>
                {ai_text}
                <div class="ai-hint">
                    <h4>🚀 Keep Going!</h4>
                    <p>Use this feedback to refine your solution. Remember, coding is an iterative process!</p>
                </div>
                '''
            
            return formatted_response
        else:
            raise Exception("No candidates in Gemini response")
    else:
        raise Exception(f"Gemini API error: {response.status_code} - {response.text}")

def generate_dynamic_code_review(problem, language, mode, user_code):
    """
    Generate dynamic code review when API is not available.
    """
    print(f"Generating dynamic code review for: {problem.title}")
    
    if not user_code.strip():
        return '''
        <div class="ai-hint">
            <h4>❌ No Code to Review</h4>
            <p>Please write some code in the editor above before requesting a review.</p>
        </div>
        '''
    
    # Analyze the user's code
    code_analysis = analyze_user_code(user_code, language)
    problem_type = detect_problem_type(problem.description.lower() if problem.description else "", 
                                     problem.title.lower() if problem.title else "")
    
    if mode == 'review':
        return generate_code_review_feedback(problem, language, code_analysis, problem_type, user_code)
    else:
        return generate_code_improvement_feedback(problem, language, code_analysis, problem_type, user_code)

def detect_problem_type(problem_text, problem_title):
    """
    Detect the type of problem based on keywords in the description.
    """
    # Define keyword patterns for different problem types
    patterns = {
        'array': ['array', 'list', 'elements', 'index', 'sort', 'search'],
        'string': ['string', 'character', 'substring', 'palindrome', 'anagram'],
        'math': ['sum', 'product', 'factorial', 'prime', 'fibonacci', 'gcd', 'lcm'],
        'graph': ['graph', 'tree', 'node', 'edge', 'path', 'traversal'],
        'dp': ['dynamic', 'programming', 'optimal', 'subproblem', 'memoization'],
        'greedy': ['greedy', 'minimum', 'maximum', 'optimal', 'choice'],
        'simulation': ['simulate', 'step', 'process', 'iteration', 'game'],
        'geometry': ['point', 'line', 'distance', 'coordinate', 'area', 'perimeter']
    }
    
    combined_text = problem_text + " " + problem_title
    
    # Count matches for each pattern
    scores = {}
    for problem_type, keywords in patterns.items():
        score = sum(1 for keyword in keywords if keyword in combined_text)
        if score > 0:
            scores[problem_type] = score
    
    # Return the type with highest score, or 'general' if no matches
    if scores:
        return max(scores, key=scores.get)
    return 'general'

def analyze_user_code(user_code, language):
    """
    Analyze user's code for common patterns and potential issues.
    """
    analysis = {
        'has_input': False,
        'has_output': False,
        'has_loops': False,
        'has_conditionals': False,
        'has_functions': False,
        'line_count': len(user_code.split('\n')),
        'potential_issues': []
    }
    
    code_lower = user_code.lower()
    
    # Check for input/output
    if language == 'python':
        analysis['has_input'] = 'input(' in code_lower
        analysis['has_output'] = 'print(' in code_lower
        analysis['has_loops'] = any(keyword in code_lower for keyword in ['for ', 'while '])
        analysis['has_conditionals'] = any(keyword in code_lower for keyword in ['if ', 'elif ', 'else:'])
        analysis['has_functions'] = 'def ' in code_lower
        
        # Check for potential issues
        if 'input()' in user_code and 'int(' not in code_lower:
            analysis['potential_issues'].append('Input might need type conversion')
        if analysis['line_count'] > 50:
            analysis['potential_issues'].append('Code might be too complex')
        if not analysis['has_output']:
            analysis['potential_issues'].append('No output statements found')
            
    elif language == 'cpp':
        analysis['has_input'] = 'cin' in code_lower
        analysis['has_output'] = 'cout' in code_lower
        analysis['has_loops'] = any(keyword in code_lower for keyword in ['for(', 'for (', 'while(', 'while ('])
        analysis['has_conditionals'] = any(keyword in code_lower for keyword in ['if(', 'if (', 'else'])
        analysis['has_functions'] = any(keyword in code_lower for keyword in ['int main', 'void ', 'int ', 'double '])
        
        # Check for potential issues
        if 'cin' in code_lower and 'iostream' not in code_lower:
            analysis['potential_issues'].append('Missing iostream header')
        if not analysis['has_output']:
            analysis['potential_issues'].append('No output statements found')
    
    return analysis

def generate_code_review_feedback(problem, language, analysis, problem_type, user_code):
    """
    Generate comprehensive code review feedback.
    """
    feedback_html = f'''
    <div class="ai-hint">
        <h4>🔍 Code Review for "{problem.title}"</h4>
        <p>Here's an analysis of your {language} code:</p>
    </div>
    
    <div class="ai-hint">
        <h4>📊 Code Structure Analysis</h4>
        <p><strong>Lines of code:</strong> {analysis['line_count']}</p>
        <p><strong>Has input handling:</strong> {"✅ Yes" if analysis['has_input'] else "❌ No"}</p>
        <p><strong>Has output:</strong> {"✅ Yes" if analysis['has_output'] else "❌ No"}</p>
        <p><strong>Uses loops:</strong> {"✅ Yes" if analysis['has_loops'] else "❌ No"}</p>
        <p><strong>Uses conditionals:</strong> {"✅ Yes" if analysis['has_conditionals'] else "❌ No"}</p>
    </div>
    '''
    
    # Add potential issues
    if analysis['potential_issues']:
        feedback_html += '''
        <div class="ai-hint">
            <h4>⚠️ Potential Issues</h4>
        '''
        for issue in analysis['potential_issues']:
            feedback_html += f'<p>• {issue}</p>'
        feedback_html += '</div>'
    
    # Add problem-specific feedback
    feedback_html += f'''
    <div class="ai-hint">
        <h4>🎯 Problem-Specific Review</h4>
        <p><strong>Problem type:</strong> {problem_type.title()}</p>
        {get_problem_specific_review(problem_type, analysis, language)}
    </div>
    
    <div class="ai-hint">
        <h4>💡 Suggestions</h4>
        {get_code_suggestions(analysis, language, problem_type)}
    </div>
    
    <div class="ai-hint">
        <h4>✅ Next Steps</h4>
        <p>1. Test your code with the provided examples</p>
        <p>2. Consider edge cases like empty input or boundary values</p>
        <p>3. Check if your solution handles all requirements from the problem description</p>
        <p>4. Optimize for better time/space complexity if needed</p>
    </div>
    '''
    
    return feedback_html

def get_problem_specific_review(problem_type, analysis, language):
    """
    Get problem-specific review comments.
    """
    reviews = {
        'array': '<p>For array problems, ensure you handle array bounds and consider if sorting is needed.</p>',
        'string': '<p>For string problems, check character-by-character processing and string manipulation methods.</p>',
        'math': '<p>For math problems, verify your formulas and handle edge cases like zero or negative numbers.</p>',
        'graph': '<p>For graph problems, ensure proper traversal and consider if you need to track visited nodes.</p>',
        'general': '<p>Review the problem requirements carefully and ensure your logic matches the expected behavior.</p>'
    }
    
    return reviews.get(problem_type, reviews['general'])

def get_code_suggestions(analysis, language, problem_type):
    """
    Get specific code improvement suggestions.
    """
    suggestions = []
    
    if not analysis['has_input']:
        suggestions.append('• Add proper input handling to read the problem data')
    
    if not analysis['has_output']:
        suggestions.append('• Add output statements to display your results')
    
    if analysis['line_count'] < 5:
        suggestions.append('• Your solution might be too simple - ensure it handles all requirements')
    elif analysis['line_count'] > 50:
        suggestions.append('• Consider breaking down your solution into smaller functions')
    
    if language == 'python':
        suggestions.append('• Use descriptive variable names for better readability')
        suggestions.append('• Consider using Python built-in functions where appropriate')
    elif language == 'cpp':
        suggestions.append('• Ensure proper memory management and avoid array bounds errors')
        suggestions.append('• Use STL containers and algorithms for efficiency')
    
    if not suggestions:
        suggestions.append('• Your code structure looks good! Focus on testing with different inputs')
    
    return '<p>' + '</p><p>'.join(suggestions) + '</p>'

def generate_code_improvement_feedback(problem, language, analysis, problem_type, user_code):
    """
    Generate improvement-focused feedback.
    """
    return f'''
    <div class="ai-hint">
        <h4>📝 Improvement Feedback</h4>
        <p>Here are specific suggestions to improve your code for "{problem.title}":</p>
    </div>
    
    <div class="ai-hint">
        <h4>🎯 What You Did Well</h4>
        {get_positive_feedback(analysis, language)}
    </div>
    
    <div class="ai-hint">
        <h4>🔧 Areas for Improvement</h4>
        {get_improvement_areas(analysis, problem_type, language)}
    </div>
    
    <div class="ai-hint">
        <h4>🚀 Optimization Tips</h4>
        {get_optimization_tips(problem_type, language)}
    </div>
    
    <div class="ai-hint">
        <h4>🧪 Testing Recommendations</h4>
        <p>• Test with the provided examples first</p>
        <p>• Try edge cases like minimum/maximum input sizes</p>
        <p>• Consider boundary conditions specific to this problem</p>
        <p>• Verify your output format matches the expected format</p>
    </div>
    '''

def get_positive_feedback(analysis, language):
    """
    Generate positive feedback based on code analysis.
    """
    positives = []
    
    if analysis['has_input'] and analysis['has_output']:
        positives.append('• Good job implementing input/output handling')
    
    if analysis['has_loops']:
        positives.append('• Nice use of loops for iteration')
    
    if analysis['has_conditionals']:
        positives.append('• Good use of conditional logic')
    
    if analysis['line_count'] > 10 and analysis['line_count'] < 30:
        positives.append('• Your code length seems appropriate for the problem')
    
    if not positives:
        positives.append('• You\'re on the right track - keep working on the implementation')
    
    return '<p>' + '</p><p>'.join(positives) + '</p>'

def get_improvement_areas(analysis, problem_type, language):
    """
    Get specific improvement areas.
    """
    improvements = []
    
    if not analysis['has_input']:
        improvements.append('• Add proper input reading to handle the problem data')
    
    if not analysis['has_output']:
        improvements.append('• Include output statements to display your results')
    
    if problem_type in ['array', 'string'] and not analysis['has_loops']:
        improvements.append(f'• Consider using loops for {problem_type} processing')
    
    if analysis['line_count'] < 5:
        improvements.append('• Your solution might need more logic to handle all cases')
    
    if not improvements:
        improvements.append('• Focus on testing and handling edge cases')
    
    return '<p>' + '</p><p>'.join(improvements) + '</p>'

def get_optimization_tips(problem_type, language):
    """
    Get optimization tips based on problem type.
    """
    tips = {
        'array': '<p>• Consider if sorting the array first would help</p><p>• Look for opportunities to use two-pointer technique</p>',
        'string': '<p>• Use efficient string methods for manipulation</p><p>• Consider using hash maps for character counting</p>',
        'math': '<p>• Look for mathematical patterns to avoid brute force</p><p>• Consider modular arithmetic for large numbers</p>',
        'graph': '<p>• Choose the right traversal method (BFS vs DFS)</p><p>• Consider using appropriate data structures</p>',
        'general': '<p>• Think about time complexity and optimize if needed</p><p>• Consider space-time tradeoffs</p>'
    }
    
    return tips.get(problem_type, tips['general'])
