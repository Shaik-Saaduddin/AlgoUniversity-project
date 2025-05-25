from django.db import models
from django.contrib.auth.models import User
from problems.models import Problem

class CodeSubmission(models.Model):
    LANGUAGE_CHOICES = [
        ('python', 'Python'),
        ('cpp', 'C++'),
        ('java', 'Java'),
        ('c', 'C'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, null=True, blank=True, related_name='submissions')
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES)
    code = models.TextField()
    output = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    execution_time = models.FloatField(default=0.0)
    is_correct = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-submitted_at']
    
    def __str__(self):
        problem_name = self.problem.title if self.problem else "No Problem"
        return f"{self.user.username} - {problem_name} ({self.language})"
