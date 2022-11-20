import datetime
import logging
import random
from functools import reduce
from markups import markups
from manage import DatabaseManager
from models import User, Event
from settings import *
from handlers import *
from telegram_token import TOKEN
from collections import defaultdict

from telegram import Update
from telegram.ext import Updater
from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram.ext import CallbackContext, CallbackQueryHandler

try:
    from telegram_token import *
except ImportError:
    exit('Скопируйте telegram_token.py.deafault как telegram_token.py и укажите в нем токен')

log = logging.getLogger()
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
log.addHandler(stream_handler)
log.setLevel(logging.DEBUG)
stream_handler.setLevel(logging.INFO)


def def_value():
    return User(0, None, None)


def default_markup():
    return markups['start']


class Bot:
    def __init__(self, token):
        self.events = None
        self.users = defaultdict(def_value)
        self.bot = Updater(token=token)
        self.db = DatabaseManager()
        self.button_handlers = {
            'load_events': self.load_events,
            'help': self.help_command,
            'message_delete': self.message_delete,
            'user_set': self.user_settings,
            'load_users': self.load_users,
        }

    def run(self):
        """
        Run the bot
        """
        updater = Updater(token=TOKEN)
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CommandHandler('start', self.start))
        dispatcher.add_handler(CommandHandler('help', self.help_command))
        dispatcher.add_handler(CommandHandler('load_events', self.load_events))
        dispatcher.add_handler(CommandHandler('load_users', self.load_users))
        dispatcher.add_handler(CallbackQueryHandler(self.button))
        dispatcher.add_handler(MessageHandler(Filters.text, self.handle_messages))
        updater.start_polling()

    def handle_messages(self, update: Update, context: CallbackContext):
        self.user_check(update)
        try:
            log.debug('обнаружен ивент: %s', update.message.text)
            self.on_event(update, context)
        except ConnectionError:
            log.exception(f'Ошибка при получении ивента')

    def new_user(self, user_id, username):
        """
        :return: create new user for keeping repeating cards, load cards from database for the user id
        """
        user = User(user_id, username, self.db)
        user.load()
        if user.user_id == DEFAULT_ADMIN_ID:
            user.admin = True
            user.moderator = True
            # user.roll_multiplier = -5
            # user.reroll = 9999
            user.save()
        self.users[user_id] = user
        log.info('User is created, id: %s', user_id)

    def on_event(self, update, context):
        user_id = update.message.from_user.id
        if update:
            if user_id not in self.users:
                self.new_user(user_id, update.message.from_user.username)
            user = self.users[user_id]
            if update.message.text[:6] == '/event':
                if user.admin or user.moderator:
                    options = update.message.text[7:]
                    self.create_event(update, context, options=options)
            elif update.message.text[:5] == '/user':
                username = update.message.text[6:]
                button = ['user_set', username, 'load', 'None']
                self.user_settings(update, context, button)

    def start(self, update: Update, context: CallbackContext):
        # user = self.user_check(update)
        log.debug('/start')
        self.load_events(update, context)

    def user_check(self, update, user_id=None):
        if update.message:
            user_id = update.message.from_user.id
            if user_id not in self.users:
                self.new_user(update.message.from_user.id, update.message.from_user.username)
        elif update.callback_query:
            user_id = update.callback_query.from_user.id
            if user_id not in self.users:
                self.new_user(update.callback_query.from_user.id, update.callback_query.from_user.username)
        if user_id in self.users:
            return self.users[user_id]

    def user_settings(self, update, context, button):
        username = button[1]
        command = button[2]
        value = button[3]
        if value == 'True':
            value = True
        elif value == 'False':
            value = False
        user = self.user_check(update)
        if not username:
            username = user.username
        database_user = self.db.load_username(username)

        def user_update(user):
            if user.user_id in self.users:
                self.users[user.user_id].load()

        if database_user and (user.admin and user.moderator):
            message = 'Настройки'
            if command == 'load':
                markup = markups['user_settings'](user, database_user)
                context.bot.send_message(update.effective_chat.id, message, reply_markup=markup)
            else:
                if command == 'roll_multiplier':
                    if value == 'sub':
                        database_user.roll_multiplier -= 1
                    else:
                        database_user.roll_multiplier += 1
                    database_user.save()
                    user_update(database_user)
                elif command == 'reroll':
                    if database_user.reroll > 0 and value == 'sub':
                        database_user.reroll -= 1
                    else:
                        database_user.reroll += 1
                    database_user.save()
                    user_update(database_user)
                elif command == 'admin':
                    database_user.admin = value
                    database_user.save()
                    user_update(database_user)
                elif command == 'moderator':
                    database_user.moderator = value
                    database_user.save()
                    user_update(database_user)
                elif command == 'ban':
                    database_user.ban = value
                    database_user.save()
                    user_update(database_user)
                elif command == 'fix':
                    database_user.fix = value
                    database_user.save()
                    user_update(database_user)
                markup = markups['user_settings'](user, database_user)
                return [message, markup, None]
        elif database_user and (not user.admin and not user.moderator):
            message = f'Свойства юзера:\nБонус: {database_user.roll_multiplier}\nПовтор: {database_user.reroll}'
            context.bot.send_message(update.effective_chat.id, message)

    def load_users(self, update: Update, context: CallbackContext, button=None):
        user = self.user_check(update)
        users = self.db.load_users(user)
        full_message = self.pages_handler(users, 'load_users', button)
        if button:
            return full_message
        else:
            context.bot.send_message(update.effective_chat.id, full_message[0], reply_markup=full_message[1])

    def pages_handler(self, page_list, func_name, button):
        if button:
            page = int(button[2])
            if page > len(page_list) - 1:
                page = 0
                markup = markups['page_markup'](pages_list=page_list, button=[f'{func_name}', 'None', 0])
            else:
                markup = markups['page_markup'](pages_list=page_list, button=button)
            message = reduce(lambda a, x: a + x, page_list[page])
        else:
            markup = markups['page_markup'](pages_list=page_list, button=[f'{func_name}', 'None', 0])
            message = reduce(lambda a, x: a + x, page_list[0])
        return [message, markup, None]

    def help_command(self, update: Update, context: CallbackContext, button=None):
        user = self.user_check(update)
        pages = [MESSAGE['help']]
        if user.moderator or user.admin:
            pages.append(MESSAGE['help-moderator'])
        if user.admin:
            pages.append(MESSAGE['help-admin'])
        if button:
            page = int(button[2])
            if page > len(pages) - 1:
                page = 0
                markup = markups['page_markup'](pages_list=pages, button=[f'help', 'None', 0])
            else:
                markup = markups['page_markup'](pages_list=pages, button=button)
            message = pages[page]
            return [message, markup, None]
        else:
            markup = markups['page_markup'](pages_list=pages, button=[f'help', 'None', 0])
            message = pages[0]
            context.bot.send_message(update.effective_chat.id, message, reply_markup=markup)

    def create_event(self, update, context, options):
        options = options.split(sep='\n')
        syntax_error = False
        if len(options) == 3:
            raw_date = options[1].split(sep='.')
            if len(raw_date) == 3:
                try:
                    event_date = datetime.datetime(
                        day=int(raw_date[0]),
                        month=int(raw_date[1]),
                        year=int(raw_date[2]),
                    )
                except SyntaxError:
                    event_date = None
                    syntax_error = True
                event_attendees = options[2]
                if event_date and event_attendees.isnumeric():
                    event_title = options[0]
                    event = Event(
                        title=event_title,
                        date=event_date,
                        attendees=int(event_attendees)
                    )
                    success = self.db.create_event(event=event)
                    if success:
                        self.load_events(update, context)
                else:
                    syntax_error = True
            else:
                syntax_error = True
        else:
            syntax_error = True
        if syntax_error:
            message = f'Ошибка форматирования.\n Чтобы создать мероприятние напишите команду вида:\n' \
                      f'/event\n[Название]\n[дата]\n[количество человек]\nНапример:\n' \
                      f'/event\nНовый год\n31.12.2022\n20'
            context.bot.send_message(update.effective_chat.id, message)

    def message_delete(self, update, context, button=None):
        self.user_check(update)
        context.bot.delete_message(update.effective_chat.id, update.callback_query.message.message_id)

    def load_events(self, update: Update, context: CallbackContext, button=None):
        user = self.user_check(update)
        self.events = self.db.load_events(user)
        if self.events:
            events_ids = list(self.events.keys())
            if button:
                event_id = int(button[1])
                if event_id in events_ids:
                    event = self.events[event_id]
                else:
                    event = self.events[events_ids[0]]
                    event_id = int(events_ids[0])
                    button = ['load_events', event_id, 'load']
                return_button = ['load_events', event_id, 'load']
                if button[2] == 'roll':
                    if user.user_id not in self.events[event_id].users or user.reroll > 0:
                        if user.ban:
                            context.bot.send_message(update.effective_chat.id, 'Как-нибудь в другой раз')
                        else:
                            return self.roll(update, context, event_id, user)
                elif button[2] == 'close':
                    self.db.close_event(event, user)
                    self.users = defaultdict(def_value)
                    return self.load_events(update, context, return_button)
                elif button[2] == 'delete':
                    self.db.delete_event(event, user)
                    return self.load_events(update, context, return_button)
                elif button[2] == 'archiving':
                    self.db.archiving_event(event, user)
                    return self.load_events(update, context, return_button)
                elif button[2] == 'cancel':
                    if event.status == 'open':
                        roll = event.users[user.user_id]['roll']
                        self.db.registration(event, user, roll, cancel=not event.users[user.user_id]['cancel'])
                    return self.load_events(update, context, return_button)
                elif event_id in events_ids:
                    markup = markups['event_markup'](events=self.events, user=user, button=button)
                    message = self.event_message(user, self.events[event_id])
                    return [message, markup, None]
                else:
                    return self.load_events(update, context)
            else:
                markup = markups['event_markup'](events=self.events, user=user)

                message = self.event_message(user, self.events[events_ids[0]])
                context.bot.send_message(update.effective_chat.id, message, reply_markup=markup)
        else:
            # no one event
            if button:
                message = 'Регистрация на мероприятие закрыта'
                return [message, None, None]
            else:
                context.bot.send_message(update.effective_chat.id, 'Нет мероприятий')

    def roll(self, update, context, event_id, user):
        if event_id in list(self.events.keys()):
            event = self.events[event_id]
            rolls_num = 1 + abs(user.roll_multiplier)
            rolls = []
            for roll in range(rolls_num):
                rolls.append(random.randint(1, 100))
            if user.roll_multiplier < 0:
                sorted_rolls = sorted(rolls)
                bonus = f'({user.roll_multiplier})'
            else:
                if user.roll_multiplier != 0:
                    bonus = f'(+{user.roll_multiplier})'
                else:
                    bonus = ''
                sorted_rolls = sorted(rolls, reverse=True)
            result_roll = sorted_rolls[0]
            another_rolls = f'Бросок{bonus}: '
            for another_roll in rolls:
                another_rolls += f'∙{another_roll}'
            context.bot.send_message(
                update.effective_chat.id,
                f'{another_rolls}',
                reply_markup=markups['message_delete'](f'🎲 {sorted_rolls[0]}')
            )
            if user.user_id in event.users:
                if user.reroll > 0:
                    user.reroll -= 1
                    user.save()
                    if event.users[user.user_id]['roll'] > result_roll:
                        return None
            self.db.registration(event, user, result_roll, cancel=False)
            button = ['load_events', event_id, 'load']
            return self.load_events(update, context, button)

    def event_message(self, user, event):
        message_user = user
        users_rolls = ''
        # sort users by current roll
        users = []
        for user_id in event.users:
            if not event.users[user_id]['cancel']:
                users.append(event.users[user_id])
        users = sorted(event.users, key=lambda u: event.users[u]['roll'], reverse=True)
        active_users = []
        for user in users:
            if not event.users[user]['cancel'] and not event.users[user]['ban']:
                active_users.append(user)
        if len(active_users) > 0:
            users_rolls += '\n⊶'
            if len(active_users) < event.attendees:
                list_lenght = len(active_users)
            else:
                list_lenght = event.attendees
            for num in range(list_lenght):
                user = active_users[num]
                user_roll = event.users[user]['roll']
                username = event.users[user]['username']
                if message_user.admin or message_user.moderator:
                    username = '@' + username
                users_rolls += f'\n{user_roll} - {username}'
        message = f'{event.title}\nУчастников: {event.attendees}\nДата: {event.date}{users_rolls}'
        return message

    def button(self, update: Update, context: CallbackContext):
        # buttons callback handler
        self.user_check(update)
        query = update.callback_query
        button = query.data.split()
        logging.debug('Pressed button: %s', button)
        query.answer()
        if button[0] in self.button_handlers:
            message_edit = self.button_handlers[button[0]](update, context, button=button)
            logging.debug('Edited message: %s', button)
            if message_edit:
                button_compare_result = button_compare(message_edit,
                                                       update.callback_query.message.reply_markup.inline_keyboard)
                # print(
                #     f'{button_compare_result}\n{len(message_edit[0])}\n{message_edit[0]}\n'
                #     f'{len(update.callback_query.message.text)}\n{update.callback_query.message.text}')
                try:
                    if (message_edit[0] != update.callback_query.message.text) or button_compare_result:
                        if message_edit[2] and message_edit[1]:
                            query.edit_message_text(text=message_edit[0], reply_markup=message_edit[1],
                                                    entities=[message_edit[2]])
                        elif message_edit[1]:
                            query.edit_message_text(text=message_edit[0], reply_markup=message_edit[1])
                        elif message_edit[2]:
                            query.edit_message_text(text=message_edit[0], entities=[message_edit[2]])
                        else:
                            query.edit_message_text(text=message_edit[0])
                except SyntaxError:
                    log.exception(f'Ошибка редактирования сообщения\nbutton_compare_result: {button_compare_result}\n'
                                  f'message_edit: {message_edit}\n'
                                  f'update.callback_query.message.text: {update.callback_query.message.text}')


if __name__ == '__main__':
    mindcard_bot = Bot(TOKEN)
    mindcard_bot.run()
