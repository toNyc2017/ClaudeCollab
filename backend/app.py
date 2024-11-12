import os
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/")
def hello_world():
    return jsonify({
        "message": "Hello World from Python Backend!",
        "environment": os.getenv('RAILWAY_ENVIRONMENT', 'development')
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
