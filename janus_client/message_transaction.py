import asyncio
import uuid
from typing import Dict, List, Union


def is_subset(dict_1: Dict, dict_2: Dict) -> bool:
    """Check if dict_2 is subset of dict_1 recursively

    Only checks dict or str type in dict_2
    """
    if not isinstance(dict_1, dict):
        raise Exception(f"dict_1 must be a dictionary: {dict_1}")

    if not isinstance(dict_2, dict):
        return True

    if not dict_2:
        return True

    for key_2, val_2 in dict_2.items():
        val_1 = dict_1.get(key_2, None)

        # Simple compare
        if val_1 == val_2:
            continue

        # Now val_2 can be another dict
        if isinstance(val_1, dict) and isinstance(val_2, dict):
            if is_subset(val_1, val_2):
                continue
            else:
                return False

        # key_2: val_2 is not in dict_1, so False
        return False

    # All of dict_2 is found in dict_1
    return True


class MessageTransaction:
    __id: str
    __msg_all: List[Dict]
    __msg_in: asyncio.Queue

    def __init__(self) -> None:
        self.__id = uuid.uuid4().hex
        self.__msg_all = []
        self.__msg_in = asyncio.Queue()

    @property
    def id(self) -> str:
        return self.__id

    def put_msg(self, message: Dict) -> None:
        # Queue is never full
        self.__msg_in.put_nowait(message)

    async def get(
        self, dict_matcher: Dict = {}, timeout: Union[float, None] = None
    ) -> Dict:
        # Try to find message in saved messages
        for msg in self.__msg_all:
            if is_subset(msg, dict_matcher):
                return msg

        # Wait in queue until a matching message is found
        msg = await asyncio.wait_for(self.__msg_in.get(), timeout=timeout)
        # Always save received messages
        self.__msg_all.append(msg)

        while not is_subset(msg, dict_matcher):
            msg = await asyncio.wait_for(self.__msg_in.get(), timeout=timeout)
            self.__msg_all.append(msg)

        return msg

    async def on_done(self):
        pass
