import telebot
import yt_dlp
import os
import threading
from flask import Flask

# --- קסם: הוספת FFmpeg לשרת כדי שנוכל למזג שורטים ---
import static_ffmpeg
static_ffmpeg.add_paths()

# הכנס את הטוקן שקיבלת מ-BotFather כאן
TOKEN = '8361927641:AAHfz5_1Sb2SFM5mWl6-t2VfKFL4v-zaACo'
bot = telebot.TeleBot(TOKEN)

# --- הגדרת שרת Flask כדי שפלטפורמות כמו Render לא יסגרו את הבוט ---
app = Flask(__name__)
@app.route('/')
def index():
    return "The bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "היי! 🎬\nשלח לי קישור לסרטון ואוריד אותו עבורך.\n*שימו לב: הבוט מוריד באיכות המותאמת למגבלת טלגרם (עד 50MB).*")

@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text
    
    try:
        status_msg = bot.reply_to(message, "מתחיל בהורדה... מכין את הסרטון ⏳")
        
        # הגדרות yt-dlp - עכשיו הוא יודע למזג וידאו ואודיו!
        # הגדרות yt-dlp - מוריד את הטוב ביותר ללא תלות בפורמט המקור, וממיר ל-MP4
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4', 
            'outtmpl': 'video_%(id)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'cookiefile': 'cookies.txt',
            'extractor_args': {'youtube': ['player_client=android,web']}
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # בגלל המיזוג, לפעמים הסיומת משתנה ל-mp4. נוודא שאנחנו מחפשים את הקובץ הנכון
            if not os.path.exists(filename):
                filename = filename.rsplit('.', 1)[0] + '.mp4'
        
        # בדיקת גודל הקובץ לפני השליחה (מגבלת 50MB של טלגרם)
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            if file_size > 50 * 1024 * 1024:
                bot.edit_message_text("הסרטון כבד מדי (מעל 50MB) גם לאחר כיווץ, ולכן טלגרם חוסמת אותו. 😔", chat_id=message.chat.id, message_id=status_msg.message_id)
            else:
                bot.edit_message_text("ההורדה הסתיימה, מעלה לטלגרם... 🚀", chat_id=message.chat.id, message_id=status_msg.message_id)
                
                with open(filename, 'rb') as video:
                    bot.send_video(message.chat.id, video, timeout=300)
            
            # מחיקת הקובץ
            os.remove(filename)
            
    except Exception as e:
        error_msg = str(e)
        try:
            bot.edit_message_text(f"שגיאה בהורדה. הטקסט המדויק:\n{error_msg[:200]}", chat_id=message.chat.id, message_id=status_msg.message_id)
        except:
            pass
        
        # ניקיון שאריות
        for file in os.listdir():
            if file.startswith("video_") and file != "video_%(id)s.%(ext)s":
                try:
                    os.remove(file)
                except:
                    pass

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    print("Bot is listening...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)