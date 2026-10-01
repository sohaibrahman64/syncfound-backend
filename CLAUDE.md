# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- **Run the backend**: `uvicorn app.main:app --reload`
- **Install dependencies**: `pip install -r requirements.txt`
- **Run tests**: No test framework detected yet; likely manual testing via API endpoints.
- **Database migrations**: Uses Alembic; run `alembic upgrade head` to apply migrations.
- **Linting**: No linter configured; consider adding flake8 or pylint.
- **Format code**: No formatter configured; consider adding black or isort.

## Project Structure

- `app/main.py`: FastAPI application entry point, includes routers and startup events.
- `app/models/`: SQLAlchemy models for various entities (users, chats, monetization, etc.).
- `app/routes/`: API route modules organized by feature (auth, chats, matches, etc.).
- `app/services/`: External service integrations (Firebase, Apify, Google Cloud Storage).
- `app/database.py`: Database connection and session setup.
- `uploads/`: Directory for locally stored uploaded files (when local storage enabled).
- `.env`: Environment variables (not committed; see .gitignore).
- `requirements.txt`: Python dependencies.

## Architecture Overview

This is a FastAPI-based backend for the Syncfound platform, likely a cofounder matching service. Key features:

- **Authentication**: Auth routes handle user registration/login.
- **Profiles**: User profile and LinkedIn integration.
- **Matching**: Matching algorithms based on roles, skills, location, and preferences.
- **Chats**: Real-time chat functionality between matched users.
- **Monetization**: Premium subscription handling via payment gateway.
- **Invites**: Invitation system for user referrals.
- **Storage**: File uploads handled via Google Cloud Storage or local storage.
- **External APIs**: Apify for web scraping, Firebase for notifications.

## Common Tasks

- **Adding a new endpoint**: Create a new router in `app/routes/`, define Pydantic schemas in `app/schemas/` (if exists), and register the router in `app/main.py`.
- **Adding a model**: Define a SQLAlchemy model in `app/models/` and ensure it's imported in `app/main.py` for table creation.
- **Configuring CORS**: Adjust `origins` list in `app/main.py` via `CORS_ORIGINS` environment variable.
- **Running locally**: Set environment variables in `.env` (copy from example if available), then start the server.

## Environment Variables

Key variables (set in `.env`):
- `DATABASE_URL`: PostgreSQL connection string.
- `CORS_ORIGINS`: Comma-separated list of allowed origins.
- Firebase credentials: Path to service account JSON.
- Google Cloud Storage: Bucket name and credentials.
- Apify API token.
- Payment gateway keys (for monetization).

## Notes

- The project uses SQLAlchemy 2.0 with Alembic for migrations.
- Pydantic v2 is used for data validation.
- Firebase Admin SDK initialized on startup for push notifications.
- Local storage toggle via `is_local_storage_enabled()` in `storage_service`.