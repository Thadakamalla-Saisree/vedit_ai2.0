from flask import Flask, render_template, redirect, url_for, request, send_file, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, History
from video_tools import trim_video, split_video, add_captions, mute_audio, add_background_music
from config import Config
from werkzeug.utils import secure_filename
from gtts import gTTS
import os
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config.from_object(Config)
db.init_app(app)
with app.app_context():
    db.create_all()
login_manager = LoginManager(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_user_preview_path(filename):
    user_dir = f"static/previews/user_{current_user.id}"
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, filename)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = User(username=request.form['username'], password=request.form['password'])
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.password == request.form['password']:
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    response = session.pop('response', None)
    history = History.query.filter_by(user_id=current_user.id).all()

    video_path = None
    if request.method == "POST" and "video" in request.files:
        video = request.files["video"]
        upload_path = os.path.join("static", "uploads", secure_filename(video.filename))
        video.save(upload_path)
        video_path = "/" + upload_path.replace("\\", "/")
        session['video_path'] = video_path
    else:
        video_path = session.get('video_path')

    user_dir = f"static/previews/user_{current_user.id}"
    trimmed_exists = os.path.exists(os.path.join(user_dir, "trimmed.mp4"))
    voice_exists = os.path.exists(os.path.join(user_dir, "voice.mp3"))
    captioned_exists = os.path.exists(os.path.join(user_dir, "captioned.mp4"))
    split_exists = os.path.exists(os.path.join(user_dir, "split_part1.mp4")) and os.path.exists(os.path.join(user_dir, "split_part2.mp4"))
    muted_exists = os.path.exists(os.path.join(user_dir, "muted.mp4"))
    music_exists = os.path.exists(os.path.join(user_dir, "music_added.mp4"))

    return render_template("dashboard.html",
        video_path=video_path,
        trimmed_exists=trimmed_exists,
        voice_exists=voice_exists,
        captioned_exists=captioned_exists,
        split_exists=split_exists,
        muted_exists=muted_exists,
        music_exists=music_exists,
        response=response,
        history=history,
        current_user=current_user
    )

@app.route('/trim', methods=['POST'])
@login_required
def trim():
    url_path = request.form['path']
    filename = os.path.basename(url_path)
    real_path = os.path.join("static", "uploads", secure_filename(filename))

    start = int(request.form['start'])
    end = int(request.form['end'])

    output_path = get_user_preview_path("trimmed.mp4")
    trim_video(real_path, start, end, output_path)

    return redirect(url_for('dashboard'))

@app.route('/voice', methods=['POST'])
@login_required
def voice():
    text = request.form['text']
    output_path = get_user_preview_path("voice.mp3")
    tts = gTTS(text=text, lang='en')
    tts.save(output_path)
    return redirect(url_for('dashboard'))

@app.route('/music', methods=['POST'])
@login_required
def music():
    try:
        music_file = request.files['music']
        os.makedirs("static/audio", exist_ok=True)
        music_path = "static/audio/background.mp3"  # ✅ Save here consistently
        music_file.save(music_path)

        video_path = request.form['video_path'].lstrip('/')
        output_path = get_user_preview_path("music_added.mp4")
        add_background_music(video_path, music_path, output_path)

        
        session['response'] = "Background music added successfully!"
    except Exception as e:
        session['response'] = f"Music upload failed: {str(e)}"

    return redirect(url_for('dashboard'))
@app.route("/chat", methods=["POST"])
@login_required
def chat():
    prompt = request.form["prompt"]
    video_path = request.form.get("video_path", "static/uploads/videoplayback.mp4").lstrip('/')
    if not os.path.exists(video_path):
        response = "No video found to edit. Please upload one first."
        return redirect(url_for('dashboard'))

    response = ""
    user_dir = f"static/previews/user_{current_user.id}"
    os.makedirs(user_dir, exist_ok=True)

    trimmed_exists = voice_exists = captioned_exists = split_exists = muted_exists = music_exists = False

    if match := re.search(r"trim.*?(\d+).*?(\d+)", prompt.lower()):
        start, end = int(match.group(1)), int(match.group(2))
        output_path = os.path.join(user_dir, "trimmed.mp4")
        trim_video(video_path, start, end, output_path)
        trimmed_exists = True
        response = f"Trimmed video from {start} to {end} seconds."

    elif "split" in prompt.lower():
        if match := re.search(r"split.*?(\d+)", prompt.lower()):
            time = int(match.group(1))
            split_video(video_path, time, user_dir)
            split_exists = True
            response = f"Video split at {time} seconds."

    elif "caption" in prompt.lower() or "subtitle" in prompt.lower():
        if match := re.search(r"(caption|subtitle).*?:\s*(.+)", prompt.lower()):
            text = match.group(2)
            output_path = os.path.join(user_dir, "captioned.mp4")
            add_captions(video_path, text, output_path)
            captioned_exists = True
            response = f"Caption added: {text}"

    elif "add music to muted" in prompt.lower():
        video_path = os.path.join(user_dir, "muted.mp4")
        music_path = "static/audio/background.mp3"
        output_path = os.path.join(user_dir, "music_added.mp4")
        if os.path.exists(music_path):
            add_background_music(video_path, music_path, output_path)
            music_exists = True
            response = "Background music added to muted video."
        else:
            response = "No music file found. Please upload one or choose from the gallery."
    elif "mute" in prompt.lower():
        output_path = os.path.join(user_dir, "muted.mp4")
        mute_audio(video_path, output_path)
        muted_exists = True
        response = "Muted the video."

    

    elif "music" in prompt.lower():
        music_path = "static/audio/background.mp3"
        output_path = os.path.join(user_dir, "music_added.mp4")
        if os.path.exists(music_path):
            add_background_music(video_path, music_path, output_path)
            music_exists = True
            response = "Background music added."
        else:
            response = "No background music file found. Please upload one using the 'Add Music' button below."

    else:
        response = "Sorry, I didn't understand that command. Try 'Trim from 5 to 10 seconds' or 'Add captions: Hello world'."

    # Save command to history
    new_entry = History(
        user_id=current_user.id,
        command=prompt,
        response=response
    )
    db.session.add(new_entry)
    db.session.commit()

    history = History.query.filter_by(user_id=current_user.id).all()

    return render_template("dashboard.html",
        video_path=session.get('video_path'),
        trimmed_exists=trimmed_exists,
        voice_exists=voice_exists,
        captioned_exists=captioned_exists,
        split_exists=split_exists,
        muted_exists=muted_exists,
        music_exists=music_exists,
        response=response,
        history=history,
        current_user=current_user
    )
@app.route("/clear_edits", methods=["POST"])
@login_required
def clear_edits():
    user_dir = f"static/previews/user_{current_user.id}"
    if os.path.exists(user_dir):
        for filename in os.listdir(user_dir):
            file_path = os.path.join(user_dir, filename)
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")
    session['response'] = "✅ Your edits have been cleared."
    return redirect(url_for("dashboard"))
@app.route("/clear_history", methods=["POST"])
@login_required
def clear_history():
    History.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    session['response'] = "🧹 Command history cleared."
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)