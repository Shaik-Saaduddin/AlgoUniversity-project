from django import forms
from django.forms import inlineformset_factory
from .models import Problem, TestCase

class ProblemForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = ['title', 'description', 'difficulty']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter problem title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Enter problem description with examples, constraints, etc.'
            }),
            'difficulty': forms.Select(attrs={
                'class': 'form-control'
            }, choices=[
                ('Easy', 'Easy'),
                ('Medium', 'Medium'),
                ('Hard', 'Hard')
            ])
        }

class TestCaseForm(forms.ModelForm):
    class Meta:
        model = TestCase
        fields = ['input_data', 'expected_output']
        widgets = {
            'input_data': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter test case input'
            }),
            'expected_output': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter expected output'
            })
        }


TestCaseFormSet = inlineformset_factory(
    Problem, 
    TestCase, 
    form=TestCaseForm,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True
)
