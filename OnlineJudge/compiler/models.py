from django.db import models
from problems.models import Problem

# Create your models here.
class CodeSubmission(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, null=True, blank=True)
    language = models.CharField(max_length=100)
    code = models.TextField()
    input_data = models.TextField(blank=True, null=True)
    output_data = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
