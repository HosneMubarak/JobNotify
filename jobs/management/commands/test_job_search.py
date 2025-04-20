# jobs/management/commands/test_job_search.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from jobs.models import JobSearchQuery, JobFrequency
from jobs.tasks import run_job_search
from notifications.models import Channels, ChannelTypes
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test job search functionality'

    def add_arguments(self, parser):
        parser.add_argument('--user_id', type=int, help='User ID to run the search for')
        parser.add_argument('--search_id', type=int, help='Specific search query ID to run')
        parser.add_argument('--create', action='store_true', help='Create a test search query')

    def handle(self, *args, **options):
        if options['create']:
            try:
                user_id = options.get('user_id')
                if not user_id:
                    user = User.objects.first()
                    if not user:
                        self.stdout.write(self.style.ERROR('No users found. Please create a user first.'))
                        return
                else:
                    try:
                        user = User.objects.get(id=user_id)
                    except User.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f'User with ID {user_id} not found.'))
                        return

                # Find or create a channel type
                channel_type, created = ChannelTypes.objects.get_or_create(name='Telegram')

                # Find or create a notification channel
                channel, created = Channels.objects.get_or_create(
                    user=user,
                    name='Test Channel',
                    defaults={
                        'channel_types_id': channel_type,
                        'config': 'tgram://API_KEY:API_SECRET/CHAT_ID/?format=markdown',
                        'description': 'Test notification channel'
                    }
                )

                # Create a test search query
                search_query = JobSearchQuery.objects.create(
                    user=user,
                    name='Test Upwork Python Search',
                    search_url='https://www.upwork.com/nx/search/jobs/?payment_verified=1&proposals=0-4&q=python%20django&sort=recency&page=1&per_page=10',
                    search_keywords='python django',
                    notification_channel=channel,
                    is_active=True,
                    schedule_type=JobFrequency.EVERY_30_MINUTES,
                    next_run=timezone.now()
                )

                self.stdout.write(
                    self.style.SUCCESS(f'Test search query created: ID {search_query.id}')
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating test search: {str(e)}')
                )

        # Run search if specified
        if options['search_id']:
            try:
                search_id = options['search_id']
                search_query = JobSearchQuery.objects.get(id=search_id)

                self.stdout.write(f'Running search query: {search_query.name}')

                # Run the task
                result = run_job_search(search_id)

                self.stdout.write(
                    self.style.SUCCESS(f'Search task completed: {result}')
                )

            except JobSearchQuery.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Search query with ID {search_id} not found')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error running search: {str(e)}')
                )

        # If neither create nor search_id specified, list available searches
        if not options['create'] and not options['search_id']:
            searches = JobSearchQuery.objects.all()

            if searches.exists():
                self.stdout.write('Available search queries:')
                for search in searches:
                    self.stdout.write(f'  ID: {search.id}, Name: {search.name}, User: {search.user.username}')
                self.stdout.write('\nRun with --search_id=X to execute a specific search')
            else:
                self.stdout.write('No search queries found. Use --create to create a test search.')