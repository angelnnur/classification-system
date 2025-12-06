from api.app import create_app
from config import Config
import sys

def main():
    app = create_app()

    try:
        app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    main()
