from pathlib import Path
import subprocess
import uuid
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse
from problems.models import Problem, TestCase
from .forms import CodeSubmissionForm

# Create your views here.
def submit(request):
    if request.method == "POST":
        form = CodeSubmissionForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            problem_id = request.POST.get('problem_id')
            problem = Problem.objects.get(id=problem_id)
            submission.problem = problem
            submission.save()

            action = request.POST.get('action')
            if action == "run":
                user_input = form.cleaned_data['input_data']
                output = run_code(submission.language, submission.code, user_input)
                verdict = ""
            elif action == "submit":
                testcases = problem.testcases.all()
                all_passed = True
                for tc in testcases:
                    output = run_code(submission.language, submission.code, tc.input_data)
                    if output.strip() != tc.expected_output.strip():
                        all_passed = False
                        break
                verdict = "Success" if all_passed else "Failed"
                output = ""  

            context = {
                "problem": problem,
                "form": form,
                "output": output if action == "run" else "",
                "verdict": verdict if action == "submit" else "",
                "action": action,
            }
            return render(request, "problem.html", context)
    else:
        form = CodeSubmissionForm()
    return render(request, "submit.html", {"form": form})

def run_code(language, code, input_data):
    project_path = Path(settings.BASE_DIR)
    directories = ["code", "inputs", "outputs"]

    for directory in directories:
        dir_path = project_path / directory
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
    codes_dir = project_path / "code"
    inputs_dir = project_path / "inputs"
    outputs_dir = project_path / "outputs"

    unique = str(uuid.uuid4())

    code_file_name = f"{unique}.{language}"
    input_file_name = f"{unique}.txt"
    output_file_name = f"{unique}.txt"

    code_file_path = codes_dir / code_file_name
    input_file_path = inputs_dir / input_file_name
    output_file_path = outputs_dir / output_file_name

    with open(code_file_path, "w") as code_file:
        code_file.write(code)
    with open(input_file_path, "w") as input_file:
        input_file.write(input_data)
    with open(output_file_path, "w") as output_file:
        pass

    if language == "cpp":
        executable_path = codes_dir / unique
        compile_result = subprocess.run(["g++", str(code_file_path), "-o", str(executable_path)])
        if compile_result.returncode == 0:
            with open(input_file_path, "r") as input_file:
                with open(output_file_path, "w") as output_file:
                    subprocess.run([str(executable_path)], stdin=input_file, stdout=output_file,)

    elif language == "python":
        with open(input_file_path, "r") as output_file:
            with open(output_file_path, "w") as output_file:
                subprocess.run(["python3", str(code_file_path)], stdin=input_file, stdout=output_file,)

    with open(output_file_path, "r") as output_file:
        output_data = output_file.read()
    
    return output_data