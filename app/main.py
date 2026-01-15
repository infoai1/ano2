"""Entry point for Annotation Tool v2."""
from app import create_app
from app.config import get_logger

app = create_app()
logger = get_logger()

if __name__ == '__main__':
    logger.info("starting_dev_server", host='0.0.0.0', port=5000)
    app.run(host='0.0.0.0', port=5000, debug=True)
