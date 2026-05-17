import telebot
import os
import threading
import yt_dlp
from flask import Flask

# הטוקן שהדבקת לי (אגב, ממליץ לעשות לו Revoke מתישהו כשיהיה לך כוח כי הוא נחשף פה)
TOKEN = '8361927641:AAE108imYXrhoqSfpiKQqhltyFhWRnLZX8w'
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
        status_msg = bot.reply_to(message, "מוריד את הסרטון... 🚀")
        
        # --- התיקון שמונע מסך שחור באייפון/מק (מכריח קידוד H.264) ---
        # --- התיקון שמונע מסך שחור באייפון + שימוש בעוגיות לאינסטגרם ---
        ydl_opts = {
            'format': '22/best[ext=mp4][vcodec^=avc1]/best[ext=mp4]/best', 
            'outtmpl': filename,
            'cookiefile': 'cookies.txt', # <--- שורת הקסם שפותחת את החסימה
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True
        }
        
        # מוריד עצמאית בתוך השרת
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        if not os.path.exists(filename):
            raise Exception("הקובץ לא נוצר בהצלחה.")
            
        file_size = os.path.getsize(filename)
        if file_size > 50 * 1024 * 1024:
            bot.edit_message_text("הסרטון שוקל יותר מ-50MB ולכן טלגרם חוסמת אותו. 😔", chat_id=message.chat.id, message_id=status_msg.message_id)
        else:
            bot.edit_message_text("ההורדה הסתיימה! מעלה לטלגרם... ⏳", chat_id=message.chat.id, message_id=status_msg.message_id)
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
        # מנקה את השרת בסיום
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                pass
            
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    print("Bot is listening...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)