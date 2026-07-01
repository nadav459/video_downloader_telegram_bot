import telebot
import yt_dlp
import os
import threading
import cloudscraper
import requests
import re
from flask import Flask

TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

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

# פונקציית גיבוי שמשתמשת בסקרייפר שעוקף זיהוי בוטים
def scrape_instagram_fallback(url):
    try:
        # שימוש ב-Cobalt API (פרויקט קוד פתוח חינמי לעקיפת חסימות מדיה)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        data = {
            "url": url
        }
        
        # בקשה לשרת של קובלט
        response = requests.post("https://api.cobalt.tools/api/json", json=data, headers=headers, timeout=20)
        result = response.json()
        
        # חילוץ הלינק הישיר לסרטון מהתשובה
        video_url = result.get("url")
        
        if video_url:
            # הורדת הקובץ הישיר
            video_data = requests.get(video_url, timeout=20).content
            filename = f"fallback_video_{os.urandom(4).hex()}.mp4"
            with open(filename, 'wb') as f:
                f.write(video_data)
            return filename
        else:
            print(f"Cobalt API returned unexpected response: {result}")
            
    except Exception as e:
        print(f"Scraper fallback failed: {e}")
    return None

@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text
    is_instagram = 'instagram.com' in url
    filename = None
    
    try:
        try:
            bot.reply_to(message, "מתחיל בהורדה... זה עשוי לקחת כמה שניות ⏳")
        except Exception:
            pass
        
        ydl_opts = {
            'format': 'best[vcodec^=avc1][filesize<50M]/best[filesize<50M]/best', 
            'outtmpl': 'video_%(id)s.%(ext)s',
            'noplaylist': True,
            'quiet': True
        }
        
        # שיטה 1: הזרקת פרוקסי רק עבור אינסטגרם
        if is_instagram:
            proxy = os.environ.get('PROXY_URL')
            if proxy:
                ydl_opts['proxy'] = proxy
        
        # ניסיון ראשון: yt-dlp
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
        except Exception as e:
            # במקרה ש-yt-dlp נכשל (נחסם) והקישור הוא של אינסטגרם - עוברים לגיבוי
            if is_instagram:
                bot.send_message(message.chat.id, "yt-dlp נחסם, מנסה שיטת גיבוי... 🔄")
                filename = scrape_instagram_fallback(url)
                if not filename:
                    raise Exception("גם שיטת הגיבוי נכשלה מול אינסטגרם.")
            else:
                raise e # זורק את השגיאה הלאה אם זה לא אינסטגרם

        if not filename or not os.path.exists(filename):
            raise Exception("הקובץ לא נוצר.")

        # בדיקת גודל והעלאה (נשאר זהה לקוד שלך)
        if os.path.getsize(filename) > 50 * 1024 * 1024:
            bot.reply_to(message, "הסרטון שוקל יותר מ-50MB ולכן טלגרם חוסמת את השליחה שלו. 😔")
        else:
            try:
                bot.reply_to(message, "ההורדה הסתיימה, מעלה לטלגרם... 🚀")
            except:
                pass 
            
            with open(filename, 'rb') as video:
                bot.send_video(message.chat.id, video, timeout=300)
        
        os.remove(filename)
        
    except Exception as e:
        try:
            bot.reply_to(message, f"אופס, משהו השתבש בהורדה. ייתכן שהקישור לא חוקי או שהסרטון חסום.\nשגיאה: {str(e)[:50]}")
        except:
            pass
        # ניקוי קובץ במקרה של קריסה באמצע
        if filename and os.path.exists(filename):
            os.remove(filename)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    print("Bot is listening...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)