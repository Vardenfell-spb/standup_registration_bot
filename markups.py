from telegram import KeyboardButton, InlineKeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup


def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    """
    Builds button menu from:
    :param buttons: list of InlineKeyboardButton
    :param n_cols: number of menu columns
    :param header_buttons: menu is above message text
    :param footer_buttons: menu is below message text
    :return: args for InlineKeyboardMarkup
    """
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        menu.append([footer_buttons])
    return menu


repeat = KeyboardButton('Repeat')
new_word = KeyboardButton('Create')
translate = KeyboardButton('Translate')
remember = KeyboardButton("Remember")
forgot = KeyboardButton("Forgot")
delete = KeyboardButton("Delete")
yes = KeyboardButton("Yes")
no = KeyboardButton("No")

markup_start = ReplyKeyboardMarkup(build_menu([repeat, new_word], n_cols=2), resize_keyboard=True)
markup_send_card = ReplyKeyboardMarkup([[remember, forgot], [new_word, delete]], resize_keyboard=True)
markup_delete = ReplyKeyboardMarkup(build_menu([yes, no, new_word, repeat], n_cols=2), resize_keyboard=True)
markup_create = markup_start


def page_markup(pages_list, button):
    func_name = button[0]
    new_buttons = []
    next_page = int(button[2])
    if next_page == 0 and len(pages_list) > 2:
        new_buttons.append(InlineKeyboardButton(f'▷▷',
                                                callback_data=f'{func_name} {button[1]} {len(pages_list) - 1}'))
    elif next_page != 0 and len(pages_list) > 1:
        new_buttons.append(InlineKeyboardButton(f'◁',
                                                callback_data=f'{func_name} {button[1]} {next_page - 1}'))
    if len(pages_list) > 1:
        new_buttons.append(InlineKeyboardButton(f'{next_page + 1}',
                                                callback_data=f'{func_name} {button[1]} {next_page}'))
    else:
        new_buttons.append(InlineKeyboardButton(f'↻',
                                                callback_data=f'{func_name} {button[1]} {next_page}'))

    if next_page == len(pages_list) - 1 and len(pages_list) > 2:
        new_buttons.append(InlineKeyboardButton(f'◁◁',
                                                callback_data=f'{func_name} {button[1]} 0'))
    elif next_page != len(pages_list) - 1 and len(pages_list) > 1:
        new_buttons.append(InlineKeyboardButton(f'▷',
                                                callback_data=f'{func_name} {button[1]} {next_page + 1}'))
    message_markup = InlineKeyboardMarkup(build_menu(new_buttons, n_cols=3))
    return message_markup


def list_step(proc_list, current_step, step_change):
    """
    Cycle change from list
    :param proc_list: list of changed parameters
    :param current_step: currents value (from user settings)
    :param step_change: change value (+1, -1) for button
    :return: list value number for changed parametr
    """
    step_change = int(step_change)
    if current_step + step_change >= len(proc_list):
        next_step = current_step + step_change - len(proc_list)
    elif current_step + step_change < 0:
        next_step = len(proc_list) + current_step + step_change
    else:
        next_step = current_step + step_change
    return next_step


def delete_markup(button):
    func_name = button[0]
    message_markup = InlineKeyboardMarkup(build_menu([
        (InlineKeyboardButton(f'✔️Yes', callback_data=f'{func_name} {button[1]} yes')),
        (InlineKeyboardButton(f'✖️No', callback_data=f'{func_name} {button[1]} no')),
    ], n_cols=2), resize_keyboard=True)
    return message_markup


