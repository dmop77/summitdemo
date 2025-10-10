"""
Simple Token Server for LiveKit
================================
Generates access tokens for the frontend to connect to LiveKit.
Run this if you don't want to manually generate tokens.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from livekit import api
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for browser requests

# LiveKit credentials (optional - only if you want token server)
LIVEKIT_API_KEY = os.getenv('LIVEKIT_API_KEY', 'devkey')
LIVEKIT_API_SECRET = os.getenv('LIVEKIT_API_SECRET', 'secret')


@app.route('/token', methods=['POST'])
def create_token():
    """Generate a LiveKit access token."""
    try:
        data = request.json
        room = data.get('room', 'task-agent')
        identity = data.get('identity', f'user-{os.urandom(4).hex()}')
        name = data.get('name', identity)
        
        # Create access token
        token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        token.with_identity(identity).with_name(name)
        token.with_grants(
            api.VideoGrants(
                room_join=True,
                room=room,
                can_publish=True,
                can_subscribe=True,
            )
        )
        
        return jsonify({
            'token': token.to_jwt(),
            'url': 'ws://localhost:7880'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    print("🎫 Token Server running on http://localhost:8080")
    print("💡 Use this to generate tokens for the frontend")
    print("📝 Frontend will call: POST http://localhost:8080/token")
    print()
    app.run(host='0.0.0.0', port=8080, debug=True)