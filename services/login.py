#!/usr/bin/env python

import hmac
import random
import string
import json

from peewee import *

import base
import models

db = models.get_database()

User=models.bind_model(models.User,db)



def random_string(length:int)->str:
    return "".join(
        random.SystemRandom().choice(string.ascii_letters + string.digits)
        for _ in range(length)
    )
class Main:
    @db.atomic()
    def login(self, username: str, password: str) -> int | None:
        if username == "system":
            return None
        user = User.get_or_none(User.name == username)
        if user is None:
            return None
        if not user.login:
            return None
        hashed_password = hmac.new(user.salt.encode(), password.encode(), "sha512").hexdigest()
        if hashed_password!=user.password:
            return None
        return user.id
    
    @db.atomic()
    def register(self, username: str, password: str) -> bool:
        if username == "system":
            return False
        hashed_password = hmac.new((salt:=random_string(10)).encode(), password.encode(), "sha512").hexdigest()
        try:
            User(name=username, password=hashed_password,salt=salt).save()
            return True
        except:
            return False

    @db.atomic()
    def get_name(self, id: int) -> str | None:
        user = User.get_or_none(id=id)
        if user is None:
            return None
        return user.name

if __name__ == "__main__":
    db.create_tables([User])
    server = base.RpcServiceFactory("login")
    server.register(Main())
    server.connect()
