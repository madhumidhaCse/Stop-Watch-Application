
from flask import Flask, render_template, request, jsonify, Response
import sqlite3
import csv
import io
import os
import math
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from datetime import datetime

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "stopwatch.db")


# ----------------------------------
# DATABASE CONNECTION
# ----------------------------------

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ----------------------------------
# CREATE DATABASE TABLES
# ----------------------------------

def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            total_time REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS laps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            lap_number INTEGER NOT NULL,
            lap_time REAL NOT NULL,
            total_time REAL NOT NULL,
            FOREIGN KEY(session_id)
                REFERENCES sessions(id)
                ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# ----------------------------------
# FORMAT TIME
# ----------------------------------

def format_time(seconds):
    minutes = int(seconds // 60)
    return f"{minutes:02d}:{seconds % 60:06.3f}"


# ----------------------------------
# HOME PAGE
# ----------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ----------------------------------
# SAVE A STOPWATCH SESSION
# ----------------------------------

@app.route("/api/sessions", methods=["POST"])
def save_session():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Invalid request data"
        }), 400

    name = data.get("name", "Stopwatch Session")
    total_time = data.get("total_time")
    lap_data = data.get("laps", [])

    if not isinstance(name, str) or not name.strip() or len(name) > 100:
        return jsonify({
            "error": "Enter a session name (up to 100 characters)"
        }), 400

    if (
        isinstance(total_time, bool)
        or not isinstance(total_time, (int, float))
        or not math.isfinite(total_time)
        or not 0 <= total_time <= 31536000
    ):
        return jsonify({
            "error": "Invalid total time"
        }), 400

    if not isinstance(lap_data, list) or len(lap_data) > 10000:
        return jsonify({
            "error": "Invalid lap data"
        }), 400

    validated_laps = []

    try:
        previous_total = 0.0

        for index, lap in enumerate(lap_data, start=1):
            if not isinstance(lap, dict):
                raise ValueError("Each lap must be an object")

            lap_time = lap.get("lap_time")
            lap_total = lap.get("total_time")

            if (
                isinstance(lap_time, bool)
                or not isinstance(lap_time, (int, float))
                or isinstance(lap_total, bool)
                or not isinstance(lap_total, (int, float))
                or not math.isfinite(lap_time)
                or not math.isfinite(lap_total)
            ):
                raise ValueError("Lap times must be valid numbers")

            if (
                lap_time < 0
                or lap_total < previous_total
                or lap_time > lap_total
                or lap_total > total_time + 0.01
            ):
                raise ValueError("Lap timing values are out of range")

            validated_laps.append(
                (index, float(lap_time), float(lap_total))
            )

            previous_total = float(lap_total)

    except (ValueError, TypeError) as e:
        return jsonify({
            "error": f"Invalid lap timings: {e}"
        }), 400

    conn = get_db_connection()

    try:
        cursor = conn.execute(
            """
            INSERT INTO sessions (
                name,
                total_time,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                name.strip(),
                float(total_time),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )

        session_id = cursor.lastrowid

        conn.executemany(
            """
            INSERT INTO laps (
                session_id,
                lap_number,
                lap_time,
                total_time
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    session_id,
                    number,
                    lap_time,
                    lap_total
                )
                for number, lap_time, lap_total in validated_laps
            ]
        )

        conn.commit()

        return jsonify({
            "message": "Session saved successfully",
            "session_id": session_id
        }), 201

    except sqlite3.Error as e:
        conn.rollback()

        print("DATABASE ERROR:", repr(e))

        return jsonify({
            "error": "Could not save session to the database",
            "details": str(e)
        }), 500

    finally:
        conn.close()


# ----------------------------------
# VIEW SAVED SESSIONS
# ----------------------------------

@app.route("/api/sessions", methods=["GET"])
def get_sessions():
    conn = get_db_connection()

    sessions = conn.execute("""
        SELECT
            s.id,
            s.name,
            s.total_time,
            s.created_at,
            COUNT(l.id) AS lap_count
        FROM sessions s
        LEFT JOIN laps l ON s.id = l.session_id
        GROUP BY s.id
        ORDER BY s.id DESC
    """).fetchall()

    conn.close()

    result = []

    for session in sessions:
        item = dict(session)

        item["formatted_time"] = format_time(
            item["total_time"]
        )

        result.append(item)

    return jsonify(result)


