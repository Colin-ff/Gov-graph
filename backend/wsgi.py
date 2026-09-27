"""Entry point for `flask run` and WSGI servers.

Loads .env (from the repo root) then builds the app via the factory.
"""

import os

from dotenv import load_dotenv

# Load the repo-root .env so backend and docker-compose share one config file.
load_dotenv(os.path.join(os.path.dirname(__file__), os.pardir, ".env"))

from app import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
