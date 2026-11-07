import os
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

from accounts.models import Department, FacultyProfile, StudentProfile


class Opportunity(models.Model):
    class OpportunityType(models.TextChoices):
        RESEARCH = 'RESEARCH', 'Research'
        THESIS = 'THESIS', 'Thesis'
        COURSE_PROJECT = 'COURSE_PROJECT', 'Project'
        COMPETITION = 'COMPETITION', 'Competition'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        OPEN = 'OPEN', 'Open'
        CLOSED = 'CLOSED', 'Closed'

    faculty = models.ForeignKey(
        FacultyProfile, on_delete=models.CASCADE, related_name='opportunities'
    )
    target_departments = models.ManyToManyField(
        Department, related_name='opportunities'
    )
    title = models.CharField(max_length=200)
    opportunity_type = models.CharField(max_length=20, choices=OpportunityType.choices)
    category = models.CharField(max_length=100)
    description = models.TextField()
    required_skills = models.CharField(max_length=255, blank=True)
    positions = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    deadline = models.DateField()
    duration = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Opportunities'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('opportunities:detail', args=[self.pk])

    @property
    def is_open(self):
        """True only if published AND the deadline has not passed."""
        return self.status == self.Status.OPEN and self.deadline >= timezone.localdate()

    @property
    def days_left(self):
        return (self.deadline - timezone.localdate()).days

    @property
    def faculty_name(self):
        user = self.faculty.user
        return user.get_full_name() or user.username

    @property
    def departments_display(self):
        return ', '.join(department.code for department in self.target_departments.all())


class OpportunityResource(models.Model):
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE, related_name='resources'
    )
    title = models.CharField(max_length=150)
    file = models.FileField(upload_to='opportunities/resources/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.title} ({self.opportunity.title})'

    @property
    def filename(self):
        return os.path.basename(self.file.name)


class SavedOpportunity(models.Model):
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name='saved_opportunities'
    )
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE, related_name='saved_by'
    )
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-saved_at']
        verbose_name_plural = 'Saved opportunities'
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'opportunity'],
                name='unique_saved_opportunity',
            )
        ]

    def __str__(self):
        return f'{self.student} saved {self.opportunity}'