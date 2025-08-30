# ISKCON Gorakhpur Website

This repository contains the source code of a Django based website for ISKCON Gorakhpur. It is a standard Django project composed of several apps (`homepage`, `donation`, `services`, `festivals`, `who_we_are`).

## Prerequisites

- Python 3.12 or newer
- PostgreSQL server
- `virtualenv` (optional but recommended)

## Setup

1. **Clone the repository**

   ```bash
   git clone <repo-url>
   cd iskcongkp
   ```

2. **Create and activate a virtual environment**

   ```bash
   python3 -m venv env
   source env/bin/activate
   ```

3. **Install dependencies**

    Install the project dependencies using the provided `requirements.txt`:

    ```bash
    pip install -r requirements.txt
    ```

4. **Create a PostgreSQL database**

   Create a database named `iskcongkp` and a user that matches your settings. By default the configuration is in `iskcongkp/settings/base.py`.

   ```
   NAME: iskcongkp
   USER: vishnuvahan
   PASSWORD: <your db password>
   HOST: localhost
   PORT: 5432
   ```

## Environment variables

The project expects the following environment variables which can be placed in a `.env` file in the project root:

- `ENVIRONMENT_NAME` – selects the settings module. Set to `production` to use `iskcongkp.settings.production`, otherwise `iskcongkp.settings.base` is used.
- `PASSWORD` – database password for the production settings file.
- `HDFC_MERCHANT_ID` – merchant identifier for HDFC SmartGateway.
- `HDFC_API_KEY` – API key for HDFC SmartGateway.

Ensure `HDFC_MERCHANT_ID` and `HDFC_API_KEY` are configured in every environment where payments are processed.

Example `.env`:

```ini
ENVIRONMENT_NAME=production
PASSWORD=your_db_password
HDFC_MERCHANT_ID=your_merchant_id
HDFC_API_KEY=your_api_key
```

## Running the site

Run migrations and start the development server:

```bash
python manage.py migrate
python manage.py runserver
```

The server will start on `http://127.0.0.1:8000/`.

For production you can use gunicorn:

```bash
gunicorn iskcongkp.wsgi
```

Static files are served from the `assets/` directory and media uploads from `media/`.

