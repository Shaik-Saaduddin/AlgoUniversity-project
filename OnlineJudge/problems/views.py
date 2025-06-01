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

# AI Assistance
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
        
        # Get language and mode from request
        language = data.get('language', 'python')
        mode = data.get('mode', 'solution')  # 'solution' or 'hints'
        
        print(f"Language: {language}, Mode: {mode}")
        
        # Generate AI assistance based on the problem
        assistance_html = generate_ai_assistance(problem, data.get('problem_description', ''), language, mode)
        print(f"Generated assistance length: {len(assistance_html)}")
        
        return JsonResponse({
            'success': True,
            'assistance': assistance_html,
            'mode': mode,  # Include mode in response for debugging
            'language': language  # Include language in response for debugging
        })
    except Exception as e:
        print(f"Error in ai_assist: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def generate_ai_assistance(problem, description, language, mode):
    """
    Generate AI-powered assistance using Gemini API for solving the problem.
    """
    print(f"Generating assistance for mode: {mode}, language: {language}")
    
    # Check if requests module is available
    if not REQUESTS_AVAILABLE:
        print("Requests module not available, using fallback assistance")
        return generate_fallback_assistance(problem, language, mode)
    
    try:
        # Get Gemini API key from environment
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            print("Gemini API key not found, using fallback assistance")
            return generate_fallback_assistance(problem, language, mode)
        
        # Prepare the prompt for Gemini based on mode
        if mode == 'solution':
            prompt = f"""
            You are an expert programming tutor providing a complete solution to a coding problem.
            
            Problem Title: {problem.title}
            Difficulty: {problem.difficulty}
            Problem Description: {problem.description[:1500]}
            Programming Language: {language}
            
            Please provide a COMPLETE, WORKING SOLUTION to this problem in {language}. Structure your response as follows:
            
            1. Brief explanation of the approach (2-3 sentences)
            2. Complete, well-commented code solution that solves the problem
            3. Time and space complexity analysis
            4. Example walkthrough if helpful
            
            Make sure your solution:
            - Is syntactically correct and runnable
            - Handles all edge cases mentioned in the problem
            - Follows best practices for {language}
            - Is well-commented to explain the logic
            
            Format the code in HTML like this:
            <div class="ai-code">
                <div class="ai-code-header">
                    <h5>Complete Solution in {language}</h5>
                    <button class="ai-code-copy">Copy Code</button>
                </div>
                <pre>YOUR_CODE_HERE</pre>
            </div>
            
            Use simple HTML formatting with <h4> for section headers and <p> for content.
            """
        else:  # hints mode
            prompt = f"""
            You are an expert programming tutor providing hints and guidance for a coding problem.
            
            Problem Title: {problem.title}
            Difficulty: {problem.difficulty}
            Problem Description: {problem.description[:1500]}
            Programming Language: {language}
            
            Please provide HELPFUL HINTS AND GUIDANCE (NOT the complete solution) to solve this problem. Structure your response as follows:
            
            1. Problem Understanding - Help break down what the problem is asking (be specific)
            2. Approach Strategy - Suggest the algorithmic approach without giving away the implementation
            3. Key Insights - Provide 2-3 key insights that will help solve the problem
            4. Implementation Tips - Provide {language}-specific tips for implementation
            5. Edge Cases - Mention important edge cases to consider
            6. Next Steps - Suggest what the student should try first
            
            IMPORTANT: 
            - Do NOT provide the complete solution or full code
            - Give enough guidance to help them think through the problem
            - Focus on the thought process and approach
            - Be encouraging and educational
            
            Use simple HTML formatting with <h4> for section headers and <p> for content.
            """
        
        print(f"Sending prompt to Gemini API (mode: {mode})")
        
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
        
        # Make API request
        response = requests.post(url, json=payload, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                ai_text = result['candidates'][0]['content']['parts'][0]['text']
                
                # Format the response in a nice HTML structure
                if mode == 'solution':
                    formatted_response = f'''
                    <div class="ai-hint">
                        <h4>🎯 Complete Solution</h4>
                        <p>Here's a complete working solution to the problem in {language}:</p>
                    </div>
                    {ai_text}
                    <div class="ai-hint">
                        <h4>💡 How to Use This Solution</h4>
                        <p>Study the code carefully to understand the approach. You can copy it to your editor, but make sure you understand each part before submitting!</p>
                    </div>
                    '''
                else:
                    formatted_response = f'''
                    <div class="ai-hint">
                        <h4>💡 Hints & Guidance</h4>
                        <p>Here are some hints to help you solve this problem step by step:</p>
                    </div>
                    {ai_text}
                    <div class="ai-hint">
                        <h4>🚀 Ready to Code?</h4>
                        <p>Use these hints to implement your solution. If you need the complete solution, click the "Solution" tab above!</p>
                    </div>
                    '''
                
                print(f"Successfully generated {mode} response")
                return formatted_response
            else:
                print("No candidates in Gemini response")
                return generate_fallback_assistance(problem, language, mode)
        else:
            print(f"Gemini API error: {response.status_code} - {response.text}")
            return generate_fallback_assistance(problem, language, mode)
            
    except Exception as e:
        print(f"Error calling Gemini API: {str(e)}")
        return generate_fallback_assistance(problem, language, mode)

def generate_fallback_assistance(problem, language, mode):
    """
    Fallback assistance when Gemini API is not available.
    """
    print(f"Generating fallback assistance for mode: {mode}, language: {language}")
    
    if mode == 'solution':
        # Provide a complete solution template based on language
        solution_templates = {
            'python': f'''
            <div class="ai-hint">
                <h4>🎯 Complete Solution Approach</h4>
                <p>This problem can be solved using a systematic approach. Here's a complete solution template for you to understand and modify:</p>
            </div>
            <div class="ai-code">
                <div class="ai-code-header">
                    <h5>Complete Solution in Python</h5>
                    <button class="ai-code-copy">Copy Code</button>
                </div>
                <pre>def solve_problem():
    """
    Solution for: {problem.title}
    Difficulty: {problem.difficulty}
    
    Approach:
    1. Parse the input carefully
    2. Implement the core algorithm
    3. Handle edge cases
    4. Return/print the result
    """
    
    # Step 1: Read and parse input
    # TODO: Modify based on the specific input format
    n = int(input())
    data = list(map(int, input().split()))
    
    # Step 2: Initialize variables
    result = []
    
    # Step 3: Core algorithm implementation
    # TODO: Implement the specific algorithm for this problem
    for i in range(n):
        # Process each element
        # Add your logic here
        pass
    
    # Step 4: Handle edge cases
    if not data:
        return []
    
    # Step 5: Return or print result
    return result

def main():
    try:
        result = solve_problem()
        print(result)
    except Exception as e:
        print(f"Error: {{e}}")

if __name__ == "__main__":
    main()</pre>
            </div>
            <div class="ai-hint">
                <h4>⚡ Time & Space Complexity</h4>
                <p><strong>Time Complexity:</strong> O(n) - where n is the input size</p>
                <p><strong>Space Complexity:</strong> O(n) - for storing the result</p>
                <p><em>Note: Actual complexity depends on your specific implementation.</em></p>
            </div>
            <div class="ai-hint">
                <h4>🔧 Implementation Tips</h4>
                <p>• Use Python's built-in functions like <code>len()</code>, <code>min()</code>, <code>max()</code></p>
                <p>• Consider using list comprehensions for cleaner code</p>
                <p>• Don't forget to handle empty inputs and edge cases</p>
            </div>
            ''',
            'cpp': f'''
            <div class="ai-hint">
                <h4>🎯 Complete Solution Approach</h4>
                <p>This problem can be solved using a systematic approach. Here's a complete solution template in C++:</p>
            </div>
            <div class="ai-code">
                <div class="ai-code-header">
                    <h5>Complete Solution in C++</h5>
                    <button class="ai-code-copy">Copy Code</button>
                </div>
                <pre>#include &lt;iostream&gt;
#include &lt;vector&gt;
#include &lt;algorithm&gt;
using namespace std;

/*
 * Solution for: {problem.title}
 * Difficulty: {problem.difficulty}
 * 
 * Approach:
 * 1. Read input efficiently
 * 2. Implement core algorithm
 * 3. Handle edge cases
 * 4. Output result
 */

vector&lt;int&gt; solveProblem(const vector&lt;int&gt;&amp; data) {{
    int n = data.size();
    vector&lt;int&gt; result;
    
    // Core algorithm implementation
    // TODO: Implement the specific logic for this problem
    for (int i = 0; i &lt; n; i++) {{
        // Process each element
        // Add your logic here
    }}
    
    return result;
}}

int main() {{
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    try {{
        // Read input
        int n;
        cin &gt;&gt; n;
        
        vector&lt;int&gt; data(n);
        for (int i = 0; i &lt; n; i++) {{
            cin &gt;&gt; data[i];
        }}
        
        // Solve the problem
        vector&lt;int&gt; result = solveProblem(data);
        
        // Output result
        for (int i = 0; i &lt; result.size(); i++) {{
            cout &lt;&lt; result[i];
            if (i &lt; result.size() - 1) cout &lt;&lt; " ";
        }}
        cout &lt;&lt; endl;
        
    }} catch (const exception&amp; e) {{
        cerr &lt;&lt; "Error: " &lt;&lt; e.what() &lt;&lt; endl;
        return 1;
    }}
    
    return 0;
}}</pre>
            </div>
            <div class="ai-hint">
                <h4>⚡ Time & Space Complexity</h4>
                <p><strong>Time Complexity:</strong> O(n) - where n is the input size</p>
                <p><strong>Space Complexity:</strong> O(n) - for storing the result</p>
            </div>
            <div class="ai-hint">
                <h4>🔧 C++ Optimization Tips</h4>
                <p>• Use <code>ios_base::sync_with_stdio(false)</code> for faster I/O</p>
                <p>• Prefer <code>vector</code> over arrays for dynamic sizing</p>
                <p>• Use <code>const</code> references to avoid unnecessary copying</p>
            </div>
            ''',
            'java': f'''
            <div class="ai-hint">
                <h4>🎯 Complete Solution Approach</h4>
                <p>This problem can be solved using a systematic approach. Here's a complete solution template in Java:</p>
            </div>
            <div class="ai-code">
                <div class="ai-code-header">
                    <h5>Complete Solution in Java</h5>
                    <button class="ai-code-copy">Copy Code</button>
                </div>
                <pre>import java.util.*;
import java.io.*;

/*
 * Solution for: {problem.title}
 * Difficulty: {problem.difficulty}
 * 
 * Approach:
 * 1. Read input using Scanner
 * 2. Implement core algorithm
 * 3. Handle edge cases
 * 4. Output result
 */

public class Solution {{
    
    public static List&lt;Integer&gt; solveProblem(List&lt;Integer&gt; data) {{
        int n = data.size();
        List&lt;Integer&gt; result = new ArrayList&lt;&gt;();
        
        // Core algorithm implementation
        // TODO: Implement the specific logic for this problem
        for (int i = 0; i &lt; n; i++) {{
            // Process each element
            // Add your logic here
        }}
        
        return result;
    }}
    
    public static void main(String[] args) {{
        try {{
            Scanner scanner = new Scanner(System.in);
            
            // Read input
            int n = scanner.nextInt();
            List&lt;Integer&gt; data = new ArrayList&lt;&gt;();
            
            for (int i = 0; i &lt; n; i++) {{
                data.add(scanner.nextInt());
            }}
            
            // Solve the problem
            List&lt;Integer&gt; result = solveProblem(data);
            
            // Output result
            for (int i = 0; i &lt; result.size(); i++) {{
                System.out.print(result.get(i));
                if (i &lt; result.size() - 1) {{
                    System.out.print(" ");
                }}
            }}
            System.out.println();
            
            scanner.close();
            
        }} catch (Exception e) {{
            System.err.println("Error: " + e.getMessage());
        }}
    }}
}}</pre>
            </div>
            <div class="ai-hint">
                <h4>⚡ Time & Space Complexity</h4>
                <p><strong>Time Complexity:</strong> O(n) - where n is the input size</p>
                <p><strong>Space Complexity:</strong> O(n) - for storing the result</p>
            </div>
            <div class="ai-hint">
                <h4>🔧 Java Best Practices</h4>
                <p>• Use <code>ArrayList</code> for dynamic arrays</p>
                <p>• Always close Scanner to prevent resource leaks</p>
                <p>• Use proper exception handling</p>
            </div>
            ''',
            'c': f'''
            <div class="ai-hint">
                <h4>🎯 Complete Solution Approach</h4>
                <p>This problem can be solved using a systematic approach. Here's a complete solution template in C:</p>
            </div>
            <div class="ai-code">
                <div class="ai-code-header">
                    <h5>Complete Solution in C</h5>
                    <button class="ai-code-copy">Copy Code</button>
                </div>
                <pre>#include &lt;stdio.h&gt;
#include &lt;stdlib.h&gt;
#include &lt;string.h&gt;

/*
 * Solution for: {problem.title}
 * Difficulty: {problem.difficulty}
 * 
 * Approach:
 * 1. Read input using scanf
 * 2. Implement core algorithm
 * 3. Handle edge cases and memory management
 * 4. Output result
 */

int* solveProblem(int* data, int n, int* resultSize) {{
    // Allocate memory for result
    int* result = (int*)malloc(n * sizeof(int));
    *resultSize = 0;
    
    // Core algorithm implementation
    // TODO: Implement the specific logic for this problem
    for (int i = 0; i &lt; n; i++) {{
        // Process each element
        // Add your logic here
        
        // Example: add to result
        // result[(*resultSize)++] = data[i];
    }}
    
    return result;
}}

int main() {{
    int n;
    
    // Read input
    if (scanf("%d", &amp;n) != 1) {{
        fprintf(stderr, "Error reading input\\n");
        return 1;
    }}
    
    // Allocate memory for input data
    int* data = (int*)malloc(n * sizeof(int));
    if (data == NULL) {{
        fprintf(stderr, "Memory allocation failed\\n");
        return 1;
    }}
    
    // Read data
    for (int i = 0; i &lt; n; i++) {{
        if (scanf("%d", &amp;data[i]) != 1) {{
            fprintf(stderr, "Error reading data\\n");
            free(data);
            return 1;
        }}
    }}
    
    // Solve the problem
    int resultSize;
    int* result = solveProblem(data, n, &amp;resultSize);
    
    // Output result
    for (int i = 0; i &lt; resultSize; i++) {{
        printf("%d", result[i]);
        if (i &lt; resultSize - 1) {{
            printf(" ");
        }}
    }}
    printf("\\n");
    
    // Free allocated memory
    free(data);
    free(result);
    
    return 0;
}}</pre>
            </div>
            <div class="ai-hint">
                <h4>⚡ Time & Space Complexity</h4>
                <p><strong>Time Complexity:</strong> O(n) - where n is the input size</p>
                <p><strong>Space Complexity:</strong> O(n) - for storing the result</p>
            </div>
            <div class="ai-hint">
                <h4>🔧 C Programming Tips</h4>
                <p>• Always check return values of <code>scanf</code> and <code>malloc</code></p>
                <p>• Remember to <code>free()</code> all allocated memory</p>
                <p>• Use proper error handling for robust code</p>
            </div>
            '''
        }
        
        return solution_templates.get(language, solution_templates['python'])
    
    else:  # hints mode
        hints_content = f'''
        <div class="ai-hint">
            <h4>🤔 Problem Understanding</h4>
            <p><strong>What is this problem asking?</strong></p>
            <p>• Read the problem statement carefully and identify the input format</p>
            <p>• Understand what output is expected</p>
            <p>• Look for constraints and edge cases mentioned</p>
            <p>• Try to rephrase the problem in your own words</p>
        </div>
        
        <div class="ai-hint">
            <h4>🎯 Approach Strategy</h4>
            <p><strong>How should you approach this problem?</strong></p>
            <p>• Start with a brute force solution if the constraints allow</p>
            <p>• Look for patterns or mathematical relationships</p>
            <p>• Consider if sorting, searching, or dynamic programming might help</p>
            <p>• Think about the most efficient data structures to use</p>
        </div>
        
        <div class="ai-hint">
            <h4>💡 Key Insights for {language}</h4>
            <p><strong>Language-specific tips:</strong></p>
            {get_language_specific_hints(language)}
        </div>
        
        <div class="ai-hint">
            <h4>⚠️ Edge Cases to Consider</h4>
            <p>• What happens with empty input?</p>
            <p>• How do you handle the minimum and maximum constraints?</p>
            <p>• Are there any special cases mentioned in the problem?</p>
            <p>• Test your solution with the provided examples</p>
        </div>
        
        <div class="ai-hint">
            <h4>🚀 Next Steps</h4>
            <p><strong>Start coding step by step:</strong></p>
            <p>1. Write the input reading part first</p>
            <p>2. Implement a basic solution (even if inefficient)</p>
            <p>3. Test with the given examples</p>
            <p>4. Optimize if needed based on time constraints</p>
            <p>5. Handle edge cases</p>
        </div>
        
        <div class="ai-hint">
            <h4>🎓 Learning Tip</h4>
            <p>Try to solve it yourself first! If you get stuck, you can always switch to the "Solution" tab for a complete answer.</p>
        </div>
        '''
        
        return hints_content

def get_language_specific_hints(language):
    """
    Get language-specific hints for the hints mode.
    """
    hints = {
        'python': '''
            <p>• Use <code>input()</code> for reading and <code>print()</code> for output</p>
            <p>• List comprehensions can make your code more concise</p>
            <p>• Built-in functions like <code>len()</code>, <code>sum()</code>, <code>min()</code>, <code>max()</code> are very useful</p>
            <p>• Consider using <code>collections.defaultdict</code> or <code>collections.Counter</code> for counting problems</p>
        ''',
        'cpp': '''
            <p>• Use <code>cin</code> and <code>cout</code> for I/O, add <code>ios_base::sync_with_stdio(false)</code> for speed</p>
            <p>• STL containers like <code>vector</code>, <code>map</code>, <code>set</code> are very powerful</p>
            <p>• Use <code>auto</code> keyword for type inference</p>
            <p>• Remember to include necessary headers like <code>&lt;algorithm&gt;</code>, <code>&lt;vector&gt;</code></p>
        ''',
        'java': '''
            <p>• Use <code>Scanner</code> for input and <code>System.out.println()</code> for output</p>
            <p>• <code>ArrayList</code>, <code>HashMap</code>, and <code>HashSet</code> are commonly used</p>
            <p>• Use <code>Collections.sort()</code> for sorting</p>
            <p>• Remember to handle exceptions and close resources</p>
        ''',
        'c': '''
            <p>• Use <code>scanf()</code> for input and <code>printf()</code> for output</p>
            <p>• Always check return values of <code>scanf()</code> and <code>malloc()</code></p>
            <p>• Remember to <code>free()</code> any memory you allocate</p>
            <p>• Use arrays and pointers effectively for data manipulation</p>
        '''
    }
    
    return hints.get(language, hints['python'])
