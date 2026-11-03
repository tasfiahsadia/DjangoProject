from django.db import models
from django.urls import reverse
from django.utils import timezone

from accounts.models import StudentProfile
from opportunities.models import Opportunity


class Collaboration(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'

    opportunity = models.OneToOneField(
        Opportunity, on_delete=models.CASCADE, related_name='collaboration'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('collaboration:detail', args=[self.pk])

    @property
    def faculty_name(self):
        """The owner is always the faculty who posted the opportunity."""
        return self.opportunity.faculty_name


class CollaborationMember(models.Model):
    collaboration = models.ForeignKey(
        Collaboration, on_delete=models.CASCADE, related_name='members'
    )
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name='collaboration_memberships'
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['joined_at']
        constraints = [
            models.UniqueConstraint(
                fields=['collaboration', 'student'],
                name='unique_collaboration_member',
            )
        ]

    def __str__(self):
        return f'{self.student} in {self.collaboration}'