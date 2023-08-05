import logging

import aiohttp

from .transport import JanusTransport


logger = logging.getLogger(__name__)


class JanusTransportHTTP(JanusTransport):
    """Janus transport through HTTP

    Manage Sessions and Transactions
    """

    def __build_url(self, session_id: int = None, handle_id: int = None) -> str:
        url = self.base_url

        if session_id:
            url = f"{url}/{session_id}"

            if handle_id:
                url = f"{url}/{handle_id}"

        return url

    async def info(self) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/info") as response:
                return await response.json()

    async def _send(
        self,
        message: dict,
    ) -> None:
        session_id = message.get("session_id")
        handle_id = message.get("handle_id")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=self.__build_url(session_id=session_id, handle_id=handle_id),
                json=message,
            ) as response:
                print("Status:", response.status)
                print("Content-type:", response.headers["content-type"])

                response.raise_for_status()

                response = await response.json()

                if "error" in response:
                    raise Exception(response)

                # There must be a transaction ID
                response_transaction_id = response["transaction"]

                # Fake receive
                # We will immediately get a response in the HTTP response, so need
                # to put this into the queue
                await self.put_response(
                    transaction_id=response_transaction_id, response=response
                )

    async def receive(self):
        pass


JanusTransport.register_transport(
    protocol_matcher=lambda _: True, transport_cls=JanusTransportHTTP
)
