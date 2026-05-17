import telebot
import os
import threading
import requests
from flask import Flask

# 1. חובה: שים פה טוקן *חדש* אחרי שעשית Revoke לישן ב-BotFather!
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
    bot.reply_to(message, "היי! 🎬\nשלח לי קישור (יוטיוב, טיקטוק, אינסטגרם) ואוריד אותו עבורך.\n*שימו לב: מגבלת טלגרם היא 50MB.*")

@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text
    filename = f"video_{message.message_id}.mp4"
    status_msg = None 
    
    try:
        status_msg = bot.reply_to(message, "טוען.. 🚀")
        
        # --- הגדרות ה-API של Snap Video ---
        api_url = "https://snap-video3.p.rapidapi.com/download"
        
        # שולחים את הלינק המלא כמו שהוא! (בלי Regex)
        payload = {"url": url} 
        
        headers = {
            "x-rapidapi-key": "b4a2f511b3mshca2e3aedcf3e427p1f6aadjsnedea0c48fa16",
            "x-rapidapi-host": "snap-video3.p.rapidapi.com",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # שים לב שכאן עברנו לבקשת POST כדי להתאים לשרת החדש
        response = requests.post(api_url, data=payload, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"שגיאה מול ה-API. קוד: {response.status_code}")
            
        data = response.json()
        
        stream_url = None
        
        # סריקה חכמה של ה-JSON כדי למצוא את קישור הוידאו
        if isinstance(data, dict):
            # מנסים לשלוף ממבנים נפוצים של ה-API הזה
            stream_url = data.get("url") or data.get("video_url")
            if not stream_url and "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
                stream_url = data["data"][0].get("url")
                
        # גיבוי: חיפוש עמוק אם המבנה טיפה שונה
        if not stream_url:
            for key, value in data.items():
                if isinstance(value, str) and value.startswith("http"):
                    stream_url = value
                    break
                    
        if not stream_url:
            print("API Response:", data) # נדפיס ללוגים למקרה שנרצה לחקור
            raise Exception("ה-API ענה בהצלחה אבל לא מצאתי את קישור הוידאו בתשובה.")
            
        bot.edit_message_text("העיבוד הסתיים! מוריד ומעלה לטלגרם... ⏳", chat_id=message.chat.id, message_id=status_msg.message_id)
        
        # זיוף דפדפן אגרסיבי למניעת חסימות IP בהורדה
        download_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.google.com/"
        }
        
        with requests.get(stream_url, stream=True, headers=download_headers) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            if file_size > 50 * 1024 * 1024:
                bot.edit_message_text("הסרטון שוקל יותר מ-50MB ולכן טלגרם חוסמת אותו. 😔", chat_id=message.chat.id, message_id=status_msg.message_id)
            else:
                with open(filename, 'rb') as video:
                    bot.send_video(message.chat.id, video, timeout=300)
                bot.delete_message(message.chat.id, status_msg.message_id)
        
    except Exception as e:
        error_text = f"אופס, משהו השתבש.\nפרטי השגיאה: {str(e)[:100]}"
        try:
            if status_msg:
                bot.edit_message_text(error_text, chat_id=message.chat.id, message_id=status_msg.message_id)
            else:
                bot.reply_to(message, error_text)
        except:
            pass
            
    finally:
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                pass
            
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    print("Bot is listening...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)