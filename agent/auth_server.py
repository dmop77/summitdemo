"""
Authentication Server for Voice Agent
====================================
Simple Flask server that provides authentication tokens for the voice agent.
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env")

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Configuration
PORT = int(os.getenv("AUTH_SERVER_PORT", "8082"))

app = Flask(__name__)
CORS(app)

# Simple in-memory token storage (in production, use a proper database)
active_tokens = {}

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "voice-agent-auth"
    })

@app.route('/token', methods=['POST'])
def generate_token():
    """Generate an authentication token for the voice agent."""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        room = data.get('room', 'default')
        
        # Generate a simple token (in production, use proper JWT or similar)
        token_data = {
            "user_id": user_id,
            "room": room,
            "issued_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
            "permissions": ["voice_agent_access"]
        }
        
        # Create a simple token (base64 encoded JSON)
        import base64
        import json
        token = base64.b64encode(json.dumps(token_data).encode()).decode()
        
        # Store the token
        active_tokens[token] = token_data
        
        logger.info(f"Generated token for user: {user_id}, room: {room}")
        
        return jsonify({
            "token": token,
            "expires_at": token_data["expires_at"],
            "websocket_url": f"ws://localhost:8081"
        })
        
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        return jsonify({"error": "Failed to generate token"}), 500

@app.route('/token/validate', methods=['POST'])
def validate_token():
    """Validate an authentication token."""
    try:
        data = request.get_json() or {}
        token = data.get('token')
        
        if not token:
            return jsonify({"valid": False, "error": "No token provided"}), 400
        
        if token not in active_tokens:
            return jsonify({"valid": False, "error": "Invalid token"}), 401
        
        token_data = active_tokens[token]
        
        # Check if token is expired
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        if datetime.now() > expires_at:
            del active_tokens[token]
            return jsonify({"valid": False, "error": "Token expired"}), 401
        
        return jsonify({
            "valid": True,
            "user_id": token_data["user_id"],
            "room": token_data["room"],
            "expires_at": token_data["expires_at"]
        })
        
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return jsonify({"valid": False, "error": "Token validation failed"}), 500

@app.route('/token/revoke', methods=['POST'])
def revoke_token():
    """Revoke an authentication token."""
    try:
        data = request.get_json() or {}
        token = data.get('token')
        
        if not token:
            return jsonify({"error": "No token provided"}), 400
        
        if token in active_tokens:
            del active_tokens[token]
            logger.info("Token revoked successfully")
            return jsonify({"message": "Token revoked successfully"})
        else:
            return jsonify({"error": "Token not found"}), 404
            
    except Exception as e:
        logger.error(f"Error revoking token: {e}")
        return jsonify({"error": "Failed to revoke token"}), 500

@app.route('/tokens', methods=['GET'])
def list_tokens():
    """List all active tokens (for debugging)."""
    try:
        # Return token info without the actual tokens for security
        token_list = []
        for token, data in active_tokens.items():
            token_list.append({
                "user_id": data["user_id"],
                "room": data["room"],
                "issued_at": data["issued_at"],
                "expires_at": data["expires_at"]
            })
        
        return jsonify({
            "active_tokens": len(active_tokens),
            "tokens": token_list
        })
        
    except Exception as e:
        logger.error(f"Error listing tokens: {e}")
        return jsonify({"error": "Failed to list tokens"}), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500

def cleanup_expired_tokens():
    """Clean up expired tokens (run periodically)."""
    current_time = datetime.now()
    expired_tokens = []
    
    for token, data in active_tokens.items():
        expires_at = datetime.fromisoformat(data["expires_at"])
        if current_time > expires_at:
            expired_tokens.append(token)
    
    for token in expired_tokens:
        del active_tokens[token]
    
    if expired_tokens:
        logger.info(f"Cleaned up {len(expired_tokens)} expired tokens")

if __name__ == '__main__':
    logger.info(f"Starting authentication server on port {PORT}")
    logger.info(f"Health check: http://localhost:{PORT}/health")
    logger.info(f"Token endpoint: http://localhost:{PORT}/token")
    
    # Start cleanup task in background
    import threading
    import time
    
    def cleanup_worker():
        while True:
            time.sleep(3600)  # Run every hour
            cleanup_expired_tokens()
    
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
