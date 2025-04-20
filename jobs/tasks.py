from huey import crontab
from huey.contrib.djhuey import db_periodic_task, db_task
from django.utils import timezone
from django.contrib.auth.models import User
import logging

from .models import JobSearchQuery, JobSearchLog, Job
from .scraper import UpworkScraper, send_notification_via_apprise
from notifications.models import Channels, ChannelTypes, Notifications, NotificationStatus

logger = logging.getLogger('jobs.tasks')


@db_task()
def run_job_search(search_query_id):
    """
    Task to run a specific job search query and process results

    Args:
        search_query_id (int): ID of the JobSearchQuery to run
    """
    try:
        # Get the search query
        search_query = JobSearchQuery.objects.get(id=search_query_id)

        # Create a log entry for this run
        log_entry = JobSearchLog.objects.create(
            search_query=search_query,
            start_time=timezone.now()
        )

        # Run the job search
        try:
            # Create a scraper instance and run the search
            scraper = UpworkScraper(headless=True, debug=True)
            job_listings = scraper.scrape_jobs(search_query.search_url)

            # Process results
            new_jobs = 0
            notifications_sent = 0

            # For each job listing, check if it's new and save it
            for job_data in job_listings:
                # Some basic validation
                if not job_data.get('url') or not job_data.get('title'):
                    continue

                # Check if this job already exists for this user
                job_exists = Job.objects.filter(
                    user=search_query.user,
                    url=job_data['url']
                ).exists()

                if not job_exists:
                    # Create a new job
                    new_job = Job(
                        title=job_data.get('title', ''),
                        url=job_data['url'],
                        price_type=job_data.get('price_type', 'Hourly'),
                        price_range=job_data.get('price_range', ''),
                        skills=job_data.get('skills', ''),
                        posted_date=job_data.get('posted_date', ''),
                        estimated_time=job_data.get('estimated_time', ''),
                        description=job_data.get('description', ''),
                        experience_level=job_data.get('experience_level', ''),
                        user=search_query.user,
                        search_query=search_query
                    )
                    new_job.save()
                    new_jobs += 1

                    # Queue notification task
                    send_job_notification.schedule(
                        args=(new_job.id, search_query.notification_channel.id),
                        delay=2
                    )
                    notifications_sent += 1

            # Update search query stats
            search_query.total_jobs_found += len(job_listings)
            search_query.total_notifications_sent += notifications_sent

            # Update next run time
            search_query.update_next_run()

            # Complete log with success
            log_entry.complete_with_success(
                jobs_found=len(job_listings),
                new_jobs_saved=new_jobs,
                notifications_sent=notifications_sent
            )

            logger.info(
                f"Successfully ran job search '{search_query.name}': "
                f"found {len(job_listings)} jobs, saved {new_jobs} new jobs"
            )

        except Exception as e:
            # Log error and update status
            error_msg = f"Error running job search: {str(e)}"
            log_entry.complete_with_error(error_msg)
            logger.error(error_msg, exc_info=True)
        finally:
            # Always close the scraper to clean up resources
            if 'scraper' in locals():
                scraper.close()

    except JobSearchQuery.DoesNotExist:
        logger.error(f"JobSearchQuery with ID {search_query_id} not found")
    except Exception as e:
        logger.error(f"Unexpected error in run_job_search task: {str(e)}", exc_info=True)


@db_task()
def send_job_notification(job_id, channel_id):
    """
    Send a notification for a new job

    Args:
        job_id (int): ID of the job to notify about
        channel_id (int): ID of the notification channel to use
    """
    try:
        job = Job.objects.get(id=job_id)
        channel = Channels.objects.get(id=channel_id)

        # Create notification content
        title = f"New Upwork Job: {job.title}"

        # Create message based on job details
        message = f"*Job Title:* {job.title} 🎯\n"
        message += f"*URL:* [Click here]({job.url}) 🔗\n"
        message += f"*Price:* {job.price_range} 💰\n"

        if job.skills:
            message += f"*Skills:* {job.skills} 🛠️\n"

        message += f"*Posted:* {job.posted_date} 📅\n"

        if job.estimated_time:
            message += f"*Est. Time:* {job.estimated_time} ⏱️\n"

        # Create a notification record
        notification = Notifications.objects.create(
            sender=job.user,
            recipient=job.user,
            body=title,
            extra={
                'job_id': job.id,
                'message': message
            },
            channels_id=channel,
            status=NotificationStatus.QUEUED
        )

        # Send the actual notification
        if channel.config:
            try:
                result = send_notification_via_apprise(
                    channel.config,
                    title,
                    message
                )

                if result:
                    notification.status = NotificationStatus.SENT
                    notification.save()
                    logger.info(f"Notification sent successfully for job ID {job_id}")
                else:
                    notification.status = NotificationStatus.FAILED
                    notification.details = "Failed to send notification"
                    notification.save()
                    logger.error(f"Failed to send notification for job ID {job_id}")
            except Exception as e:
                notification.status = NotificationStatus.FAILED
                notification.details = str(e)[:500]  # Truncate if too long
                notification.save()
                logger.error(f"Error sending notification: {str(e)}")
        else:
            notification.status = NotificationStatus.FAILED
            notification.details = "No channel configuration provided"
            notification.save()
            logger.error(f"No channel configuration for channel ID {channel_id}")

    except Job.DoesNotExist:
        logger.error(f"Job with ID {job_id} not found")
    except Channels.DoesNotExist:
        logger.error(f"Channel with ID {channel_id} not found")
    except Exception as e:
        logger.error(f"Unexpected error in send_job_notification task: {str(e)}", exc_info=True)


@db_periodic_task(crontab(minute='*/5'))
def schedule_job_searches():
    """
    Periodic task that runs every 5 minutes to check for job searches that need to be run
    """
    now = timezone.now()
    logger.info(f"Checking for job searches to run at {now}")

    # Find all active searches that are due to run
    due_searches = JobSearchQuery.objects.filter(
        is_active=True,
        next_run__lte=now
    )

    search_count = due_searches.count()
    logger.info(f"Found {search_count} job searches to run")

    # Schedule individual tasks for each search
    for search in due_searches:
        logger.info(f"Scheduling job search: {search.name} (ID: {search.id})")
        run_job_search(search.id)
