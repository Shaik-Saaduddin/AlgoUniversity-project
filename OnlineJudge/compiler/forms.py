from django import forms
from .models import CodeSubmission
from problems.models import Problem

class CodeSubmissionForm(forms.ModelForm):
    class Meta:
        model = CodeSubmission
        fields = ['problem', 'language', 'code']
        widgets = {
            'problem': forms.Select(attrs={
                'class': 'form-control',
                'id': 'problem-select'
            }),
            'language': forms.Select(attrs={
                'class': 'form-control',
                'id': 'language-select'
            }),
            'code': forms.Textarea(attrs={
                'class': 'form-control',
                'id': 'code-editor',
                'rows': 20,
                'placeholder': 'Write your code here...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['problem'].queryset = Problem.objects.all()
        self.fields['problem'].empty_label = "Select a problem"
