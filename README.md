# Nova 210 SE Backend

## Setting up development environment

### Requirements

- Python >= 3.12.0 (supports `f"{a.get("b")}"`)
- pip

### Steps

1. Clone the repository
2. (Optional, recommended) Create a virtual environment
3. Install the requirements
4. Install dependencies `pip install -r requirements.txt`
5. Make directory for database `mkdir data`
6. Run migrations `python manage.py migrate`
7. Run the server `python manage.py runserver`

### Override config

You *should* override the default config by creating a `settings.local.py` file in the root directory of the project.

This file will be executed dynamically at the end of the `backend/settings.py` file, so you can override any settings you want.

You may want to override:

- `DEBUG` to `True` so that detailed server error (500) message is printed
- `CORS_ORIGIN_ALLOW_ALL` to `True` so that local frontend can access the API
- `ALLOWED_HOSTS` to `["*"]` so that the server can be accessed from any host

### Add pre-commit hook

Use `git config core.hooksPath .githooks` to add pre-commit hook.
