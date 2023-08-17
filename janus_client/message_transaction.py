import asyncio
import uuid
from typing import Dict, List, Union, Callable


def is_subset(dict_1: Dict, dict_2: Dict) -> bool:
    """Check if dict_2 is subset of dict_1 recursively

    Only checks dict, str or int type in dict_2
    """
    if not isinstance(dict_1, dict):
        raise TypeError(f"dict_1 must be a dictionary: {dict_1}")

    if not isinstance(dict_2, dict):
        raise TypeError(f"dict_2 must be a dictionary: {dict_2}")

    if not dict_2:
        return True

    for key_2, val_2 in dict_2.items():
        if not (
            isinstance(val_2, dict) or isinstance(val_2, str) or isinstance(val_2, int)
        ):
            # If not these few types, then only need
            # key_2 to be in dict_1
            if key_2 in dict_1:
                continue
            else:
                return False

        # Need to check values
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
        self,
        matcher: Union[Dict, Callable] = lambda *args, **kwargs: True,
        timeout: Union[float, None] = None,
    ) -> Dict:
        if not (isinstance(matcher, dict) or callable(matcher)):
            raise TypeError(f"matcher must be callable or dictionary: {matcher}")

        _matcher: Callable
        if callable(matcher):
            # matcher is a function
            _matcher = matcher
        else:
            # matcher is a dict
            def dict_matcher(msg: dict) -> bool:
                return is_subset(msg, matcher)

            _matcher = dict_matcher

        # Try to find message in saved messages
        for msg in self.__msg_all:
            if _matcher(msg):
                return msg

        # Wait in queue until a matching message is found
        msg = await asyncio.wait_for(self.__msg_in.get(), timeout=timeout)
        # Always save received messages
        self.__msg_all.append(msg)

        while not _matcher(msg):
            msg = await asyncio.wait_for(self.__msg_in.get(), timeout=timeout)
            self.__msg_all.append(msg)

        return msg

    async def on_done(self) -> None:
        pass

    async def done(self) -> None:
        """Must call this when finish using to release resources"""
        await self.on_done()
