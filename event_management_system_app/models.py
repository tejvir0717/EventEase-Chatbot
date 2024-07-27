from django.db import models
from django.db import models

class Category(models.Model):
	name = models.CharField(max_length=100)

class Event(models.Model):
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=100)
	category = models.ForeignKey(Category, on_delete=models.CASCADE)
	start_date = models.DateTimeField()
	end_date = models.DateTimeField()
	priority = models.IntegerField(default=1)
	description = models.TextField(default='')
	location = models.CharField(max_length=255, default='')
	organizer = models.CharField(max_length=100, default='')
	participants = models.IntegerField(default=0)