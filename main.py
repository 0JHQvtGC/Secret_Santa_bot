from handlers import *
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import os
import logging
from database import create_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CREATING_GAME, GETTING_BUDGET, GETTING_RULES, ADD_USER, ADD_IDEAS, GET_STARTED = range(6)

def main():
    load_dotenv()
    create_db()
    application = ApplicationBuilder().token(os.getenv('TOKEN')).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('create', create_room), CommandHandler('start', start)],
        states={
            CREATING_GAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_game_creation)],
            GETTING_BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_budget)],
            GETTING_RULES: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rules)],
            ADD_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username)],
            ADD_IDEAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ideas)],
            GET_STARTED: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_start)]
        },
        fallbacks=[]
    )
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('my_rooms', my_rooms))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('start_game', start_game))
    application.run_polling()


if __name__ == '__main__':
    main()