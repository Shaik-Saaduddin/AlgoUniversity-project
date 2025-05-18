from django.db import models

# Create your models here.
class Problem(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.CharField(max_length=50)

    def __str__(self):
        return self.title