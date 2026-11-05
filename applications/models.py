import os

from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models

from accounts.models import FacultyProfile, StudentProfile
from opportunities.models import Opportunity
#add check

class Application(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'

    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE, related_name='applications'
    )
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name='applications'
    )
    sop = models.TextField(verbose_name='Statement of purpose')
    remarks = models.TextField(blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-applied_at']
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'opportunity'],
                name='unique_application_per_student_opportunity',
            )
        ]

    def __str__(self):
        return f'{self.student} -> {self.opportunity} ({self.status})'

    @property
    def is_pending(self):
        """Edit, attachment add/delete and withdraw are allowed only while pending."""
        return self.status == self.Status.PENDING


class ApplicationAttachment(models.Model):
    ALLOWED_EXTENSIONS = ['pdf', 'doc', 'docx', 'zip', 'jpg', 'jpeg', 'png']

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name='attachments'
    )
    title = models.CharField(max_length=150)
    file = models.FileField(
        upload_to='applications/attachments/',
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_EXTENSIONS)],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.title} ({self.application_id})'

    @property
    def filename(self):
        return os.path.basename(self.file.name)


class ApplicationEvaluation(models.Model):
    class Decision(models.TextChoices):
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'

    application = models.OneToOneField(
        Application, on_delete=models.CASCADE, related_name='evaluation'
    )
    evaluator = models.ForeignKey(
        FacultyProfile, on_delete=models.CASCADE, related_name='evaluations'
    )
    score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    feedback = models.TextField()
    decision = models.CharField(max_length=10, choices=Decision.choices)
    evaluated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Evaluation of application {self.application_id}: {self.decision}'