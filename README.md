# CoolCuts

CoolCuts is a full-stack barber appointment booking platform built with Django REST Framework and React. It includes user authentication, OTP-based registration, Google sign-in, appointment booking, appointment history, profile management, and an admin panel for managing services and appointments.

## Tech Stack

- Backend: Django, Django REST Framework, Simple JWT
- Frontend: React, Vite, Tailwind CSS, Axios
- Database: SQLite for local development when `DEBUG=True`, PostgreSQL for production
- Deployment: Render

## Project Structure

- `Coolcuts-backend/` - Django backend
- `Coolcuts-frontend/` - React frontend

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/Vishal18cse/CoolCuts
cd CoolCuts
```

### 2. Backend setup

```bash
cd Coolcuts-backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file using `.env.example`.

Run migrations:

```bash
python manage.py migrate
```

Start the backend server:

```bash
python manage.py runserver
```

### 3. Frontend setup

Open a new terminal:

```bash
cd Coolcuts-frontend
npm install
```

Create a `.env` file using `.env.example`.

Start the frontend:

```bash
npm run dev
```

To create a production build:

```bash
npm run build
```

## Environment Variables

Backend variables are documented in `Coolcuts-backend/.env.example`.

Frontend variables are documented in `Coolcuts-frontend/.env.example`.
