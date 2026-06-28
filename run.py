import os
from src.app import create_app
from settings import Settings

flask_app = create_app()

if __name__ == "__main__":
    flask_app.run(
        host=os.environ.get("HOST", Settings.HOST),
        port=int(os.environ.get("PORT", Settings.PORT)),
        debug=True,
    )
