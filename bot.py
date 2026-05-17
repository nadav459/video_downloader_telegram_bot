import telebot
import os
import threading
import requests
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
    bot.reply_to(message, "היי! 🎬\nשלח לי קישור לסרטון (מיוטיוב, טיקטוק, אינסטגרם וכדו') ואוריד אותו עבורך בשניות.\n*שימו לב: יש מגבלה של 50MB.*")

@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text
    filename = f"video_{message.message_id}.mp4"
    
    try:
        status_msg = bot.reply_to(message, "מעבד את הסרטון בצינור המהיר... 🚀")
        
        # פנייה ל-API הציבורי של Cobalt
        cobalt_url = "https://api.cobalt.tools/api/json"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "url": url,
            "videoQuality": "720", # איכות מצוינת ששומרת על משקל נמוך מ-50MB לרוב
            "filenamePattern": "basic"
        }
        
        response = requests.post(cobalt_url, json=payload, headers=headers)
        
        if response.status_code != 200:
            raise Exception("שרת ההורדות עמוס, נסה שוב בעוד רגע.")
            
        data = response.json()
        
        # בדיקה אם השרת החזיר שגיאה
        if data.get("status") == "error":
            raise Exception(data.get("text", "שגיאה בעיבוד הסרטון."))
            
        stream_url = data.get("url")
        if not stream_url:
            raise Exception("לא נמצא קישור ישיר לקובץ.")
            
        bot.edit_message_text("העיבוד הסתיים! מוריד ומעלה לטלגרם... ⏳", chat_id=message.chat.id, message_id=status_msg.message_id)
        
        # הורדת הקובץ לשרת של Render כדי לבדוק גודל
        with requests.get(stream_url, stream=True) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        # בדיקת מגבלת ה-50MB של טלגרם
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            if file_size > 50 * 1024 * 1024:
                bot.edit_message_text("הסרטון שוקל יותר מ-50MB ולכן טלגרם חוסמת את השליחה שלו. 😔", chat_id=message.chat.id, message_id=status_msg.message_id)
            else:
                with open(filename, 'rb') as video:
                    bot.send_video(message.chat.id, video, timeout=300)
                # מוחקים את הודעת הסטטוס כדי להשאיר צ'אט נקי
                bot.delete_message(message.chat.id, status_msg.message_id)
        
    except Exception as e:
        try:
            bot.edit_message_text(f"אופס, משהו השתבש.\nפרטי השגיאה: {str(e)[:100]}", chat_id=message.chat.id, message_id=status_msg.message_id)
        except:
            pass
            
    finally:
        # בלוק שמבטיח מחיקה של הקובץ מהשרת בכל מצב (הצלחה או כישלון)
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                pass

if __name__ == '__main__':
    # הפעלת שרת האינטרנט בתהליך מקביל
    threading.Thread(target=run_flask).start()
    
    # הפעלת הבוט
    print("Bot is listening...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)