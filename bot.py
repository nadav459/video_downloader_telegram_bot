import telebot
import yt_dlp
import os
import threading
from flask import Flask

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
    bot.reply_to(message, "היי שירן! 🎬\nשלחי לי קישור לסרטון (מיוטיוב, טיקטוק, אינסטגרם וכדו') ואוריד אותו עבורך.\n*שימי לב: יש מגבלה של 50MB.*")
@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text
    
    try:
        # נסיון לשלוח הודעת פתיחה. אם החיבור נפל - נתעלם ונמשיך ישר להורדה
        try:
            bot.reply_to(message, "מתחיל בהורדה... זה עשוי לקחת כמה שניות ⏳")
        except Exception as e:
            print("Skipped initial message due to connection error.")
        
        # הגדרות yt-dlp - ניסיון להוריד קובץ שקטן מ-50 מגה
        ydl_opts = {
            'format': 'best[filesize<50M]/best', 
            'outtmpl': 'video_%(id)s.%(ext)s',
            'noplaylist': True,
            'quiet': True
        }
        
        # הורדת הסרטון
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        # בדיקה האם הקובץ שהורד גדול מ-50MB
        if os.path.getsize(filename) > 50 * 1024 * 1024:
            bot.reply_to(message, "הסרטון שוקל יותר מ-50MB ולכן טלגרם חוסמת את השליחה שלו. 😔")
        else:
            try:
                bot.reply_to(message, "ההורדה הסתיימה, מעלה לטלגרם... 🚀")
            except:
                pass # מתעלם אם הודעת הטקסט נכשלת
            
            # העלאת הסרטון עם טיימאאוט ארוך (התיקון שעשינו קודם)
            with open(filename, 'rb') as video:
                bot.send_video(message.chat.id, video, timeout=300)
        
        # מחיקת הקובץ מהשרת כדי לחסוך מקום
        os.remove(filename)
        
    except Exception as e:
        try:
            bot.reply_to(message, f"אופס, משהו השתבש בהורדה. ייתכן שהקישור לא חוקי או שהסרטון חסום.\nשגיאה: {str(e)[:50]}")
        except:
            pass

if __name__ == '__main__':
    # הפעלת שרת האינטרנט בתהליך מקביל
    threading.Thread(target=run_flask).start()
    
    # הפעלת הבוט
    print("Bot is listening...")
    bot.infinity_polling()