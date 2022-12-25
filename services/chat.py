#!/usr/bin/env python

import datetime

from peewee import *

import base
import warnings
from login import User


db = SqliteDatabase("db.db")

class BaseModel(Model):
    class Meta:
        database = db

class Chat(BaseModel):
    id = BigAutoField(primary_key=True)
    name = CharField(max_length=20)


class ChatUser(BaseModel):
    id = BigAutoField(primary_key=True)
    user = ForeignKeyField(User, backref="chat_users")
    chat = ForeignKeyField(Chat, backref="chat_users")

class Main:
    def _get_user(self, username: str) -> User:
        try:
            return User.get(User.name == username)
        except:
            return None

    def chat_create(self, name: str) -> int:
        return Chat.create(name=name).id

    def chat_get_name(self, id: int) -> str | None:
        chat = Chat.get_or_none(id=id)
        if chat is None:
            return None
        return chat.name

    def chat_get_users(self, id: int) -> list[str]:
        chat = Chat.get_or_none(Chat.id == id)
        if chat is None:
            return []
        chat_users = chat.chat_users
        user_names = [chat_user.user.name for chat_user in chat_users]
        return user_names

    def chat_join(self, id: int, username: str) -> bool:
        try:
            chat = Chat.get(Chat.id == id)
            user = User.get(User.name == username)
            ChatUser.get_or_create(chat=chat, user=user)
            return True
        except:
            return False
    
    def chat_quit(self, id: int, username: str) -> bool:
        try:
            chat = Chat.get(Chat.id == id)
            user = User.get(User.name == username)
            chat_user = ChatUser.get_or_none(chat=chat, user=user)
            if chat_user is not None:
                chat_user.delete_instance()
                return True
            return False
        except:
            return False

    def chat_list(self) -> list[int]:
        warnings.warn(DeprecationWarning("chat_list is slow so that it shouldn't be used"))
        return [i.id for i in Chat.select()]
        

if __name__ == "__main__":
    db.create_tables([User, Chat, ChatUser])
    server = base.RpcServiceFactory()
    server.register(Main())
    server.connect()
