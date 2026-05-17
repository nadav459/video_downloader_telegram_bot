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
        # רשימת שרתי קהילה של Cobalt (גיבויים למקרה של עומס)
        cobalt_instances = [
            "https://api.cobalt.tools/api/json",
            "https://api.cobalt.squables.app/api/json",
            "https://cobalt-api.kwiatekm.dev/api/json",
            "https://imput.net/api/json"
        ]
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            # מוסיפים User-Agent כללי כדי שחלק מהשרתים לא יחסמו אותנו
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        payload = {
            "url": url,
            "videoQuality": "720", 
            "filenamePattern": "basic"
        }
        
        stream_url = None
        
        # הבוט רץ על השרתים אחד אחרי השני. אם אחד נכשל, עוברים להבא
        for api_url in cobalt_instances:
            try:
                response = requests.post(api_url, json=payload, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") != "error":
                        stream_url = data.get("url")
                        if stream_url:
                            break # מצאנו שרת שעובד! עוצרים את החיפוש
            except Exception as e:
                continue # השרת הזה לא ענה או קרס, עוברים לשרת הבא ברשימה
                
        # אם עברנו על כל הרשימה ואף שרת לא עבד
        if not stream_url:
            raise Exception("כל שרתי הגיבוי עמוסים כרגע. נסה שוב בעוד דקה.")
            
        bot.edit_message_text("העיבוד הסתיים! מוריד ומעלה לטלגרם... ⏳", chat_id=message.chat.id, message_id=status_msg.message_id)
        
        # הורדת הקובץ לשרת של Render 
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