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
        for event_div in soup.find_all('div', class_='event'):
            event_data = {
                'id': int(event_div.find('p', id='event-id').text.split(':')[1].strip()),
                'name': event_div.find('p', id='event-name').text.split(':')[1].strip(),
                'category': event_div.find('p', id='event-category').text.split(':')[1].strip(),
                'start_date': event_div.find('p', id='event-start-date').text.split(':')[1].strip(),
                'end_date': event_div.find('p', id='event-end-date').text.split(':')[1].strip(),
                'priority': int(event_div.find('p', id='event-priority').text.split(':')[1].strip()),
                'participants': int(event_div.find('p', id='event-participants').text.split(':')[1].strip()),
                'description': event_div.find('p', id='event-description').text.split(':')[1].strip(),
                'location': event_div.find('p', id='event-location').text.split(':')[1].strip(),
                'organizer': event_div.find('p', id='event-organizer').text.split(':')[1].strip()
            }
            events.append(event_data)
        return events
    except requests.RequestException as e:
        logger.error(f"Error scraping events for category: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error while scraping events: {e}")
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    features = """
🎉 Welcome to EventEase Bot! 🎉

Here are the main features of our bot:

1. 📋 Event Categories List:
   - View all available event categories
   - Browse events within each category
   - Book your chosen event

2. ℹ️ Company Info:
   - Learn about EventEase and our specialties

3. 📞 Contact Us:
   - Get our contact information for further inquiries

How can I assist you today?
    """
    
    keyboard = [
        [InlineKeyboardButton("📋 Event Categories List", callback_data='event_categories')],
        [InlineKeyboardButton("ℹ️ Company Info", callback_data='company_info')],
        [InlineKeyboardButton("📞 Contact Us", callback_data='contact_us')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(features, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(features, reply_markup=reply_markup)
    return MAIN_MENU

async def event_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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

async def category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    category = query.data.split('_')[1]
    context.user_data['category'] = category
    
    category_url = context.user_data['categories'][category]
    events = scrape_events_for_category(category_url)
    context.user_data['events'] = events
    
    if not events:
        await query.edit_message_text(f"Sorry, no events found in the {category} category.")
        return MAIN_MENU
    
    keyboard = [
        [InlineKeyboardButton(event['name'], callback_data=f"event_{event['id']}")] for event in events
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data='event_categories')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(f"Events in {category} category:", reply_markup=reply_markup)
    return EVENT

async def event_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    event_id = int(query.data.split('_')[1])
    events = context.user_data['events']
    event = next((event for event in events if event['id'] == event_id), None)
    
    if not event:
        await query.edit_message_text("Sorry, the selected event was not found.")
        return MAIN_MENU
    
    context.user_data['event'] = event

    event_details = f"""
    🎭 Event: {event['name']}
    🏷️ Category: {event['category']}
    📅 Start: {event['start_date']}
    🏁 End: {event['end_date']}
    🔢 Priority: {event['priority']}
    👥 Participants: {event['participants']}
    📍 Location: {event['location']}
    🎤 Organizer: {event['organizer']}
    
    📝 Description: {event['description']}
    
    Would you like to book this event?
    """
    keyboard = [
        [InlineKeyboardButton("Yes, book now", callback_data='confirm_booking')],
        [InlineKeyboardButton("🔙 Back to Events", callback_data=f"cat_{context.user_data['category']}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(event_details, reply_markup=reply_markup)
    return BOOKING

async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Event Details", callback_data=f"event_{context.user_data['event']['id']}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("✨ Wonderful choice! Let's proceed with the booking.\n\nPlease enter your name:", reply_markup=reply_markup)
    return NAME

async def save_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text
    await update.message.reply_text(f"Thanks, {context.user_data['name']}. Now, please enter your email:")
    return EMAIL

async def save_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['email'] = update.message.text
    event = context.user_data['event']
    name = context.user_data['name']
    email = context.user_data['email']
    
    # Increment participant count
    event_id = event['id']
    try:
        response = requests.post(f"{DJANGO_WEBSITE_URL}/increment_participants/{event_id}/")
        if response.status_code == 200:
            participants = response.json()['participants']
            booking_message = f"Your booking for '{event['name']}' is confirmed!\n\n"
            booking_message += f"Name: {name}\nEmail: {email}\n\n"
            booking_message += f"You are participant number {participants}!\n\n"
            booking_message += "Thank you for using EventEase!"
        else:
            booking_message = "Your booking is confirmed, but we couldn't update the participant count."
    except requests.RequestException:
        booking_message = "Your booking is confirmed, but we couldn't update the participant count."
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(booking_message, reply_markup=reply_markup)
    return MAIN_MENU

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

def main():
    application = Application.builder().token("6874845152:AAHVmTYvC_6pM_w7TtDDMYqWPvcFN9Vrcsg").build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(event_categories, pattern='^event_categories$'),
                CallbackQueryHandler(company_info, pattern='^company_info$'),
                CallbackQueryHandler(contact_us, pattern='^contact_us$'),
            ],
            CATEGORY: [
                CallbackQueryHandler(category_selection, pattern='^cat_'),
                CallbackQueryHandler(start, pattern='^main_menu$'),
            ],
            EVENT: [
                CallbackQueryHandler(event_selection, pattern='^event_'),
                CallbackQueryHandler(event_categories, pattern='^event_categories$'),
            ],
            BOOKING: [
                CallbackQueryHandler(confirm_booking, pattern='^confirm_booking$'),
                CallbackQueryHandler(event_selection, pattern='^event_'),
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