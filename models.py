from peewee import *

standup_db = SqliteDatabase('standup.db')


class Event:
    def __init__(self, title, date, attendees, event_id=None, status='open'):
        self.event_id = event_id
        self.title = title
        self.date = date
        self.attendees = attendees
        self.users = {}
        self.status = status


class User:
    def __init__(self, user_id, username, db):
        self.user_id = user_id
        self.username = username
        self.roll_multiplier = 0
        self.reroll = 0
        self.db = db
        self.admin = False
        self.moderator = False
        self.ban = False
        self.fix = False

    def save(self):
        self.db.save_user(self)

    def load(self):
        self.db.load_user(self)


# Event class for database
class EventDB(Model):
    event_id = AutoField()
    title = CharField()
    date = DateField()
    attendees = IntegerField()
    status = CharField()

    class Meta:
        database = standup_db


# User class for database
class UserDB(Model):
    user_id = IntegerField(unique=True)
    username = CharField()
    roll_multiplier = IntegerField()
    reroll = IntegerField()
    admin = BooleanField()
    moderator = BooleanField()
    ban = BooleanField()
    fix = BooleanField()

    class Meta:
        database = standup_db


# User class for database
class Registration(Model):
    id = AutoField()
    user = ForeignKeyField(UserDB, backref='registration')
    event = ForeignKeyField(EventDB, backref='registration')
    username = CharField()
    roll = IntegerField()
    cancel = BooleanField()

    class Meta:
        database = standup_db


if __name__ == '__main__':
    standup_db.connect()
    standup_db.create_tables([EventDB, UserDB, Registration])
