# jobs/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator
from notifications.models import Channels
from datetime import timedelta


class JobFrequency(models.TextChoices):
    """
    Predefined frequency choices for job search scheduling
    """
    EVERY_5_MINUTES = '5', 'Every 5 minutes'
    EVERY_15_MINUTES = '15', 'Every 15 minutes'
    EVERY_30_MINUTES = '30', 'Every 30 minutes'
    HOURLY = '60', 'Every hour'
    EVERY_3_HOURS = '180', 'Every 3 hours'
    EVERY_6_HOURS = '360', 'Every 6 hours'
    DAILY = '1440', 'Daily'
    CUSTOM = 'custom', 'Custom'


class Job(models.Model):
    """
    Model to store scraped jobs from Upwork

    This model stores all job information including title, URL, pricing details,
    skills required, and status flags for tracking engagement with the job.

    Fields:
        title (str): The job title
        url (str): The unique URL of the job listing
        price_type (str): Either 'Hourly' or 'Fixed Price'
        price_range (str): Price range for the job as a string (e.g., "Hourly: $10.00 - $20.00")
        skills (str): Comma-separated list of required skills
        posted_date (str): When the job was posted, as shown on Upwork (e.g., "4 hours ago")
        estimated_time (str): Estimated project duration (e.g., "1 to 3 months")
        description (str): Full job description if scraped
        experience_level (str): Required experience level

        user (User): The user who owns this job record
        search_query (JobSearchQuery): The search query that found this job

        created_at (datetime): When this record was created
        updated_at (datetime): When this record was last updated

        is_viewed (bool): Whether the user has viewed this job
        is_applied (bool): Whether the user has applied to this job
        is_favorited (bool): Whether the user has marked this job as a favorite
    """
    title = models.CharField(max_length=255)
    url = models.URLField()
    price_type = models.CharField(max_length=50, choices=[('Hourly', 'Hourly'), ('Fixed Price', 'Fixed Price')], default='Hourly')
    price_range = models.CharField(max_length=255, null=True, blank=True)  # Store the price range as a string
    skills = models.TextField(null=True, blank=True)
    posted_date = models.CharField(max_length=50)
    estimated_time = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    experience_level = models.CharField(max_length=100, null=True, blank=True)

    # References
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jobs')
    search_query = models.ForeignKey('JobSearchQuery', on_delete=models.CASCADE, related_name='jobs', null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Status flags
    is_viewed = models.BooleanField(default=False)
    is_applied = models.BooleanField(default=False)
    is_favorited = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'url')  # Ensure that the URL is unique per user
        indexes = [
            models.Index(fields=['url']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return self.title


class JobSearchQuery(models.Model):
    """
    Model to store search queries for job scraping with scheduling configuration

    This model stores the search criteria and scheduling parameters for periodic
    job searches. It allows users to configure when and how often to search for
    jobs on Upwork.

    Fields:
        user (User): The user who created this search query
        name (str): A descriptive name for this search query
        search_url (str): The complete Upwork search URL to scrape
        search_keywords (str): Keywords used in the search (for reference)
        notification_channel (Channels): Where to send notifications for new jobs

        is_active (bool): Whether this search query is active and should be run
        schedule_type (str): The type of schedule (predefined or custom)
        frequency (int): How often to run this search (in minutes)
        custom_frequency (int): For custom schedules, the minutes between runs
        last_run (datetime): When this search was last executed
        next_run (datetime): When this search is scheduled to run next

        total_jobs_found (int): Total number of jobs found by this search
        total_notifications_sent (int): Total notifications sent for this search

        created_at (datetime): When this search query was created
        updated_at (datetime): When this search query was last updated
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_searches')
    name = models.CharField(max_length=100)
    search_url = models.URLField(max_length=1000)
    search_keywords = models.CharField(max_length=255, help_text="Keywords used in the search")
    notification_channel = models.ForeignKey(Channels, on_delete=models.CASCADE, related_name='job_searches')

    # Scheduling configuration
    is_active = models.BooleanField(default=True)
    schedule_type = models.CharField(
        max_length=10,
        choices=JobFrequency.choices,
        default=JobFrequency.HOURLY,
        help_text="How frequently to run this search"
    )
    frequency = models.IntegerField(
        default=60,  # Default to hourly
        help_text="Frequency in minutes to run this search"
    )
    custom_frequency = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Custom frequency in minutes (only used if schedule_type is 'custom')"
    )
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)

    # Stats
    total_jobs_found = models.IntegerField(default=0)
    total_notifications_sent = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ('user', 'name')
        verbose_name = "Job Search Query"
        verbose_name_plural = "Job Search Queries"

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    def save(self, *args, **kwargs):
        """
        Override save method to handle frequency calculation and next_run update
        """
        # Set the actual frequency based on schedule type
        if self.schedule_type != JobFrequency.CUSTOM:
            self.frequency = int(self.schedule_type)
        elif self.custom_frequency:
            self.frequency = self.custom_frequency

        # If this is a new search query or next_run is not set, set it
        if not self.pk or not self.next_run:
            self.next_run = timezone.now()

        super().save(*args, **kwargs)

    def update_next_run(self):
        """
        Update the next scheduled run time based on frequency
        """
        now = timezone.now()
        self.last_run = now
        self.next_run = now + timedelta(minutes=self.frequency)
        self.save(update_fields=['last_run', 'next_run'])


class JobSearchLog(models.Model):
    """
    Model to log job search execution history

    This model records details about each execution of a job search, including
    timing, results, and any errors that occurred.

    Fields:
        search_query (JobSearchQuery): The search query that was executed
        start_time (datetime): When the search execution started
        end_time (datetime): When the search execution finished
        jobs_found (int): Number of jobs found during this execution
        new_jobs_saved (int): Number of new jobs saved to the database
        notifications_sent (int): Number of notifications sent during this execution
        status (str): The outcome of the execution (success, error, running)
        error_message (str): Details about any errors that occurred
    """
    search_query = models.ForeignKey(JobSearchQuery, on_delete=models.CASCADE, related_name='logs')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    jobs_found = models.IntegerField(default=0)
    new_jobs_saved = models.IntegerField(default=0)
    notifications_sent = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=[
        ('success', 'Success'),
        ('error', 'Error'),
        ('running', 'Running')
    ], default='running')
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.search_query.name} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"

    def complete_with_success(self, jobs_found, new_jobs_saved, notifications_sent):
        """
        Mark this log as successfully completed with result statistics

        Args:
            jobs_found (int): Number of jobs found during execution
            new_jobs_saved (int): Number of new jobs saved during execution
            notifications_sent (int): Number of notifications sent during execution
        """
        self.end_time = timezone.now()
        self.jobs_found = jobs_found
        self.new_jobs_saved = new_jobs_saved
        self.notifications_sent = notifications_sent
        self.status = 'success'
        self.save()

    def complete_with_error(self, error_message):
        """
        Mark this log as failed with an error message

        Args:
            error_message (str): Description of the error that occurred
        """
        self.end_time = timezone.now()
        self.status = 'error'
        self.error_message = error_message
        self.save()
