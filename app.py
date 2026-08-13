import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

from config import CATEGORIES

BASE_DIR = Path(__file__).parent
DATABASE = Path(os.environ.get("PAPERS_DB", BASE_DIR / "papers.db"))

app = Flask(__name__)


def connect():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with connect() as database:
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS papers (
                arxiv_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                abstract TEXT NOT NULL,
                primary_category TEXT NOT NULL,
                categories TEXT NOT NULL,
                published TEXT NOT NULL,
                updated TEXT NOT NULL,
                arxiv_url TEXT NOT NULL,
                pdf_url TEXT NOT NULL
            )
            """
        )


@app.get("/")
def index():
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    per_page = 40
    category = request.args.get("category", "")
    if category and category not in CATEGORIES:
        category = ""
    selected_date = request.args.get("date", "")
    try:
        if datetime.strptime(selected_date, "%Y-%m-%d").date() > date.today():
            selected_date = ""
    except ValueError:
        selected_date = ""
    range_start = request.args.get("start", "")
    range_end = request.args.get("end", "")
    try:
        start_value = datetime.strptime(range_start, "%Y-%m-%d").date()
        end_value = datetime.strptime(range_end, "%Y-%m-%d").date()
        if start_value > end_value or end_value > date.today():
            range_start = range_end = ""
    except ValueError:
        range_start = range_end = ""

    conditions = []
    parameters = []
    if category:
        conditions.append("instr(',' || categories || ',', ',' || ? || ',') > 0")
        parameters.append(category)

    archive_query = "SELECT substr(published, 1, 10) AS day, COUNT(*) AS count FROM papers"
    if conditions:
        archive_query += " WHERE " + " AND ".join(conditions)
    archive_query += " GROUP BY day ORDER BY day DESC"

    with connect() as database:
        archive = database.execute(archive_query, parameters).fetchall()
        paper_conditions = list(conditions)
        paper_parameters = list(parameters)
        if selected_date:
            paper_conditions.append("substr(published, 1, 10) = ?")
            paper_parameters.append(selected_date)
        elif range_start:
            paper_conditions.append("substr(published, 1, 10) BETWEEN ? AND ?")
            paper_parameters.extend((range_start, range_end))

        query = "SELECT * FROM papers"
        if paper_conditions:
            query += " WHERE " + " AND ".join(paper_conditions)
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        total = database.execute(count_query, paper_parameters).fetchone()[0]
        pages = max(1, (total + per_page - 1) // per_page)
        page = min(page, pages)
        query += " ORDER BY published DESC LIMIT ? OFFSET ?"
        papers = database.execute(
            query, paper_parameters + [per_page, (page - 1) * per_page]
        ).fetchall()

    return render_template(
        "index.html",
        papers=papers,
        categories=CATEGORIES,
        selected=category,
        archive=archive,
        selected_date=selected_date,
        range_start=range_start,
        range_end=range_end,
        today=date.today().isoformat(),
        added=request.args.get("added"),
        page=page,
        pages=pages,
        total=total,
    )


@app.post("/fetch")
def fetch_days():
    start = request.form.get("start", "")
    end = request.form.get("end", "")
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError:
        return "Choose valid start and end dates.", 400
    if start_date > end_date:
        return "The start date must be before the end date.", 400
    if end_date > date.today():
        return "Choose today or an earlier end date.", 400
    if (end_date - start_date).days > 30:
        return "Choose a range of 31 days or fewer.", 400

    from fetch import fetch_range

    added = fetch_range(start, end)
    return redirect(url_for("index", start=start, end=end, added=added))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
