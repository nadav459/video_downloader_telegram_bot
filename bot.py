import telebot
import os
import threading
import requests
import re
from flask import Flask

# הטוקן של הבוט שלך מ-BotFather
TOKEN = '8361927641:AAHfz5_1Sb2SFM5mWl6-t2VfKFL4v-zaACo'
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
    bot.reply_to(message, "היי! 🎬\nשלחו לי קישור לסרטון ואוריד אותו עבורכם.\n*שימו לב: מגבלת טלגרם היא 50MB.*")

@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text
    filename = f"video_{message.message_id}.mp4"
    
    try:
        # שליפת ה-ID של הוידאו מתוך הקישור (מתמודד עם Shorts, URL רגיל ו-youtu.be)
        match = re.search(r"(?:v=|\/shorts\/|youtu\.be\/)([0-9A-Za-z_-]{11})", url)
        if not match:
            raise Exception("לא זיהיתי קישור תקין של יוטיוב.")
        video_id = match.group(1)

        status_msg = bot.reply_to(message, "שואב את הסרטון דרך ה-API הפרטי... 🚀")
        
        # --- הגדרות ה-API של RapidAPI (מהמסך שלך) ---
        api_url = "https://youtube-media-downloader.p.rapidapi.com/v2/video/details"
        
        headers = {
            "x-rapidapi-key": "b4a2f511b3mshca2e3aedcf3e427p1f6aadjnsnedea0c48fa16",
            "x-rapidapi-host": "youtube-media-downloader.p.rapidapi.com"
        }
        
        querystring = {"videoId": video_id, "videos": "auto"}
        
        response = requests.get(api_url, headers=headers, params=querystring)
        
        if response.status_code != 200:
            raise Exception("שגיאה בתקשורת מול ה-API המרכזי.")
            
        data = response.json()
        
        # פיענוח ה-JSON של ה-API הספציפי הזה כדי למצוא את קישור ה-mp4
        stream_url = None
        try:
            items = data.get("videos", {}).get("items", [])
            for item in items:
                # מחפשים גרסה שכוללת גם אודיו וגם וידאו
                if item.get("hasAudio") and item.get("extension") == "mp4":
                    stream_url = item.get("url")
                    break
            # אם לא מצאנו פורמט משולב, פשוט ניקח את הלינק הראשון
            if not stream_url and items:
                stream_url = items[0].get("url")
        except:
            pass
            
        if not stream_url:
            print("API Data:", data) # שומר ב-Logs את התשובה כדי שנוכל לחקור אם משהו השתנה
            raise Exception("לא מצאתי קישור ישיר להורדה בתוך התשובה של יוטיוב.")
            
        bot.edit_message_text("העיבוד הסתיים! מוריד ומעלה לטלגרם... ⏳", chat_id=message.chat.id, message_id=status_msg.message_id)
        
        # מוריד לשרת של Render
        with requests.get(stream_url, stream=True) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        # מגבלת 50 מגה
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            if file_size > 50 * 1024 * 1024:
                bot.edit_message_text("הסרטון שוקל יותר מ-50MB ולכן טלגרם חוסמת את השליחה שלו. 😔", chat_id=message.chat.id, message_id=status_msg.message_id)
            else:
                with open(filename, 'rb') as video:
                    bot.send_video(message.chat.id, video, timeout=300)
                bot.delete_message(message.chat.id, status_msg.message_id)
        
    except Exception as e:
        try:
            bot.edit_message_text(f"אופס, משהו השתבש.\nפרטי השגיאה: {str(e)[:100]}", chat_id=message.chat.id, message_id=status_msg.message_id)
        except:
            pass
            
    finally:
        # ניקיון השרת תמיד!
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                pass

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    print("Bot is listening...")
    bot.infinity_polling(timeout)