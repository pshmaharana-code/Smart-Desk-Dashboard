import os
from dotenv import load_dotenv
load_dotenv(override=True) # This forces Python to use the NEW keys, ignoring old memory
from flask import Flask, request, redirect, jsonify
from flask_cors import CORS
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# This sets up Flask to serve your HTML and image files directly
app = Flask(__name__, static_url_path='', static_folder='.')
CORS(app)

# --- YOUR SPOTIFY KEYS ---
CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')


# Notice this uses 127.0.0.1 to perfectly match what you saved in the dashboard!
REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')
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
    try:
        code = request.args.get("code")
        sp_oauth.get_access_token(code)
        return "<h1>Spotify Connected Successfully!</h1><p>You can close this tab and go back to VS Code.</p>"
    except Exception as e:
        # If it crashes, it will print the EXACT reason here instead of a blank 500 error
        return f"<h1>Spotify Login Failed</h1><h2>Exact Error:</h2><p style='color:red; font-family:monospace;'>{str(e)}</p>"

# 4. Our custom API to get the current song
@app.route('/now_playing')
def now_playing():
    token_info = sp_oauth.get_cached_token()
    
    # FIX 1: Don't send a 401 error. Send a 200 OK so the phone knows the PC is awake!
    if not token_info:
        return jsonify({"is_playing": False, "error": "needs_login"})

    try:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        current_track = sp.current_user_playing_track()

        if current_track is not None and current_track.get('is_playing'):
            track = current_track['item']
            return jsonify({
                "is_playing": True,
                "song": track['name'],
                "artist": track['artists'][0]['name'],
                "album_art": track['album']['images'][0]['url'],
                "progress_ms": current_track['progress_ms'], 
                "duration_ms": track['duration_ms']          
            })
        else:
            return jsonify({"is_playing": False})
            
    except Exception as e:
        # FIX 2: If the Spotify API crashes, don't crash the server. Just show "No music".
        return jsonify({"is_playing": False, "error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888, debug=True)