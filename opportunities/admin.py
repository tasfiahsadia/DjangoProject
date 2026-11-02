from django.contrib import admin
from .models import Opportunity, OpportunityResource, SavedOpportunity


class OpportunityResourceInline(admin.TabularInline):
    model = OpportunityResource
    extra = 0


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ('title', 'faculty', 'opportunity_type', 'status', 'deadline')
    list_filter = ('opportunity_type', 'status', 'target_departments')
    search_fields = ('title', 'category', 'required_skills')
    filter_horizontal = ('target_departments',)
    inlines = [OpportunityResourceInline]


@admin.register(SavedOpportunity)
class SavedOpportunityAdmin(admin.ModelAdmin):
    list_display = ('student', 'opportunity', 'saved_at')