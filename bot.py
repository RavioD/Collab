import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, LabeledPrice, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, PreCheckoutQueryHandler
import config
import sqlite3
from datetime import datetime
import re
import requests



logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

videUrl = 'https://www.youtube.com/watch?v=U6fC4Ij608A'
conn = sqlite3.connect('bot_db.db')
cursor = conn.cursor()
table = """ CREATE TABLE IF NOT EXISTS card_data (
                id BIGINT(100) PRIMARY KEY NOT NULL,
                user_id BIGINT(100)
                txid TEXT NOT NULL,
                amount DECIMAL(10, 2) NOT NULL, -- Assuming you're dealing with a currency that has cents or similar
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            ); """
        
cursor.execute(table)
conn.close()



# output videoUrl to telegram chat
def send_video(update, context):
    context.bot.send_video(chat_id=update.effective_chat.id, video=videUrl)

ENTER_BOT =[
        [
            InlineKeyboardButton("Enter Bot", callback_data="back_to_menu"),
        ],
        [ 
            InlineKeyboardButton("Visit website", url="https://google.com"),
                    
        ],
        [
            InlineKeyboardButton("Open docs", url="https://docs.google.com")
        ]
    ]

MAIN_MENU = [
        [
            InlineKeyboardButton("Issue a new card", callback_data="Issue a new card"), 
            InlineKeyboardButton("List cards", callback_data="List cards")
        ], 
        [
            InlineKeyboardButton("Top-up card", callback_data="Top-up card"), 
            InlineKeyboardButton("Display card details", callback_data="Display card details")
        ], 
        [
            InlineKeyboardButton("List my transactions", callback_data="List my transactions"), 
            InlineKeyboardButton("Support", callback_data="Support")
        ]
    ]



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_markup = InlineKeyboardMarkup(ENTER_BOT)
    # SEND VIDEO from VIDEO_URL
    await update.message.reply_video(videUrl, reply_markup=reply_markup)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer() 
    reply_markup = InlineKeyboardMarkup(MAIN_MENU)
    await query.delete_message()
    await context.bot.send_message(
        chat_id = update.effective_chat.id, 
        text = config.WEL_MSG.format(update.effective_user.first_name), 
        reply_markup=reply_markup, 
        parse_mode = "HTML"
    )

