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
    def chat_create(self, name: str) -> int:
        return Chat.create(name=name).id

    def chat_get_name(self, id: int) -> str | None:
        chat = Chat.get_or_none(id=id)
        if chat is None:
            return None
        return chat.name

    def chat_get_users(self, id: int) -> list[int]:
        chat = Chat.get_or_none(Chat.id == id)
        if chat is None:
            return []
        chat_users = chat.chat_users
        user_names = [chat_user.user.id for chat_user in chat_users]
        return user_names

    def chat_join(self, chat_id: int, user_id: int) -> bool:
        try:
            chat = Chat.get_by_id(chat_id)
            user = User.get_by_id(user_id)
            
            ChatUser.get_or_create(chat=chat, user=user)
            return True
        except:
            return False
    
    def chat_quit(self, chat_id: int, user_id: int) -> bool:
        try:
            chat = Chat.get_by_id(chat_id)
            user = User.get_by_id(user_id)
            chat_user = ChatUser.get(chat=chat, user=user)
            chat_user.delete_instance()
            return True
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
