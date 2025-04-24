
# Django Job Search Automation Project

This Django project is designed to automate job search queries, such as fetching and filtering job listings from platforms like Upwork, with notification capabilities via channels like Telegram.

## Features

- Run periodic job searches based on user-defined criteria.
- Integrate with notification channels (e.g., Telegram).
- Use Huey for asynchronous task processing.
- Create and test job search queries via Django management commands.

---

## Getting Started

### Prerequisites

- Python 3.9+
- Django 4+
- Sqlite
- Huey (for task queue)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/yourproject.git
   cd yourproject
   ```
   
   ```bash
   SECRET_KEY=your-secret-key
   DEBUG=True
   ALLOWED_HOSTS=your-domain.com
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Create a `.env` file and define necessary values (e.g., DB credentials, secret key, etc.).

5. **Apply migrations**

   ```bash
   python manage.py migrate
   ```

6. **Create a superuser (optional)**

   ```bash
   python manage.py createsuperuser
   ```

7. Before deploying to production or when serving static files, run:

   ```bash
   python manage.py collectstatic
   ```

---

## Running the Project

### Development Server

```bash
python manage.py runserver
```

### Running Huey

This project uses [Huey](https://huey.readthedocs.io/en/latest/) with threaded workers for background tasks:

```bash
python manage.py run_huey --workers=2 --worker-type=thread
```

---

## Test Job Search Command

You can use the built-in management command to test the job search automation:

### Create a Test Job Search

```bash
python manage.py test_job_search --create --user_id=1
```

If `--user_id` is not provided, the command will use the first available user.

### Run a Specific Search

```bash
python manage.py test_job_search --search_id=5
```

This will manually run a job search task with ID 5 using the `run_job_search` task function.

### List Available Searches

```bash
python manage.py test_job_search
```

Displays all existing job search queries in the database.

---

## Project Structure

```
jobs/
  └── tasks.py        # Contains the run_job_search function
  └── models.py       # JobSearchQuery and JobFrequency models

notifications/
  └── models.py       # ChannelTypes and Channels models

jobs/management/commands/
  └── test_job_search.py  # Custom command to test job search
```

---

## Contributing

Feel free to open issues or submit pull requests if you'd like to contribute.

---

## License

This project is licensed under the MIT License.