async def Issue_a_new_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer() 
    keyboard = [[InlineKeyboardButton("Back", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Check how many cards the user already has
    conn = sqlite3.connect('bot_db.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM card_data WHERE user_id = ?", (update.effective_user.id,))
    card_count = cursor.fetchone()[0]
    conn.close()

    # Limit to 1 cards per user
    if card_count >= 1:
        await query.edit_message_text(
            text="You have reached the maximum limit of 2 cards.",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return

    url = 'https://api.pst.net/integration/user/card/buy'
    headers = {
    'Authorization': f'Bearer {config.API_TOKEN}',
    'accept': 'application/json',
    'Content-Type': 'application/json',
    'X-CSRF-TOKEN': ''
    }
    data = {
        "account_id": 2939017,
        "type": "adv",
        "start_balance": "1",
        "description": f"user {str(update.effective_user.id)}",
        "system": 5,
        "bin": 512631,
        "with_error_data": True
    }

    response = requests.post(url, headers=headers, json=data)
    card_data = response.json()
    try:
        card_id = card_data["data"]["id"]
        conn = sqlite3.connect('bot_db.db')
        cursor = conn.cursor()
        cursor.execute(f'''INSERT INTO card_data VALUES ('{card_id}', '{update.effective_user.id}')''')
        conn.commit()

        await query.delete_message()
        await context.bot.send_message(
            chat_id = update.effective_chat.id, 
            text = f"Successfully created ✅\n\n<b>Card ID: </b> {card_id}", 
            reply_markup=reply_markup, 
            parse_mode = "HTML"
        )
    except:
        await query.delete_message()
        await context.bot.send_message(
            chat_id = update.effective_chat.id, 
            text = "<b>Sorry you cant make this action at this time.</b>\n\nNot enough money to create cards ‼️", 
            reply_markup=reply_markup, 
            parse_mode = "HTML"
        )

async def List_cards(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer() 
    
    keyboard = [[InlineKeyboardButton("Back", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    conn = sqlite3.connect('bot_db.db')
    cursor = conn.cursor()
    cursor.execute(f'''SELECT * FROM card_data WHERE user_id = '{update.effective_user.id}' ''')
    result = cursor.fetchall()

    if len(result) == 0:
        msg = "You have no created cards yet ⭕️"
    else:
        msg = "Available cards IDs:\n\n"
        for I in result:
            msg = msg + f"🔹 {I[0]}\n"

    await query.delete_message()
    await context.bot.send_message(
        chat_id = update.effective_chat.id, 
        text = msg, 
        reply_markup=reply_markup, 
        parse_mode = "HTML"
    )   

async def Top_up_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("Back", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.delete_message()
    await context.bot.send_message(
        chat_id = update.effective_chat.id, 
        text = config.TOP_UP_MSG, 
        reply_markup=reply_markup, 
        parse_mode = "HTML"
    )

async def Display_card_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    conn = sqlite3.connect('bot_db.db')
    cursor = conn.cursor()
    cursor.execute(f'''SELECT * FROM card_data WHERE user_id = '{update.effective_user.id}' ''')
    result = cursor.fetchall()

    if len(result) == 0:
        keyboard = [[InlineKeyboardButton("Back", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.delete_message()
        await context.bot.send_message(
            chat_id = update.effective_chat.id, 
            text = "There are no cards ⭕️", 
            reply_markup=reply_markup, 
            parse_mode = "HTML"
        )
    else:
        keyboard = []
        for I in result:
            keyboard.append([InlineKeyboardButton(str(I[0]), callback_data=f"crd {str(I[0])}")])
        keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.delete_message()
        await context.bot.send_message(
            chat_id = update.effective_chat.id, 
            text = "Avilable cards:", 
            reply_markup=reply_markup, 
            parse_mode = "HTML"
        )

async def card_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    crd_id = query.data.split()[1]

    url = f'https://api.pst.net/integration/user/card/{crd_id}/showpan'
    headers = {
    'Authorization': f'Bearer {config.API_TOKEN}',
    'accept': 'application/json',
    'Content-Type': 'application/json',
    'X-CSRF-TOKEN': ''
    }

    response = requests.get(url, headers=headers)

    crd_data = response.json()

    crd_number = crd_data["data"]["number"]
    user_cvx = crd_data["data"]["cvx2"]
    ex_month = crd_data["data"]["exp_month"]
    ex_year = crd_data["data"]["exp_year"]
    passwd = crd_data["data"]["password"]


    keyboard = [[InlineKeyboardButton("Back", callback_data="back_to_crd")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.delete_message()
    await context.bot.send_message(
        chat_id = update.effective_chat.id, 
        text = config.CARD_DETAILS.format(crd_number, user_cvx, ex_month, ex_year, passwd), 
        reply_markup=reply_markup, 
        parse_mode = "HTML"
    ) 

async def my_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    conn = sqlite3.connect('bot_db.db')
    cursor = conn.cursor()
    cursor.execute(f'''SELECT * FROM card_data WHERE user_id = '{update.effective_user.id}' ''')
    result = cursor.fetchall()

    if len(result) == 0:
        keyboard = [[InlineKeyboardButton("Back", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.delete_message()
        await context.bot.send_message(
            chat_id = update.effective_chat.id, 
            text = "There are no active cards to list transactions ⭕️", 
            reply_markup=reply_markup, 
            parse_mode = "HTML"
        )
    else:
        cards = ""
        for I in result:
            card = cards + f"{str(I[0])}, "

        url = 'https://api.pst.net/integration/transactions-v2'
        params = {
            'type': '0',
            'cards': cards
        }
        headers = {
        'Authorization': f'Bearer {config.API_TOKEN}',
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'X-CSRF-TOKEN': ''
        }

        response = requests.get(url, params=params, headers=headers)

        crd_data = response.json()
        if crd_data["data"] == []:
            keyboard = [[InlineKeyboardButton("Back", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.delete_message()
            await context.bot.send_message(
                chat_id = update.effective_chat.id, 
                text = "There are no transactions ⭕️", 
                reply_markup=reply_markup, 
                parse_mode = "HTML"
            )
        else:
            trans_msg = "<b>TRANSACTIONS</b>\n\n"
            for I in crd_data["data"]:
                trans_msg = trans_msg + f"<b>ID:</b> {I['id']}\n<b>Amount: </b> {I['amount_total']}\n\n"

            keyboard = [[InlineKeyboardButton("Back", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.delete_message()
            await context.bot.send_message(
                chat_id = update.effective_chat.id, 
                text = trans_msg, 
                reply_markup=reply_markup, 
                parse_mode = "HTML"
            )

        

async def support_func(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("Back", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.delete_message()
    await context.bot.send_message(
        chat_id = update.effective_chat.id, 
        text = config.SUPPORT_MSG, 
        reply_markup=reply_markup, 
        parse_mode = "HTML"
    )

def main() -> None:
    application = Application.builder().token(config.BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(main_menu, pattern="^back_to_menu$"))
    application.add_handler(CallbackQueryHandler(Issue_a_new_card, pattern="^Issue a new card$"))
    application.add_handler(CallbackQueryHandler(List_cards, pattern="^List cards$"))
    application.add_handler(CallbackQueryHandler(Top_up_card, pattern="^Top-up card$"))
    application.add_handler(CallbackQueryHandler(Display_card_details, pattern="^(Display card details|back_to_crd)$"))
    application.add_handler(CallbackQueryHandler(card_details, pattern=r'^{}'.format(re.escape("crd"))))
    application.add_handler(CallbackQueryHandler(my_transactions, pattern="^List my transactions$"))
    application.add_handler(CallbackQueryHandler(support_func, pattern="^Support$"))
    

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()