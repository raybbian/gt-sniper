from peewee import (
    BooleanField,
    ForeignKeyField,
    SqliteDatabase,
    Model,
    IntegerField,
    CharField,
    DateTimeField,
    SQL,
)
import datetime, os

db = SqliteDatabase("database.db")


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    discord_id = IntegerField(unique=True)


class Course(BaseModel):
    semester = CharField()
    crn = IntegerField()
    name = CharField()
    subject_code = CharField()
    course_number = IntegerField()
    section = CharField()


class HitListEntry(BaseModel):
    user = ForeignKeyField(User, backref="entries")
    course = ForeignKeyField(Course, backref="desired_by")
    created_date = DateTimeField(default=datetime.datetime.now)
    notify = BooleanField(default=True)


def init_database():
    if not os.path.exists("database.db"):
        print("Created database!")
        db.connect()
        db.create_tables([User, Course, HitListEntry])
    else:
        print("Database already exists!")
