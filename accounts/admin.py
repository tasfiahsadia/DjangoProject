from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Department, FacultyProfile, StudentProfile, User


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    max_num = 1
    extra = 1
    can_delete = False


class FacultyProfileInline(admin.StackedInline):
    model = FacultyProfile
    max_num = 1
    extra = 1
    can_delete = False


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Role', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Extra info', {'fields': ('email', 'role')}),
    )
    list_display = ('username', 'email', 'role', 'is_staff')
    list_filter = UserAdmin.list_filter + ('role',)
    inlines = [StudentProfileInline, FacultyProfileInline]


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')