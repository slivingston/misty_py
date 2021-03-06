import asyncio
from typing import NamedTuple, Dict

import arrow

from misty_py.api import MistyAPI
from misty_py.subscriptions import SubPayload, SubType, Actuator, Sub
from misty_py.misty_ws import EventCallback, UnchangedValue
from misty_py.utils import async_run

__author__ = 'acushner'

api = MistyAPI()

questions_comments = '''
- documentation on how the websockets API actually acts is pretty fragmented
- sometimes, even though face recog is running, it just won't recognize faces. i have no idea why
    - i think it was an ephemeral issue with onboard sensors failing
    - rebooting helped
- how can i tell, easily, when face training is done?
'''


class Person(NamedTuple):
    name: str
    target_acquired_phrase: str
    theme_song: str

    async def on_find(self, api: MistyAPI):
        await api.movement.halt()
        print('first', arrow.utcnow())
        await api.audio.play(self.target_acquired_phrase, blocking=True)
        print('first done', arrow.utcnow())

        print('second', arrow.utcnow())
        await api.audio.play(self.theme_song, how_long_secs=6, blocking=True)
        print('second done', arrow.utcnow())


people: Dict[str, Person] = {}


def add_person(person: Person):
    people[person.name] = person


add_person(Person('sweettuse', 'sweettuse_recognized.mp3', 'price_is_right.mp3'))


# ======================================================================================================================


async def wait_one(sp: SubPayload):
    print('wait_one', sp)
    return True


async def _handle_head_movement(yaw):
    ecb = EventCallback(UnchangedValue())
    await api.movement.move_head(yaw=yaw)
    async with api.ws.sub_unsub(Actuator.yaw.sub, ecb, 400):
        await ecb


async def _handle_face_recognition(sp: SubPayload):
    print('face_rec', sp)
    person = people.pop(sp.data.message.personName, None)
    if person:
        print('found', person)
        await sp.sub_id.unsubscribe()
        await person.on_find(api)
        return True


async def _init_face_recognition() -> EventCallback:
    print('starting face recognition')
    await api.faces.start_recognition()
    eh = EventCallback(_handle_face_recognition)
    await api.ws.subscribe(SubType.face_recognition, eh)
    return eh


async def run():
    print('started')
    await asyncio.sleep(3)
    face_handler = await _init_face_recognition()
    await _handle_head_movement(200)
    await face_handler
    await api.faces.stop_recognition()
    print('done')


def __main():
    async_run(run())
    print('we did something')
    pass


if __name__ == '__main__':
    __main()
