from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        FACULTY = 'FACULTY', 'Faculty'

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)

    def __str__(self):
        return self.username


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return self.code


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='students')
    student_id = models.CharField(max_length=20, unique=True)
    batch = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    profile_picture = models.ImageField(upload_to='accounts/profile_pictures/', blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f'{self.user.username} ({self.student_id})'


class FacultyProfile(models.Model):
    class Designation(models.TextChoices):
        LECTURER = 'LECTURER', 'Lecturer'
        ASSISTANT_PROFESSOR = 'ASSISTANT_PROFESSOR', 'Assistant Professor'
        ASSOCIATE_PROFESSOR = 'ASSOCIATE_PROFESSOR', 'Associate Professor'
        PROFESSOR = 'PROFESSOR', 'Professor'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='faculty_profile')
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='faculty_members')
    designation = models.CharField(max_length=30, choices=Designation.choices)
    profile_picture = models.ImageField(upload_to='accounts/profile_pictures/', blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f'{self.user.username} ({self.designation})'