# ----------------------------------
# VIEW DETAILS OF ONE SESSION
# ----------------------------------

@app.route("/api/sessions/<int:session_id>", methods=["GET"])
def get_session(session_id):
    conn = get_db_connection()

    session = conn.execute(
        "SELECT * FROM sessions WHERE id = ?",
        (session_id,)
    ).fetchone()

    if session is None:
        conn.close()

        return jsonify({
            "error": "Session not found"
        }), 404

    laps = conn.execute(
        """
        SELECT
            lap_number,
            lap_time,
            total_time
        FROM laps
        WHERE session_id = ?
        ORDER BY lap_number
        """,
        (session_id,)
    ).fetchall()

    conn.close()

    return jsonify({
        "id": session["id"],
        "name": session["name"],
        "total_time": session["total_time"],
        "formatted_time": format_time(
            session["total_time"]
        ),
        "created_at": session["created_at"],
        "laps": [
            {
                "lap_number": lap["lap_number"],
                "lap_time": lap["lap_time"],
                "formatted_lap_time": format_time(
                    lap["lap_time"]
                ),
                "total_time": lap["total_time"],
                "formatted_total_time": format_time(
                    lap["total_time"]
                )
            }
            for lap in laps
        ]
    })


# ----------------------------------
# EXPORT SESSION TO CSV
# ----------------------------------

@app.route("/api/sessions/<int:session_id>/csv")
def export_csv(session_id):
    conn = get_db_connection()

    session = conn.execute(
        "SELECT * FROM sessions WHERE id = ?",
        (session_id,)
    ).fetchone()

    if session is None:
        conn.close()

        return jsonify({
            "error": "Session not found"
        }), 404

    laps = conn.execute(
        """
        SELECT
            lap_number,
            lap_time,
            total_time
        FROM laps
        WHERE session_id = ?
        ORDER BY lap_number
        """,
        (session_id,)
    ).fetchall()

    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Session Name",
        session["name"]
    ])

    writer.writerow([
        "Date",
        session["created_at"]
    ])

    writer.writerow([
        "Total Time (seconds)",
        session["total_time"]
    ])

    writer.writerow([])

    writer.writerow([
        "Lap Number",
        "Lap Time (seconds)",
        "Total Elapsed Time (seconds)"
    ])

    for lap in laps:
        writer.writerow([
            lap["lap_number"],
            lap["lap_time"],
            lap["total_time"]
        ])

    csv_content = "\ufeff" + output.getvalue()

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                f"attachment; filename=stopwatch_session_{session_id}.csv"
        }
    )


# ----------------------------------
# GENERATE LAP TIME CHART
# ----------------------------------

@app.route("/api/sessions/<int:session_id>/chart")
def session_chart(session_id):
    conn = get_db_connection()

    session = conn.execute(
        "SELECT * FROM sessions WHERE id = ?",
        (session_id,)
    ).fetchone()

    if session is None:
        conn.close()

        return jsonify({
            "error": "Session not found"
        }), 404

    laps = conn.execute(
        """
        SELECT
            lap_number,
            lap_time
        FROM laps
        WHERE session_id = ?
        ORDER BY lap_number
        """,
        (session_id,)
    ).fetchall()

    conn.close()

    if not laps:
        return jsonify({
            "error": "No laps available for this chart"
        }), 400

    lap_numbers = [
        lap["lap_number"]
        for lap in laps
    ]

    lap_times = [
        lap["lap_time"]
        for lap in laps
    ]

    fig, ax = plt.subplots(figsize=(9, 4.5))

    ax.bar(lap_numbers, lap_times)

    ax.set_title(
        f"Lap Time Analysis - {session['name']}"
    )

    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Duration (seconds)")
    ax.set_xticks(lap_numbers)

    ax.grid(
        axis="y",
        linestyle="--",
        alpha=0.4
    )

    fig.tight_layout()

    image_data = io.BytesIO()

    fig.savefig(
        image_data,
        format="png",
        dpi=120
    )

    plt.close(fig)

    image_data.seek(0)

    return Response(
        image_data.getvalue(),
        mimetype="image/png"
    )


# ----------------------------------
# RUN APPLICATION
# ----------------------------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
