from django.contrib import admin
from .models import Collaboration, CollaborationMember


class CollaborationMemberInline(admin.TabularInline):
    model = CollaborationMember
    extra = 0


@admin.register(Collaboration)
class CollaborationAdmin(admin.ModelAdmin):
    list_display = ('title', 'opportunity', 'status', 'start_date', 'end_date')
    list_filter = ('status',)
    inlines = [CollaborationMemberInline]