import functools
import asyncio
import os
import time
from typing import cast

import base
from base import ServiceExport as export
import vcc
import redis.asyncio as redis
import aiohttp
import models
import peewee
import json


def timer(interval, func=None):
    if func == None:
        return functools.partial(timer, interval)

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        await asyncio.sleep(interval - time.time() % interval)
        while 1:
            asyncio.create_task(func(*args, **kwargs))
            await asyncio.sleep(interval - time.time() % interval)

    return wrapper


class Record(metaclass=base.ServiceMeta):
    async def record_worker(self):
        async for i in self._pubsub.listen():
            if i["type"] == "pmessage":
                channel = str(json.loads(i["data"])["chat"])
                await self._redis.lpush("record:" + channel, i["data"].decode())
                await self._redis.lpush("recordl:" + channel, len(i["data"]))

    @timer(5)
    async def flush_worker(self):
        _time = int(time.time())
        print(_time % 5)
        curser = 0
        while 1:
            curser, keys = await self._redis.scan(
                cursor=curser, match="record:*", count=1
            )
            list(map(lambda x: asyncio.create_task(self.do_flush(x, _time)), keys))
            if curser == 0:
                break

    async def do_flush(self, key, time):
        length = await self._redis.llen(key)  # Freeze thr length
        content_length = []
        key = key.decode()
        for i in range(length):
            a = key.replace("d", "dl")
            content_length.append(
                int(await self._redis.rpop(a))
            )  # record:x -> recordl:x
        filename = key.replace(":", "") + "-" + str(time)
        file = await self._vcc.rpc.file.new_object(
            name=filename, id=filename, bucket="record"
        )
        header: str = ",".join(list(map(lambda x: str(x), content_length))) + "\n"

        async def data_generator():
            yield header.encode("utf8")
            for i in range(length):
                data = (await self._redis.rpop(key)) + b"\n"
                yield data

        async with aiohttp.ClientSession() as session:
            res = await session.put(
                url=file[0],
                data=data_generator(),
                headers={
                    "Content-Length": str(
                        sum(content_length) + len(header) + len(content_length)
                    )
                },
            )

    async def _ainit(self):
        await self._vcc.__aenter__()
        await self._pubsub.psubscribe("messages")
        asyncio.get_event_loop().create_task(self.record_worker())
        return await self.flush_worker()

    @export(async_mode=True)
    async def query_record(self, chatid, time):
        if time > int(globals()["time"].time()):
            return []

        aligned_time = time - time % 5

        name_list: list[str] = await self._vcc.rpc.file.list_object_names(
            prefix=f"record{chatid}-", bucket="record"
        )
        records: list[tuple[str, str]] = await asyncio.gather(
            *[
                asyncio.create_task(
                    self._vcc.rpc.file.get_object_content(id=name, bucket="record")
                )
                for name in name_list
                if int(name[name.find("-") + 1 :]) > time
            ]
        )
        return [record[0].split("\n")[1:-1] for record in records]

    def __init__(self):
        self._vcc = vcc.RpcExchanger()
        self._redis = redis.Redis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost")
        )
        self._pubsub = self._redis.pubsub()
        # asyncio.get_event_loop().create_task(self._ainit())


if __name__ == "__main__":
    asyncio.set_event_loop(loop := asyncio.new_event_loop())
    server = base.RpcServiceFactory()
    service = Record()
    server.register(service)
    loop.create_task(server.aconnect())
    loop.create_task(service._ainit())
    loop.run_forever()
