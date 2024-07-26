from django.contrib import admin
from nets_core import models

# RolePermissionInline = admin.TabularInline

class RolePermissionInline(admin.TabularInline):
    model = models.Role.permissions.through
    extra = 1


@admin.register(models.Role)
class RoleAdmin(admin.ModelAdmin):
    model = models.Role
    
    list_display = ('name', 'description', 'project', 'enabled')
    list_filter = ('project', 'enabled')
    search_fields = ('name', 'description', 'project')
    inlines = [RolePermissionInline]
        
    
@admin.register(models.Permission)
class PermissionAdmin(admin.ModelAdmin):
    model = models.Permission    
    list_display = ('codename', 'description')    
    search_fields = ('codename', 'description')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(roles__user=request.user)
    
    
@admin.register(models.EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    model = models.EmailNotification
    
    list_display = ('subject', 'to', 'custom_email', 'sent', 'tries', 'created', 'project')
    list_filter = ('created', 'sent', 'project')
    
    search_fields = ('subject', 'email', 'project')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(email=request.user.email)
    
@admin.register(models.CustomEmail)
class CustomEmailAdmin(admin.ModelAdmin):
    model = models.CustomEmail
    
    list_display = ('subject', 'to_email', 'project', 'completed', 'sent_count', 'failed_count')
    list_filter = ('project', 'completed')
    search_fields = ('subject', 'project')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(project=request.user.project)


@admin.register(models.EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    model = models.EmailTemplate
    
    list_display = ('name', 'project', 'use_for', 'enabled')
    list_filter = ('project', 'enabled')
    search_fields = ('name', 'project', 'use_for')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(project=request.user.project)
    
    def save_model(self, request, obj, form, change):
        if not obj.user:
            obj.user = request.user
        obj.save()