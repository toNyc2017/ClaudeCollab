import os
import logging
import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Global error handler
@app.errorhandler(Exception)
def handle_error(error):
    logger.error(f"Error occurred: {error}", exc_info=True)
    status_code = getattr(error, 'code', 500)
    return jsonify({
        "error": str(error),
        "status_code": status_code
    }), status_code

# Routes
@app.route("/")
def hello_world():
    logger.info(f"Hello world endpoint called from IP: {request.remote_addr}")
    return jsonify({
        "message": "Hello World from Python Backend!",
        "environment": os.getenv('AWS_ENVIRONMENT', 'development')
    })

@app.route("/health")
def health():
    logger.debug("Health check endpoint called")
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 error for path: {request.path}")
    return jsonify({
        "error": "Resource not found",
        "path": request.path
    }), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"500 error occurred", exc_info=True)
    return jsonify({
        "error": "Internal server error",
        "message": str(error)
    }), 500

# Middleware to log all requests
@app.before_request
def log_request():
    logger.info(f"Request received: {request.method} {request.path} from {request.remote_addr}")

@app.after_request
def log_response(response):
    logger.info(f"Response status: {response.status_code}")
    return response

if __name__ == "__main__":
    # This will only be used when running directly, not through gunicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting application on port {port}")
    app.run(host="0.0.0.0", port=port)
