# Chat Support System (Django)

A complete starter implementation covering the supplied Chat Support System Part 1 and Day 87 requirements.

## Included
- User registration, login and logout
- Ticket creation, status tracking and ticket-specific chat messages
- Gemini FAQ endpoint
- Staff profiles and departments
- Unassigned staff queue, claim-ticket action and personal staff queue
- Gemini ticket priority + department suggestion, with safe fallback
- Django admin, unit tests, static files and Gunicorn configuration

## Setup (Windows PowerShell / CMD)
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py makemigrations support
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Open http://127.0.0.1:8000/

## Setup (macOS/Linux)
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations support
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Gemini setup
Add your key to `.env`:
`GEMINI_API_KEY=your-key-here`

The model defaults to `gemini-2.5-flash`. Override with `GEMINI_MODEL` if needed.
If the key is absent or the API is temporarily unavailable, ticket creation still works
using Medium priority and the Technical department as fallback. FAQ shows a helpful
message instead of breaking the site.

## Staff setup
1. Sign in to `/admin/` using your superuser.
2. Create a normal Django User for each staff member (or promote an existing user).
3. Create a StaffProfile for that user and choose their department.
4. Staff users can access `/staff/` and `/staff/my-tickets/`.

A user must have a StaffProfile to use staff queue pages. Superusers can access staff pages too.

## Tests
```bash
python manage.py test
```

## Production checklist
- Set `DEBUG=False`.
- Set a strong `SECRET_KEY` in environment variables.
- Set `ALLOWED_HOSTS` to your real domain(s).
- Configure a production database (MySQL can be enabled using the DATABASE_URL approach
  in settings, or replace the default SQLite DATABASES setting).
- Run `python manage.py collectstatic`.
- Run `gunicorn support_system.wsgi:application`.

This project uses synchronous Django views and the `requests` library for Gemini HTTP calls.
The supplied learning material describes an asynchronous API call; if strict async I/O is
required in your deployment, move the Gemini HTTP client to an async HTTP library and use
Django async views with async-safe ORM access.
