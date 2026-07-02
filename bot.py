import telebot
import yt_dlp
import os
import threading
import logging
from flask import Flask

# הגדרת מערכת הלוגים כדי שתוכל לראות את השגיאות מאחורי הקלעים
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TOKEN = os.environ.get('TELEGRAM_TOKEN')
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
    welcome_text = (
        "היי שירן! 🎬\n"
        "שלחי לי קישור לסרטון (מיוטיוב, טיקטוק, אינסטגרם וכדו') ואוריד אותו עבורך.\n\n"
        "⚠️ *שימי לב:* יש מגבלה של *50MB* לקובץ."
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text
    status_message = None
    
    try:
        # שליחת הודעת סטטוס ראשונית ושמירת האובייקט שלה כדי שנוכל לערוך אותה בהמשך
        status_message = bot.reply_to(message, "⏳ *מתחיל בהורדה...*\nאנא המתן מעט", parse_mode='Markdown')
        bot.send_chat_action(message.chat.id, 'record_video')
        
        ydl_opts = {
            'format': 'best[vcodec^=avc1][filesize<50M]/best[filesize<50M]/best', 
            'outtmpl': 'video_%(id)s.%(ext)s',
            'noplaylist': True,
            'quiet': True
        }
        
        # הורדת הסרטון
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        # בדיקת גודל קובץ
        if os.path.getsize(filename) > 50 * 1024 * 1024:
            bot.edit_message_text("⚠️ *הסרטון שוקל יותר מ-50MB* ולכן טלגרם חוסמת את השליחה שלו.", 
                                  chat_id=message.chat.id, 
                                  message_id=status_message.message_id, 
                                  parse_mode='Markdown')
        else:
            # עריכת הודעת הסטטוס לאימוג'י השעון ההפוך לציון התקדמות
            bot.edit_message_text("⌛ *ההורדה הסתיימה!*\nמעלה לטלגרם... 📤", 
                                  chat_id=message.chat.id, 
                                  message_id=status_message.message_id, 
                                  parse_mode='Markdown')
            
            bot.send_chat_action(message.chat.id, 'upload_video')
            
            with open(filename, 'rb') as video:
                bot.send_video(message.chat.id, video, timeout=300)
                
            # עדכון ההודעה להצלחה בסיום העלאה
            bot.edit_message_text("✅ *הסרטון נשלח בהצלחה!*", 
                                  chat_id=message.chat.id, 
                                  message_id=status_message.message_id, 
                                  parse_mode='Markdown')
        
        # מחיקת הקובץ
        os.remove(filename)
        
    except Exception as e:
        # הדפסת השגיאה המלאה ללוגים של השרת בלבד
        logging.error(f"Error processing URL {url}: {e}", exc_info=True)
        
        # הודעה נקייה למשתמש הקצה
        error_text = "❌ *אופס, משהו השתבש בהורדה.*\nייתכן שהקישור לא חוקי או שהסרטון חסום."
        
        if status_message:
            bot.edit_message_text(error_text, 
                                  chat_id=message.chat.id, 
                                  message_id=status_message.message_id, 
                                  parse_mode='Markdown')
        else:
            bot.reply_to(message, error_text, parse_mode='Markdown')

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    logging.info("Bot is listening...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)