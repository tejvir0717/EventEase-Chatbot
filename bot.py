import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters, ContextTypes
)
from datetime import datetime

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define conversation states
MAIN_MENU, CATEGORY, EVENT, BOOKING, NAME, EMAIL = range(6)

# URL of the Django website to scrape event data from localhost
DJANGO_WEBSITE_URL = "http://127.0.0.1:8000"

def scrape_event_categories():
    try:
        response = requests.get(f"{DJANGO_WEBSITE_URL}")
        soup = BeautifulSoup(response.text, 'html.parser')
        categories = {cat.text: f"{DJANGO_WEBSITE_URL}{cat['href']}" for cat in soup.find_all('a', class_='category-link')}
        return categories
    except requests.RequestException as e:
        logger.error(f"Error scraping event categories: {e}")
        return {}

def scrape_events_for_category(category_url):
    try:
        response = requests.get(category_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        events = []
        for event in soup.find_all('div', class_='event'):
            event_data = {
                'id': int(event['data-event-id']),  # Convert to integer
                'name': event.find('h2').text.strip(),
                'start_date': event.find('span', class_='date').text.strip() + ' ' + event.find('span', class_='time').text.strip(),
                'end_date': event.find('span', class_='end-date').text.strip() + ' ' + event.find('span', class_='end-time').text.strip(),
                'category': event.find('span', class_='category').text.strip(),
                'priority': int(event.find('span', class_='priority').text.strip()),
                'description': event.find('p', class_='description').text.strip(),
                'location': event.find('span', class_='venue').text.strip(),
                'organizer': event.find('span', class_='organizer').text.strip(),
                'participants': int(event.find('span', class_='participants').text.strip())
            }  
            events.append(event_data)
        return events
    except requests.RequestException as e:
        logger.error(f"Error scraping events for category: {e}")
        return []

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    features = """
🎉 Welcome to EventEase Bot! 🎉

Here are the main features of our bot:

1. 🎫 Book Event:
   - Choose from various dynamically updated event categories
   - View event details including date, time, venue, and price
   - Complete booking process with personal information

2. ℹ️ Company Info:
   - Learn about EventEase and our specialties

3. 📞 Contact Us:
   - Get our contact information for further inquiries

4. 🤖 Natural Language Processing:
   - We understand and respond to your messages based on intent

How can I assist you today?
    """
    
    keyboard = [
        [InlineKeyboardButton("🎫 Book Event", callback_data='book_event')],
        [InlineKeyboardButton("ℹ️ Company Info", callback_data='company_info')],
        [InlineKeyboardButton("📞 Contact Us", callback_data='contact_us')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(features, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(features, reply_markup=reply_markup)
    return MAIN_MENU

# Book event handler
async def book_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    categories = scrape_event_categories()
    context.user_data['categories'] = categories
    if not categories:
        await query.edit_message_text("Sorry, we couldn't fetch event categories at the moment. Please try again later.")
        return MAIN_MENU
    keyboard = [
        [InlineKeyboardButton(cat, callback_data=f'cat_{cat}')] for cat in categories.keys()
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data='main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🌈 Please select an event category:",
        reply_markup=reply_markup
    )
    return CATEGORY

# Category selection handler

async def category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    category = query.data.split('_')[1]
    context.user_data['category'] = category
    
    await query.edit_message_text(f"You've selected the {category} category. Please enter your name:")
    return NAME

async def enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Please enter your name:")
    return NAME

async def enter_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Please enter your email:")
    return EMAIL

async def save_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print()
    print()
    context.user_data['name'] = update.message.text
    await update.message.reply_text(f"Thanks, {context.user_data['name']}. Now, please enter your email:")
    return EMAIL

async def save_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['email'] = update.message.text
    category = context.user_data.get('category', 'Unknown')
    event = context.user_data.get('event', {})
    name = context.user_data.get('name', 'Not provided')
    email = context.user_data['email']
    
    # Increment participant count
    event_id = event.get('id')
    print("\n\n\n")
    print(event_id)
    if event_id:
        try:
            response = requests.post(f"{DJANGO_WEBSITE_URL}/increment_participants/{event_id}/")
            if response.status_code == 200:
                participants = response.json()['participants']
                booking_message = f"Your booking for '{event['name']}' in the {category} category is confirmed!\n\n"
                booking_message += f"Name: {name}\nEmail: {email}\n\n"
                booking_message += f"You are participant number {participants}!\n\n"
                booking_message += "Thank you for using EventEase!"
            else:
                booking_message = "Your booking is confirmed, but we couldn't update the participant count."
        except requests.RequestException:
            booking_message = "Your booking is confirmed, but we couldn't update the participant count."
    else:
        booking_message = f"Your booking for the {category} category is confirmed!\n\n"
        booking_message += f"Name: {name}\nEmail: {email}\n\n"
        booking_message += "Thank you for using EventEase!"
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(booking_message, reply_markup=reply_markup)
    return MAIN_MENU

async def book_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    name = context.user_data.get('name', 'Not provided')
    email = context.user_data.get('email', 'Not provided')
    category = context.user_data.get('category', 'Unknown')
    
    booking_message = f"Your ticket for the {category} category has been booked!\n\nName: {name}\nEmail: {email}\n\nThank you for using EventEase!"
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(booking_message, reply_markup=reply_markup)
    return MAIN_MENU

# The rest of the code remains the same...
# Event selection handler
async def event_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    event_name = query.data.split('_')[1]
    events = context.user_data['events']
    event = next(event for event in events if event['name'] == event_name)
    context.user_data['event'] = event

    event_details = f"""
    🎭 Event: {event['name']}
    📅 Date: {event['date']}
    🕒 Time: {event['time']}
    📍 Venue: {event['venue']}
    🎤 Artists: {event['artists']}
    
    📝 Description: {event['description']}
    💵 Price per person: ${event['price_per_person']}
    
    Would you like to book this event?
    """
    keyboard = [
        [InlineKeyboardButton("Yes, book now", callback_data='confirm_booking')],
        [InlineKeyboardButton("🔙 Back to Events", callback_data='cat_' + context.user_data['category'])]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(event_details, reply_markup=reply_markup)
    return BOOKING

# Confirm booking handler
async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Event Details", callback_data='back_to_event')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("✨ Wonderful choice! Let's proceed with the booking.\n\nPlease enter your name:", reply_markup=reply_markup)
    return NAME

# Company info handler
async def company_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    company_info_text = """
    About EventEase
    Welcome to EventEase! We specialize in providing seamless event booking experiences. Our platform offers a wide range of events, 
    from cinema screenings to live music and comedy shows. Our mission is to make your event booking process as smooth and enjoyable as possible.
    """
    keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(company_info_text, reply_markup=reply_markup)
    return MAIN_MENU

# Contact info handler
async def contact_us(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    contact_info_text = """
    📞 Contact Us
    
    We'd love to hear from you! If you have any questions or need assistance, please reach out to us:
    
    📧 Email: support@eventease.com
    📱 Phone: +1-234-567-890
    
    Our support team is available Monday to Friday, 9 AM to 6 PM.
    """
    keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(contact_info_text, reply_markup=reply_markup)
    return MAIN_MENU


# Main function to start the bot
def main():
    application = Application.builder().token("6874845152:AAHVmTYvC_6pM_w7TtDDMYqWPvcFN9Vrcsg").build()
    conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        MAIN_MENU: [
            CallbackQueryHandler(book_event, pattern='^book_event$'),
            CallbackQueryHandler(company_info, pattern='^company_info$'),
            CallbackQueryHandler(contact_us, pattern='^contact_us$'),
        ],
        CATEGORY: [
            CallbackQueryHandler(category_selection, pattern='^cat_'),
            CallbackQueryHandler(start, pattern='^main_menu$'),
        ],
        BOOKING: [
            CallbackQueryHandler(enter_name, pattern='^enter_name$'),
            CallbackQueryHandler(enter_email, pattern='^enter_email$'),
            CallbackQueryHandler(book_now, pattern='^book_now$'),
            CallbackQueryHandler(book_event, pattern='^book_event$'),
        ],
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_name)],
        EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_email)],
    },
    fallbacks=[CommandHandler('start', start)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(start, pattern='^main_menu$'))

    application.run_polling()

if __name__ == '__main__':
    main()