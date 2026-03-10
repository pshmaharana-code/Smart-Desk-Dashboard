from flask import Flask, request, redirect, jsonify
from flask_cors import CORS
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# This sets up Flask to serve your HTML and image files directly
app = Flask(__name__, static_url_path='', static_folder='.')
CORS(app)

# --- YOUR SPOTIFY KEYS ---
CLIENT_ID = "85c3eb8278a64d5583dcc8d2635ead36"
CLIENT_SECRET = "27ca368de5654414aa1608e364236c72"

# Notice this uses 127.0.0.1 to perfectly match what you saved in the dashboard!
REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPE = "user-read-currently-playing"

sp_oauth = SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI, scope=SCOPE)

# 1. Serve your dashboard to the phone
@app.route('/')
def index():
    return app.send_static_file('index.html')

# 2. Login route to connect your Spotify account
@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

# 3. Spotify sends you back here after logging in
@app.route('/callback')
def callback():
    sp_oauth.get_access_token(request.args.get("code"))
    return "Spotify Connected Successfully! You can close this tab and go back to VS Code."

# 4. Our custom API to get the current song
@app.route('/now_playing')
def now_playing():
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        return jsonify({"error": "Not logged in"}), 401

    sp = spotipy.Spotify(auth=token_info['access_token'])
    current_track = sp.current_user_playing_track()

    if current_track is not None and current_track['is_playing']:
        track = current_track['item']
        return jsonify({
            "is_playing": True,
            "song": track['name'],
            "artist": track['artists'][0]['name'],
            "album_art": track['album']['images'][0]['url'],
            "progress_ms": current_track['progress_ms'], # NEW: How far into the song
            "duration_ms": track['duration_ms']          # NEW: Total song length
        })
    else:
        return jsonify({"is_playing": False})

if __name__ == '__main__':
    # host='0.0.0.0' allows your phone to connect over Wi-Fi
    app.run(host='0.0.0.0', port=8888)