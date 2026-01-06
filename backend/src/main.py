from api.app import create_app
from config import Config
import sys

app = create_app()

def main():
    """Запуск для разработки (локально)"""
    try:
        app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    main()
