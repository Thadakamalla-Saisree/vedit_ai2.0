from moviepy.editor import VideoFileClip

print("Using:", VideoFileClip)
clip = VideoFileClip(r"C:\Users\Saisree\vedit_ai\static\uploads\videoplayback.mp4")
print("Methods:", dir(clip))