ENHANCED STOPWATCH APPLICATION
==============================

FEATURES
--------
- Start, pause, resume, reset stopwatch
- Record lap durations and total elapsed times
- Save sessions to SQLite
- View saved sessions and lap details
- Export sessions to CSV
- Generate a Matplotlib lap-time chart

REQUIREMENTS
------------
- Python 3.10 or newer recommended
- Internet connection for the initial package installation
- VS Code or another text editor (optional)

RUN ON WINDOWS
--------------
1. Extract Enhanced-Stopwatch.zip.
2. Open the extracted Enhanced-Stopwatch folder in VS Code.
3. Open Terminal > New Terminal.
4. Create a virtual environment:
       python -m venv venv
5. Activate it:
       venv\Scripts\activate
   If you use PowerShell and activation is blocked, use Command Prompt
   in VS Code or run venv\Scripts\python.exe directly.
6. Install dependencies:
       python -m pip install -r requirements.txt
7. Start the app:
       python app.py
8. Open this address in your browser:
       http://127.0.0.1:5000

IF `python` DOES NOT WORK
-------------------------
Try using `py` instead, for example:
       py -m venv venv
       py -m pip install -r requirements.txt
       py app.py

HOW TO USE
----------
1. Enter a session name.
2. Click Start.
3. Click Lap one or more times while the timer runs.
4. Click Pause.
5. Click Save Session.
6. Under Saved Sessions, choose View Laps, Export CSV, or View Chart.
7. Click Reset to clear the current stopwatch and begin a new session.

NOTES
-----
- The SQLite database file (stopwatch.db) is created automatically on first run.
- Saved sessions remain after closing the browser, as long as stopwatch.db is retained.
- Reset clears only the current unsaved timer; it does not delete saved sessions.
- Stop the server with Ctrl+C in the terminal.
- This is a local development project. Do not expose Flask debug mode publicly.
