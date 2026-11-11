# University Placement System

Flask + MySQL campus recruitment app built from the SRS (v1.0).

## Run it (Windows cmd)
```
cd path\to\ups
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
1. Start MySQL (XAMPP: press Start next to MySQL) and create the database `placement_db`
   (phpMyAdmin > New, or run `schema.sql`).
2. Create a file named `.env` next to `app.py` (copy `.env.example`):
```
SECRET_KEY=a-long-random-string
DATABASE_URL=mysql+pymysql://root:@localhost/placement_db?charset=utf8mb4
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
OPENAI_MODEL=models/gemini-flash-lite-latest
OPENAI_API_KEY=your-key
```
3. Load demo data and start:
```
python seed.py
flask --app app run --debug
```
Open http://127.0.0.1:5000

| Role | Email | Password |
|---|---|---|
| Admin | admin@university.edu | Admin@123 |
| Student | student1@university.edu | Student@123 |

Change the admin password before real use. No MySQL? Use `DATABASE_URL=sqlite:///dev.db`.

## AI assistant
A chat section on the home page and at `/assistant`, grounded in the open jobs and, for logged-in students, their own CGPA and applications. It uses any OpenAI-compatible API (default: Google Gemini; get a key at https://aistudio.google.com/apikey). Run `python check_ai.py` to test your key in one step (it never prints the key). Never commit `.env` or share the key. Requests are rate-limited (15 per 10 minutes per user/IP, `AI_RATE_LIMIT`).

If the AI provider fails (bad key, no quota, blocked), the assistant still answers common questions (open jobs, eligibility, status, packages, deadlines, interview and CV tips) from the site’s own data. Set `AI_FALLBACK=0` to show errors instead.

## Troubleshooting
- `ssl.SSLError: [ASN1: NOT_ENOUGH_DATA]` on Windows: caused by a damaged certificate in the Windows store. The app connects to local MySQL without TLS, so it is avoided. Set `MYSQL_SSL=1` only if your server requires TLS.
- `Can't connect to MySQL`: MySQL is not started.
- Chat says Basic mode / error: run `python check_ai.py` and read the RESULT line.

## Design
Dark animated skyline header on every page (SVG + CSS, no image files), scroll-driven motion (progress bar, parallax skyline whose windows light up and dawn glow as you scroll, word-by-word headings, scrubbed process line, staggered reveals, auto-hiding header), toasts, and a team section. All motion respects reduced-motion settings.

## Team
Submitted by: Ashikujjaman Sifat (04324205101156), Nehan Ahamed Niloy (04324205101158), Anannya Islam (04324205101161), Turjoy Saha (04324205101163), University of Information Technology & Sciences (UITS).

## Tests
`pytest -q`

## SRS coverage
FR-1 to FR-17 and NFR-1 to NFR-8 are implemented. Also included from the suggested enhancements: edit/delete jobs, job search with pagination, CSV export of applicants. Extras: student profile page, deadline enforcement, CSRF protection.

## Structure
`config.py` settings, `models.py` data layer, `routes.py` business logic, `ai.py` assistant, `app.py` app factory, `templates/` + `static/` UI, `seed.py` demo data, `schema.sql` manual DDL, `check_ai.py` key tester, `tests/`.
Not built: password reset, email notifications, resume file upload.

## Production
`gunicorn "app:app"` behind HTTPS, with `COOKIE_SECURE=1` and a strong `SECRET_KEY`.
