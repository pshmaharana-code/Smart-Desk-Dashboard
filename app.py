import json
import os
from dotenv import load_dotenv
load_dotenv(override=True) # This forces Python to use the NEW keys, ignoring old memory

from flask_socketio import SocketIO, emit
from flask import Flask, request, redirect, jsonify
from flask_cors import CORS
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# --- VAULT CHECK ---
print("Checking Vault...")
print("ID Loaded:", os.getenv('SPOTIPY_CLIENT_ID') != None)
print("Secret Loaded:", os.getenv('SPOTIPY_CLIENT_SECRET') != None)
print("-------------------")

# This sets up Flask to serve your HTML and image files directly
app = Flask(__name__, static_url_path='', static_folder='.')
app.config['SECRET_KEY'] = 'super_secret_dashboard_key'  # Required for WebSockets
CORS(app)

# Initialize the Walkie-Talkie base station
socketio =  SocketIO(app, cors_allowed_origins="*")

# --- YOUR SPOTIFY KEYS ---
CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')
SCOPE = "user-read-currently-playing"

sp_oauth = SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI, scope=SCOPE)


# --- WEBSOCKET LISTENERS ---
# NEW: This fires the exact millisecond a device connects to the server
@socketio.on('connect')
def handle_connect():
    print("🟢 DEVICE CONNECTED TO WEBSOCKET!", flush=True)
    # Send a welcome message back to the device
    emit('server_update', {'message': 'Connection established. Waiting for orders.'})


# 1. Serve your dashboard to the phone
@app.route('/')
def index():
    return app.send_static_file('index.html')

# The Mobile Command center.
@app.route('/remote')
def remote():
    return app.send_static_file('remote.html')


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


# 5. THE COMMAND CENTER
@app.route('/api/change_screen', methods=['POST'])
def change_screen():
    # 1. catch the data sent by your desktop app
    data = request.json

    # 2. Extract the variable
    target_app = data.get('app_name')
    target_slot = data.get('slot')

    # 3. shout the command down the walkie-talkie to the phone!
    
    socketio.emit('force_layout_change', {'app': target_app, 'slot': target_slot})

    print(f"📡 COMMAND SENT: Move [{target_app}] to Slot [{target_slot}]")
    return jsonify({"status": "success"})


# 6. UPLOAD NEW PET GIF
@app.route('/api/upload_gif', methods=['POST'])
def upload_gif():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file provided"})
    
    file = request.files['file']
    # Instantly overwrite the old pet.gif with the new one!
    file.save('pet.gif') 
    
    # Tell the Walkie-Talkie to shout to the J2: "Refresh the Pet!"
    socketio.emit('refresh_pet')
    print("📥 NEW PET GIF UPLOADED!")
    
    return jsonify({"status": "success"})


# 7. ADD NEW MOTIVATIONAL QUOTE
@app.route('/api/add_quote', methods=['POST'])
def add_quote():
    data = request.json
    new_quote = data.get('quote')
    
    # 1. Open the quotes file and read it
    with open('quotes.json', 'r') as f:
        quotes = json.load(f)
        
    # 2. Add the new quote to the list
    quotes.append(new_quote)
    
    # 3. Save it back to the file
    with open('quotes.json', 'w') as f:
        json.dump(quotes, f, indent=4)
        
    # Tell the Walkie-Talkie to shout to the J2: "Refresh the Quotes!"
    socketio.emit('refresh_quotes')
    print(f"✍️ NEW QUOTE ADDED: {new_quote}")
    
    return jsonify({"status": "success"})

# --- SECURE TOKEN HANDOFF ---
@app.route('/api/get_keys')
def get_keys():
    # Hands the token to the frontend locally without exposing it in the HTML code!
    return jsonify({"pb_token": os.getenv('PUSHBULLET_TOKEN')})

@app.route('/api/reboot_screen', methods=['POST'])
def reboot_screen():
    socketio.emit('force_reload')
    print("⚠️ REMOTE COMMAND: Forcing J2 Screen Refresh!")
    return jsonify({"status": "success"})


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
    # NEW: Upgraded server starter using SocketIO instead of standard Flask
    print("🚀 Starting WebSockets Server...")
    socketio.run(app, host='0.0.0.0', port=8888, debug=True)