def user_settings(call_user, user, botton=None):
    def bool_emoji(value):
        if value:
            return '◉ '
        else:
            return ''

    username = InlineKeyboardButton(f'{user.username}', url=f'tg://user?id={user.user_id}')
    roll_multiplier_minus = InlineKeyboardButton(
        f'〘Бонус: {user.roll_multiplier}〙 ▽',
        callback_data=f'user_set {user.user_id} roll_multiplier sub')
    roll_multiplier_plus = InlineKeyboardButton(
        f'△', callback_data=f'user_set {user.user_id} roll_multiplier add')

    reroll_minus = InlineKeyboardButton(f'〘Повтор: {user.reroll}〙 ▽',
                                        callback_data=f'user_set {user.user_id} reroll sub')
    reroll_plus = InlineKeyboardButton(f'△', callback_data=f'user_set {user.user_id} reroll add')
    admin = InlineKeyboardButton(f'{bool_emoji(user.admin)} Админ',
                                 callback_data=f'user_set {user.user_id} admin {not user.admin}')
    moderator = InlineKeyboardButton(f'{bool_emoji(user.moderator)} Модератор',
                                     callback_data=f'user_set {user.user_id} moderator {not user.moderator}')
    ban = InlineKeyboardButton(f'{bool_emoji(user.ban)} Бан',
                               callback_data=f'user_set {user.user_id} ban {not user.ban}')
    fix = InlineKeyboardButton(f'{bool_emoji(user.fix)} Заморозка бонуса',
                               callback_data=f'user_set {user.user_id} fix {not user.fix}')
    user_list = InlineKeyboardButton(f'◁◁ Список пользователей',
                                     callback_data=f'user_set {user.user_id} user_list None')
    markup_buttons = [
        [user_list],
        [username],
        [roll_multiplier_minus, roll_multiplier_plus],
        [reroll_minus, reroll_plus],
        [fix],
    ]
    if call_user.admin:
        markup_buttons.append([ban])
        markup_buttons.append([moderator])
        markup_buttons.append([admin])
    message_markup = InlineKeyboardMarkup(markup_buttons)
    return message_markup


def message_delete(word):
    save_button = [
        (InlineKeyboardButton(f'{word}', callback_data=f'message_delete None None')),
    ]
    message_markup = InlineKeyboardMarkup(build_menu(save_button, n_cols=2))
    return message_markup


def event_markup(events, user, button=None):
    events_ids = list(events.keys())
    if not button:
        button = ['load_events', events_ids[0], 'load']
    event_id = int(button[1])
    event_index = events_ids.index(event_id)
    events_list_len = len(events_ids)
    func_name = button[0]
    new_buttons = []
    event = events[event_id]
    if events_list_len > 1:
        next_page = event_index + 1
        if next_page >= events_list_len:
            next_page -= events_list_len
        prev_page = event_index - 1
        new_buttons.append(InlineKeyboardButton(
            f'◁', callback_data=f'{func_name} {events_ids[prev_page]} load'))
        new_buttons.append(InlineKeyboardButton(
            f'▷', callback_data=f'{func_name} {events_ids[next_page]} load'))
    cancel_button = None
    if user.moderator or user.admin:
        if event.status == 'open':
            new_buttons.append(InlineKeyboardButton(
                'Подсчет', callback_data=f'{func_name} {event.event_id} close'))
        elif event.status == 'closed':
            new_buttons.append(InlineKeyboardButton(
                'Архив', callback_data=f'{func_name} {event.event_id} archiving'))
        if event.status == 'archived':
            new_buttons.append(InlineKeyboardButton(
                'Удалить', cancel_button, callback_data=f'{func_name} {event.event_id} delete'))
        else:
            new_buttons.append(InlineKeyboardButton(
                'Участники', cancel_button, callback_data=f'{func_name} {event.event_id} edit'))
    if event.status == 'open':
        if user.user_id in event.users:
            roll_value = event.users[user.user_id]['roll']
            roll_button = f'{roll_value} 🎲'
            if user.reroll > 0:
                roll_button += f'\n⟲{user.reroll}'
            if event.users[user.user_id]['cancel']:
                roll_button = f'{roll_value}🚫'
                cancel_button = 'Вернуться'
            else:
                cancel_button = 'Отмена'
        else:
            roll_button = f'🎲'
            if user.reroll > 0:
                roll_button += f'×{user.reroll}'

        new_buttons.append(InlineKeyboardButton(
            roll_button, callback_data=f'{func_name} {event.event_id} roll'))
        if cancel_button:
            new_buttons.append(InlineKeyboardButton(
                cancel_button, callback_data=f'{func_name} {event.event_id} cancel'))
        new_buttons.append(InlineKeyboardButton(
            '⟳', callback_data=f'{func_name} {event.event_id} load'))

    message_markup = InlineKeyboardMarkup(build_menu(new_buttons, n_cols=2))
    return message_markup


