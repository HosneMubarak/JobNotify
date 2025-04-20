# jobs/admin.py

from django.contrib import admin
from django.utils import timezone
from .models import Job, JobSearchQuery, JobSearchLog, JobFrequency
from django.utils.html import format_html


class JobAdmin(admin.ModelAdmin):
    """
    Custom admin for managing jobs
    """
    # Display essential fields in the list view for quick insight
    list_display = (
        'title', 'price_type', 'price_range', 'posted_date', 'is_viewed', 'is_applied', 'is_favorited', 'user',
        'created_at'
    )
    # Fields to make clickable in the admin panel for easy navigation
    list_display_links = ('title',)

    # Filters for admin to easily filter job listings based on status and type
    list_filter = ('price_type', 'is_viewed', 'is_applied', 'is_favorited', 'user')

    # Fields that will be searched
    search_fields = ('title', 'skills', 'description', 'experience_level')

    # Editable fields that can be modified from the list view
    list_editable = ('is_viewed', 'is_applied', 'is_favorited')

    # Sorting the list based on created_at (most recent first)
    ordering = ('-created_at',)

    # Using raw ID fields to handle ForeignKey fields more efficiently
    raw_id_fields = ('user', 'search_query')

    # Grouping the data by date for better insights
    date_hierarchy = 'created_at'

    # Fields that shouldn't be editable directly (timestamps)
    readonly_fields = ('created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        """
        Override save to auto-set updated_at timestamp when editing
        """
        if not obj.pk:
            obj.created_at = timezone.now()
        obj.updated_at = timezone.now()
        super().save_model(request, obj, form, change)


class JobSearchQueryAdmin(admin.ModelAdmin):
    """
    Custom admin for managing job search queries
    """
    # Display fields that are most relevant for managing search queries
    list_display = (
        'name', 'user', 'schedule_type', 'frequency', 'last_run', 'next_run', 'is_active'
    )
    list_display_links = ('name',)

    # Filters to manage search query status and schedule
    list_filter = ('is_active', 'schedule_type', 'user')

    # Fields for searching
    search_fields = ('name', 'search_keywords')

    # Ordering based on creation date
    ordering = ('-created_at',)

    # Using raw ID fields for user and notification_channel
    raw_id_fields = ('user', 'notification_channel')

    # Grouping data by creation date
    date_hierarchy = 'created_at'

    # Make timestamps read-only for clarity and avoid accidental editing
    readonly_fields = ('created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        """
        Override save to calculate and set the next_run time when saving
        """
        if not obj.pk or not obj.next_run:
            obj.next_run = timezone.now()
        super().save_model(request, obj, form, change)


class JobSearchLogAdmin(admin.ModelAdmin):
    """
    Custom admin for managing job search logs
    """
    # Essential fields displayed in the log list view
    list_display = (
        'search_query', 'start_time', 'end_time', 'jobs_found', 'new_jobs_saved', 'notifications_sent', 'status'
    )
    list_display_links = ('search_query',)

    # Filters based on search query status
    list_filter = ('status', 'search_query')

    # Fields for searching within the logs
    search_fields = ('search_query__name', 'error_message')

    # Ordering by start time (most recent first)
    ordering = ('-start_time',)

    # Using raw ID fields for search_query field
    raw_id_fields = ('search_query',)

    # Grouping by start time
    date_hierarchy = 'start_time'

    # Read-only fields for log data that should not be modified
    readonly_fields = ('start_time', 'end_time', 'status')


# Register the models with their customized admin views
admin.site.register(Job, JobAdmin)
admin.site.register(JobSearchQuery, JobSearchQueryAdmin)
admin.site.register(JobSearchLog, JobSearchLogAdmin)
