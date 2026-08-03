from src.app import create_app
from src.settings import Settings

app = create_app()

if __name__ == "__main__":
    app.run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG_MODE)
