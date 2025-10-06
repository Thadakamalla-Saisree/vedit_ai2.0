import re
from video_tools import trim_video, split_video, add_captions, mute_audio, add_background_music
from transformers import pipeline

chatbot = pipeline("text-generation", model="gpt2")

def get_response(prompt, video_path):
    prompt = prompt.lower()

    trim_match = re.search(r'trim.*?(\d+).*?(\d+)', prompt)
    if trim_match:
        start = int(trim_match.group(1))
        end = int(trim_match.group(2))
        output = trim_video(video_path, start, end)
        return f"Trimmed video from {start}s to {end}s. Download: {output}"

    split_match = re.search(r'split.*?(\d+)', prompt)
    if split_match:
        time = int(split_match.group(1))
        outputs = split_video(video_path, time)
        return f"Video split at {time}s. Parts: {outputs}"

    caption_match = re.search(r'add caption[s]?: (.+)', prompt)
    if caption_match:
        text = caption_match.group(1)
        output = add_captions(video_path, text)
        return f"Caption added. Download: {output}"

    mute_match = re.search(r'mute audio', prompt)
    if mute_match:
        output = mute_audio(video_path)
        return f"Audio muted. Download: {output}"

    music_match = re.search(r'add music: (.+)', prompt)
    if music_match:
        music_path = f"static/music/{music_match.group(1)}.mp3"
        output = add_background_music(video_path, music_path)
        return f"Music added. Download: {output}"

    response = chatbot(prompt, max_length=50, do_sample=True)[0]['generated_text']
    return response