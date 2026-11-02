from django.contrib import admin

from .models import Application, ApplicationAttachment, ApplicationEvaluation


class ApplicationAttachmentInline(admin.TabularInline):
    model = ApplicationAttachment
    extra = 0


class ApplicationEvaluationInline(admin.StackedInline):
    model = ApplicationEvaluation
    max_num = 1
    extra = 0
    can_delete = False


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'opportunity', 'status', 'applied_at')
    list_filter = ('status',)
    search_fields = (
        'student__student_id',
        'student__user__username',
        'opportunity__title',
    )
    inlines = [ApplicationAttachmentInline, ApplicationEvaluationInline]


@admin.register(ApplicationEvaluation)
class ApplicationEvaluationAdmin(admin.ModelAdmin):
    list_display = ('application', 'evaluator', 'score', 'decision', 'evaluated_at')
    list_filter = ('decision',)