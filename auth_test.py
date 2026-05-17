import yt_dlp

ydl_opts = {
    'extractor_args': {'youtube': {'player_client': ['tv_embedded']}},
    'quiet': False,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ", download=False)
    print("✅ עובד! כותרת:", info.get('title'))