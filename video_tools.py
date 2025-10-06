import os
from moviepy.editor import (
    VideoFileClip,
    concatenate_videoclips,
    TextClip,
    CompositeVideoClip,
    AudioFileClip
)
from moviepy.config import change_settings

# Optional: If you're on Windows and using ImageMagick for captions
change_settings({"IMAGEMAGICK_BINARY": "C:\\Program Files\\ImageMagick-7.1.2-Q16-HDRI\\magick.exe"})

def trim_video(path, start, end, output_path):
    clip = VideoFileClip(path).subclip(start, end)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    clip.close()
    return output_path

def split_video(path, time, output_dir):
    clip = VideoFileClip(path)
    part1 = clip.subclip(0, time)
    part2 = clip.subclip(time, clip.duration)
    os.makedirs(output_dir, exist_ok=True)
    out1 = os.path.join(output_dir, "split_part1.mp4")
    out2 = os.path.join(output_dir, "split_part2.mp4")
    part1.write_videofile(out1, codec="libx264", audio_codec="aac")
    part2.write_videofile(out2, codec="libx264", audio_codec="aac")
    clip.close()
    part1.close()
    part2.close()
    return [out1, out2]

def add_captions(path, text, output_path):
    import unicodedata
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    clip = VideoFileClip(path)
    txt = TextClip(text, fontsize=40, color='white', font='Arial') \
            .set_duration(clip.duration) \
            .set_position('bottom')
    final = CompositeVideoClip([clip, txt])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if os.path.exists(output_path):
        os.remove(output_path)
    final.write_videofile(output_path, codec="libx264", audio_codec="aac")
    clip.close()
    txt.close()
    final.close()
    return output_path

def mute_audio(path, output_path):
    from moviepy.editor import VideoFileClip

    clip = VideoFileClip(path)

    # ✅ Remove audio safely
    clip = clip.without_audio()

    # ✅ Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # ✅ Write with proper codec and metadata
    clip.write_videofile(
        output_path,
        codec="libx264",
        audio=False,  # Explicitly disable audio track
        preset="medium",
        threads=4,
        remove_temp=True
    )

    clip.close()

def add_background_music(video_path, music_path, output_path):
    from moviepy.editor import VideoFileClip, AudioFileClip
    from moviepy.audio.fx.all import audio_loop, volumex

    video = VideoFileClip(video_path)
    audio = AudioFileClip(music_path)

    # 🔁 Loop or trim music to match video
    if audio.duration < video.duration:
        audio = audio_loop(audio, duration=video.duration)
    else:
        audio = audio.subclip(0, video.duration)

    # 🔊 Boost volume if needed
    audio = volumex(audio, 2.0)

    # ✅ Set audio and write output
    final = video.set_audio(audio)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final.write_videofile(output_path, codec="libx264", audio_codec="aac")

    video.close()
    audio.close()
    final.close()