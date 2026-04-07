# StudyGenie Notes Manager (Flask + MongoDB)

Student-friendly notes manager with:
- Sign up / Sign in (session-based)
- Notes CRUD (add/edit/delete)
- Export notes to PDF
- Calendar events (FullCalendar)

## Prerequisites
- Python 3.10+ (recommended)
- MongoDB running locally (or MongoDB Atlas)

## Setup
1) Create and activate a virtual environment (recommended).

2) Install dependencies:
```bash
pip install -r requirements.txt
```

3) Create a `.env` file (copy from `.env.example`) and edit values:
- `FLASK_SECRET_KEY`
- `MONGODB_URI`
- `MONGODB_DB`

4) Run the app:
```bash
python app.py
```

Open `http://127.0.0.1:5000`

## Project structure
- `app.py`: Flask app entry
- `db.py`: MongoDB connection helpers
- `auth.py`: auth helpers + decorators
- `templates/`: HTML pages (Jinja2)
- `static/`: CSS/JS/assets

