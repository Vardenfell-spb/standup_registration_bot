# -*- coding: utf-8 -*-
import os
import datetime
import logging
from models import UserDB, EventDB, Registration, Event, standup_db

log = logging.getLogger()


# Database manager
class DatabaseManager:
    def __init__(self):
        self.user = None
        if not os.path.exists('standup.db'):
            standup_db.connect()
            standup_db.create_tables([EventDB, UserDB, Registration])

    def save_user(self, user):
        # Save user from bot to DB
        if UserDB.select().where(UserDB.user_id == user.user_id):
            db_user = UserDB.select().where(UserDB.user_id == user.user_id).get()
            db_user.username = user.username
            db_user.roll_multiplier = user.roll_multiplier
            db_user.reroll = user.reroll
            db_user.admin = user.admin
            db_user.moderator = user.moderator
            db_user.ban = user.ban
            db_user.fix = user.fix
            db_user.save()
        else:
            self.create_user(user)

    def load_user(self, user):
        # Update user data from DB
        if UserDB.select().where(UserDB.user_id == user.user_id):
            db_user = UserDB.select().where(UserDB.user_id == user.user_id).get()
            user.roll_multiplier = db_user.roll_multiplier
            user.reroll = db_user.reroll
            user.admin = db_user.admin
            user.moderator = db_user.moderator
            user.ban = db_user.ban
            user.fix = db_user.fix
        else:
            self.create_user(user)

    def load_username(self, username):
        user = UserDB.select().where(UserDB.username == username)
        if user:
            user = user.get()
            return user

    def create_user(self, user):
        # Create user in DB from bot user class
        try:
            create = UserDB.create(
                user_id=user.user_id,
                username=user.username,
                roll_multiplier=user.roll_multiplier,
                reroll=user.reroll,
                admin=user.admin,
                moderator=user.moderator,
                ban=user.ban,
                fix=user.fix,
            )
            if create == 1:
                return True
            else:
                return False
        except Exception as error:
            log.exception(f'Ошибка при записи в БД: {error}')
            return False

    def create_event(self, event):
        # Create event in database
        try:
            create = EventDB.create(
                title=event.title,
                date=event.date,
                attendees=event.attendees,
                status=event.status,
            )
            if create:
                return True
            else:
                return False
        except Exception as error:
            log.exception(f'Ошибка при записи в БД: {error}')
            return False

    def load_events(self, user):
        event_list = EventDB.select().where(EventDB.date > datetime.datetime.now())
        if event_list:
            events = {}
            for database_event in event_list:
                if database_event.status != 'archived' or user.moderator or user.admin:
                    event = Event(
                        title=database_event.title,
                        date=database_event.date,
                        attendees=database_event.attendees,
                        event_id=database_event.event_id,
                        status=database_event.status)
                    event_registrations = Registration.select().where(Registration.event == database_event)
                    if event_registrations:
                        users = {}
                        for reg in event_registrations:
                            users[reg.user.user_id] = {
                                'username': reg.user.username,
                                'roll': reg.roll,
                                'cancel': reg.cancel,
                            }
                        event.users = users
                    events[event.event_id] = event
            return events

    def close_event(self, event, user):
        if user.admin or user.moderator:
            database_event = EventDB.select().where(EventDB.event_id == event.event_id).get()
            database_event.status = 'closed'
            database_event.save()
            users_ids = sorted(event.users, key=lambda u: event.users[u]['roll'], reverse=True)
            active_users_id = []
            for user_id in users_ids:
                if not event.users[user_id]['cancel']:
                    active_users_id.append(user_id)
            win_id = []
            lose_id = []
            for num, user in enumerate(active_users_id):
                if event.attendees > num:
                    win_id.append(user)
                else:
                    lose_id.append(user)
            registrations = Registration.select().where(Registration.event == database_event)
            for registration in registrations:
                if registration.user.user_id in win_id and not registration.user.fix:
                    if registration.user.roll_multiplier > 0:
                        user = registration.user.get()
                        user.roll_multiplier -= 1
                        user.save()
                if registration.user.user_id in lose_id and not registration.user.fix:
                    user = registration.user.get()
                    user.roll_multiplier += 1
                    user.save()

    def delete_event(self, event, user):
        if user.admin or user.moderator:
            database_event = EventDB.select().where(EventDB.event_id == event.event_id).get()
            registrations = Registration.delete().where(Registration.event == database_event)
            registrations.execute()
            database_event.delete_instance()

    def archiving_event(self, event, user):
        if user.admin or user.moderator:
            database_event = EventDB.select().where(EventDB.event_id == event.event_id).get()
            database_event.status = 'archived'
            database_event.save()

    def registration(self, event, user, roll, cancel=False):
        database_event = EventDB.select().where(EventDB.event_id == event.event_id)
        database_user = UserDB.select().where(UserDB.user_id == user.user_id)
        registration = Registration.select().where(
            (Registration.user == database_user) & (Registration.event == database_event)
        )
        if registration:
            registration = registration.get()
            if registration.roll != roll or registration.cancel != cancel:
                registration.roll = roll
                registration.cancel = cancel
                if registration.save():
                    return True
                else:
                    return False

        else:
            registration = Registration.create(
                user=database_user,
                event=database_event,
                username=user.username,
                roll=roll,
                cancel=cancel,
            )
            if registration:
                return True
            else:
                return False


if __name__ == '__main__':
    base = DatabaseManager()
    UserDB.create_table(UserDB)
