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

# Serve React App - set up route for the root URL
@app.route('/')
def serve():
    return send_from_directory(app.static_folder, 'index.html')

# API Routes - prefix them with /api
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

# Catch all route to return to React Router
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

# Rest of your error handlers and middleware remain the same...
