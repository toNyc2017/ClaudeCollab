import os
import logging
import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app with static folder configuration
app = Flask(__name__, static_folder='../frontend/build', static_url_path='')
CORS(app)

# Serve React App at root URL
@app.route('/')
def serve():
    logger.info("Serving React frontend")
    return send_from_directory(app.static_folder, 'index.html')

# Move your existing endpoint to /api/hello
@app.route("/api/hello")
def hello_world():
    logger.info(f"Hello world endpoint called from IP: {request.remote_addr}")
    return jsonify({
        "message": "Hello World from Python Backend!",
        "environment": os.getenv('AWS_ENVIRONMENT', 'development')
    })

@app.route("/api/health")
def health():
    logger.debug("Health check endpoint called")
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

# Serve static files from the React app
@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# Keep your existing error handlers and middleware...

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting application on port {port}")
    app.run(host="0.0.0.0", port=port)
