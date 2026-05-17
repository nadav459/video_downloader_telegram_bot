import telebot
import yt_dlp
import os
import threading
from flask import Flask

# הכנס את הטוקן שקיבלת מ-BotFather כאן - זכור לשים את הטוקן החדש!
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
    bot.reply_to(message, "היי! 🎬\nשלח לי קישור לסרטון (מיוטיוב, טיקטוק, אינסטגרם וכדו') ואוריד אותו .\n*שימו לב: הבוט מוריד באיכות המותאמת למגבלת טלגרם (עד 50MB).*")

@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text
    
    try:
        # שולחים הודעה ראשונית ושומרים אותה כדי שנוכל לערוך אותה בהמשך
        status_msg = bot.reply_to(message, "מתחיל בהורדה... מכין את הסרטון ⏳")
        
        # הגדרות yt-dlp - נבקש פשוט את הגרסה המשולבת. בדיקת ה-50 מגה תתבצע אחרי ההורדה
        ydl_opts = {
            'format': 'best', 
            'outtmpl': 'video_%(id)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        # מוודאים שוב את גודל הקובץ ליתר ביטחון
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            if file_size > 50 * 1024 * 1024:
                bot.edit_message_text("הסרטון כבד מדי (מעל 50MB) גם לאחר כיווץ, ולכן טלגרם חוסמת אותו. 😔", chat_id=message.chat.id, message_id=status_msg.message_id)
            else:
                # מעדכנים את ההודעה במקום לשלוח אחת חדשה
                bot.edit_message_text("ההורדה הסתיימה, מעלה לטלגרם... 🚀", chat_id=message.chat.id, message_id=status_msg.message_id)
                
                with open(filename, 'rb') as video:
                    bot.send_video(message.chat.id, video, timeout=300)
            
            # מחיקת הקובץ מהשרת כדי לחסוך מקום
            os.remove(filename)
            
    # החלק החדש - תופס כל שגיאה ומדפיס אותה ישירות לבוט
    except Exception as e:
        error_msg = str(e)
        try:
            bot.edit_message_text(f"שגיאה בהורדה. הטקסט המדויק:\n{error_msg[:200]}", chat_id=message.chat.id, message_id=status_msg.message_id)
        except:
            pass
        
        # מוודאים מחיקה גם במקרה של שגיאה כדי שהשרת לא יתמלא
        for file in os.listdir():
            if file.startswith("video_") and file != "video_%(id)s.%(ext)s":
                try:
                    os.remove(file)
                except:
                    pass

if __name__ == '__main__':
    # הפעלת שרת האינטרנט בתהליך מקביל
    threading.Thread(target=run_flask).start()
    
    # הפעלת הבוט
    print("Bot is listening...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)