def event_edit_markup(event, button):
    users = event.users
    page = int(button[4])
    page_size = 10
    user_pages = [[]]
    for user_key in users:
        if len(user_pages[len(user_pages) - 1]) < page_size:
            user_pages[len(user_pages) - 1].append(users[user_key])
        else:
            user_pages.append([users[user_key]])
    user_page = user_pages[page]
    buttons = [[InlineKeyboardButton(f'◁◁ {event.title}',
                                     callback_data=f'load_events {event.event_id} load')],
               [InlineKeyboardButton(f'〘Мест: {event.attendees}〙 ▽',
                                     callback_data=f'edit_event {event.event_id} attendees_sub None {page}'),
                InlineKeyboardButton(f'△',
                                     callback_data=f'edit_event {event.event_id} attendees_add None {page}'), ]]
    for event_user in user_page:
        username = event_user['username']
        user_id = event_user['user_id']
        roll = event_user['roll']
        if event_user['cancel']:
            cancel_button_text = f'Вернуть 🚫 {roll}'
        else:
            cancel_button_text = f'Отмена 🎲 {roll}'
        buttons.append([InlineKeyboardButton(f'❌ {username}',
                                             callback_data=f'edit_event {event.event_id} delete {user_id} {page}'),
                        InlineKeyboardButton(f'{cancel_button_text}',
                                             callback_data=f'edit_event {event.event_id} cancel {user_id} {page}'), ])
    if len(user_pages) > 1:
        buttons.append([
            InlineKeyboardButton(
                '◁', callback_data=f'edit_event {event.event_id} load None {list_step(user_pages, page, -1)}'),
            InlineKeyboardButton(
                '▷', callback_data=f'edit_event {event.event_id} load None {list_step(user_pages, page, 1)}'), ])
    message_markup = InlineKeyboardMarkup(buttons)
    return message_markup


def load_users_set(users, button):
    if not button:
        page = 0
    else:
        page = int(button[2])
    buttons = []
    page_size = 10
    for num, user in enumerate(users):
        status = ''
        if user.admin:
            status += f'♚'
        elif user.moderator:
            status += f'♔'
        if user.ban:
            status += f'✖'
        button_text = f'{num + 1}: {user.roll_multiplier}⇧{user.reroll}♡{len(user.registration)}✎ {status}: ' \
                      f'{user.username}' + '.' * 100
        buttons.append([InlineKeyboardButton(button_text, callback_data=f'load_users load {user.user_id}')])
    button_pages = [[]]
    for list_button in buttons:
        if len(button_pages[len(button_pages) - 1]) < page_size:
            button_pages[len(button_pages) - 1].append(list_button)
        else:
            button_pages.append([list_button])

    if not page < len(button_pages):
        page = 0
    buttons = button_pages[page]
    if len(button_pages) > 1:
        buttons.append([
            InlineKeyboardButton(
                '◁', callback_data=f'load_users None {list_step(button_pages, page, -1)}'),
            InlineKeyboardButton(
                f'{page + 1}', callback_data=f'load_users None {page}'),
            InlineKeyboardButton(
                '▷', callback_data=f'load_users None {list_step(button_pages, page, 1)}')])
    message_markup = InlineKeyboardMarkup(buttons)
    return message_markup


markups = {'start': markup_start,
           'user_settings': user_settings,
           'create': markup_create,
           'delete': markup_delete,
           'delete_markup': delete_markup,
           'page_markup': page_markup,
           'message_delete': message_delete,
           'event_markup': event_markup,
           'event_edit_markup': event_edit_markup,
           'load_users_set': load_users_set,
           }
