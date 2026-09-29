"""
MovieMatcher — AI Movie Recommendation System
Root application entry point.
"""
import os
import sys

# Configure UTF-8 for Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure root directory is on Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.api import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("==================================================")
    print("  >> Starting MovieMatcher AI Recommendation App")
    print(f"  >> URL: http://127.0.0.1:{port}")
    print("==================================================")
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)