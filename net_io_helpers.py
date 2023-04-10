import asyncio

from abc import ABC

from constants_and_variables import ENCODING_TYPE, READ_TIMEOUT

__all__ = ["IOHelper", "PlainIOHelper"]


class IOHelper(ABC):
    def __init__(self, *params):
        pass

    def send(self, data):
        pass

    def receive(self):
        pass


class PlainIOHelper(IOHelper):
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter

    def __init__(self, *params):
        super().__init__(*params)
        self.reader: asyncio.StreamReader = params[0]
        self.writer: asyncio.StreamWriter = params[1]

    async def send(self, data):
        encoded_data = data.encode(encoding=ENCODING_TYPE)
        self.writer.write(len(encoded_data).to_bytes(4, 'big'))
        self.writer.write(encoded_data)
        await self.writer.drain()

    async def receive(self):
        data_len = await asyncio.wait_for(self.reader.read(4), READ_TIMEOUT)

        return await self.reader.read(int.from_bytes(data_len, 'big'))
