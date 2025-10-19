"""Unit tests for JanusTextRoomPlugin."""

import unittest
import logging
import asyncio
import os
from urllib.parse import urljoin

from janus_client import (
    JanusTransport,
    JanusSession,
    JanusTextRoomPlugin,
    TextRoomError,
    TextRoomEventType,
)
from tests.util import async_test

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


class BaseTestClass:
    class TestClass(unittest.TestCase):
        server_url: str

        async def asyncSetUp(self) -> None:
            self.transport = JanusTransport.create_transport(
                base_url=self.server_url, api_secret=os.getenv("JANUS_API_SECRET", "")
            )
            await self.transport.connect()

        async def asyncTearDown(self) -> None:
            await self.transport.disconnect()
            await asyncio.sleep(0.250)

        async def attach_plugin(self) -> None:
            await self.asyncSetUp()
            logger.info("Testing create and destroy room")

            self.session = JanusSession(transport=self.transport)
            self.plugin = JanusTextRoomPlugin()

            await self.plugin.attach(session=self.session)

        async def detach_plugin(self) -> None:
            await self.plugin.destroy()
            await self.session.destroy()
            await self.asyncTearDown()

        @async_test
        async def test_textroom_plugin_attach(self):
            """Test attaching TextRoom plugin to session."""
            await self.asyncSetUp()
            logger.info("Testing TextRoom plugin attach")

            session = JanusSession(transport=self.transport)
            plugin = JanusTextRoomPlugin()

            await plugin.attach(session=session)

            self.assertIsNotNone(plugin.id)
            logger.info(f"Plugin attached with ID: {plugin.id}")

            await plugin.destroy()
            await session.destroy()
            await self.asyncTearDown()

        @async_test
        async def test_textroom_setup(self):
            """Test TextRoom setup (WebRTC connection initialization)."""
            await self.asyncSetUp()
            logger.info("Testing TextRoom setup")

            session = JanusSession(transport=self.transport)
            plugin = JanusTextRoomPlugin()

            await plugin.attach(session=session)
            await plugin.setup(timeout=30.0)

            self.assertIsNotNone(plugin._pc)
            logger.info("TextRoom setup completed successfully")

            await plugin.destroy()
            await session.destroy()
            await self.asyncTearDown()

        @async_test
        async def test_textroom_list_rooms(self):
            """Test listing available TextRooms."""
            await self.attach_plugin()

            rooms = await self.plugin.list_rooms()

            self.assertIsInstance(rooms, list)
            logger.info(f"Found {len(rooms)} rooms")

            await self.detach_plugin()

        @async_test
        async def test_textroom_create_and_destroy_room(self):
            """Test creating and destroying a TextRoom."""
            await self.attach_plugin()

            # Create a room
            room_id = await self.plugin.create_room(
                description="Test Room",
                is_private=False,
                history=10,
            )

            self.assertIsInstance(room_id, int)
            logger.info(f"Created room with ID: {room_id}")

            # Verify room exists in list
            rooms = await self.plugin.list_rooms()
            room_ids = [room["room"] for room in rooms]
            self.assertIn(room_id, room_ids)

            # Destroy the room
            await self.plugin.destroy_room(room=room_id)
            logger.info(f"Destroyed room {room_id}")

            # Verify room no longer exists
            rooms = await self.plugin.list_rooms()
            room_ids = [room["room"] for room in rooms]
            self.assertNotIn(room_id, room_ids)

            await self.detach_plugin()

        @async_test
        async def test_textroom_join_and_leave(self):
            """Test joining and leaving a TextRoom."""
            await self.attach_plugin()

            await self.plugin.setup(timeout=30.0)

            # Create a test room
            room_id = await self.plugin.create_room(
                description="Test Join Room",
                is_private=False,
            )
            logger.info(f"Created room {room_id}")

            # Join the room
            participants = await self.plugin.join_room(
                room=room_id,
                username="test_user",
                display="Test User",
            )

            self.assertIsInstance(participants, list)
            logger.info(f"Joined room {room_id}, participants: {len(participants)}")

            # List participants
            participants = await self.plugin.list_participants(room=room_id)
            usernames = [p["username"] for p in participants]
            self.assertIn("test_user", usernames)

            # Leave the room
            await self.plugin.leave_room(room=room_id)
            logger.info(f"Left room {room_id}")

            # Make sure not part of participants anymore
            participants = await self.plugin.list_participants(room=room_id)
            usernames = [p["username"] for p in participants]
            self.assertNotIn("test_user", usernames)

            # Clean up
            await self.plugin.destroy_room(room=room_id)

            await self.detach_plugin()

        @async_test
        async def test_textroom_send_message(self):
            """Test sending messages in a TextRoom."""
            await self.attach_plugin()

            await self.plugin.setup(timeout=30.0)

            # Create and join a room
            room_id = await self.plugin.create_room(
                description="Test Message Room",
                is_private=False,
            )

            await self.plugin.join_room(
                room=room_id,
                username="test_sender",
            )
            logger.info(f"Joined room {room_id}")

            # Send a message
            await self.plugin.send_message(
                room=room_id,
                text="Hello, TextRoom!",
                ack=True,
            )
            logger.info("Message sent successfully")

            # Clean up
            await self.plugin.leave_room(room=room_id)
            await self.plugin.destroy_room(room=room_id)

            await self.detach_plugin()

        @async_test
        async def test_textroom_event_handlers(self):
            """Test TextRoom event handlers."""
            await self.attach_plugin()

            # Track received events
            received_messages = []
            received_joins = []

            def on_message(data):
                received_messages.append(data)
                logger.info(f"Received message: {data.get('text', '')}")

            def on_join(data):
                received_joins.append(data)
                logger.info(f"User joined: {data.get('username', '')}")

            self.plugin.on_event(TextRoomEventType.MESSAGE, on_message)
            self.plugin.on_event(TextRoomEventType.JOIN, on_join)

            await self.plugin.setup(timeout=30.0)

            # Create and join a room
            room_id = await self.plugin.create_room(
                description="Test Event Room",
                is_private=False,
            )

            await self.plugin.join_room(
                room=room_id,
                username="test_user",
            )

            # Send a message
            await self.plugin.send_message(
                room=room_id,
                text="Test message",
                ack=True,
            )

            # Give some time for events to be processed
            await asyncio.sleep(1.0)

            # Verify event did run
            self.assertTrue(received_messages)
            self.assertTrue(received_joins)

            # Clean up
            await self.plugin.leave_room(room=room_id)
            await self.plugin.destroy_room(room=room_id)

            await self.detach_plugin()

        @async_test
        async def test_textroom_private_message(self):
            """Test sending private messages."""
            await self.asyncSetUp()
            logger.info("Testing private messages")

            # Create two sessions
            session1 = JanusSession(transport=self.transport)
            plugin1 = JanusTextRoomPlugin()

            session2 = JanusSession(transport=self.transport)
            plugin2 = JanusTextRoomPlugin()

            await plugin1.attach(session=session1)
            await plugin1.setup(timeout=30.0)

            await plugin2.attach(session=session2)
            await plugin2.setup(timeout=30.0)

            # Track messages received by user2
            received_messages = []

            def on_message(data):
                received_messages.append(data)
                logger.info(f"User2 received message: {data}")

            # Register message handler for user2
            plugin2.on_event(TextRoomEventType.MESSAGE, on_message)

            # Create a room
            room_id = await plugin1.create_room(
                description="Test Private Message Room",
                is_private=False,
            )

            # Both users join
            await plugin1.join_room(room=room_id, username="user1")
            await plugin2.join_room(room=room_id, username="user2")
            logger.info("Both users joined")

            # User1 sends private message to user2
            await plugin1.send_message(
                room=room_id,
                text="Private message",
                to="user2",
                ack=True,
            )
            logger.info("Private message sent")

            # Wait for message to be received
            await asyncio.sleep(1.0)

            # Verify message was received by user2
            self.assertEqual(
                len(received_messages), 1, "User2 should receive exactly one message"
            )

            message = received_messages[0]
            self.assertEqual(
                message.get("text"), "Private message", "Message text should match"
            )
            self.assertEqual(
                message.get("from"), "user1", "Message should be from user1"
            )
            self.assertTrue(
                message.get("whisper", False),
                "Message should be marked as whisper (private)",
            )
            logger.info("Verified that user2 received the private message")

            # Clean up
            await plugin1.leave_room(room=room_id)
            await plugin2.leave_room(room=room_id)
            await plugin1.destroy_room(room=room_id)

            await plugin1.destroy()
            await plugin2.destroy()
            await session1.destroy()
            await session2.destroy()
            await self.asyncTearDown()

        @async_test
        async def test_textroom_room_with_pin(self):
            """Test creating and joining a PIN-protected room."""
            await self.attach_plugin()

            await self.plugin.setup(timeout=30.0)

            # Create a PIN-protected room
            room_id = await self.plugin.create_room(
                description="PIN Protected Room",
                pin="1234",
                is_private=False,
            )
            logger.info(f"Created PIN-protected room {room_id}")

            # Join with correct PIN
            await self.plugin.join_room(
                room=room_id,
                username="test_user",
                pin="1234",
            )
            logger.info("Joined with correct PIN")

            await self.plugin.leave_room(room=room_id)

            # Try to join with wrong PIN (should fail)
            try:
                await self.plugin.join_room(
                    room=room_id,
                    username="test_user2",
                    pin="wrong",
                    timeout=5.0,
                )
                self.fail("Should have failed with wrong PIN")
            except (TextRoomError, asyncio.TimeoutError):
                logger.info("Correctly rejected wrong PIN")

            # Clean up
            await self.plugin.destroy_room(room=room_id, secret=None)

            await self.detach_plugin()

        @async_test
        async def test_textroom_message_history(self):
            """Test message history functionality."""
            await self.attach_plugin()

            await self.plugin.setup(timeout=30.0)

            # Create room with history
            room_id = await self.plugin.create_room(
                description="History Room",
                history=10,
                is_private=False,
            )

            # Join and send messages
            await self.plugin.join_room(room=room_id, username="user1")

            for i in range(3):
                await self.plugin.send_message(
                    room=room_id,
                    text=f"Message {i+1}",
                    ack=True,
                )

            logger.info("Sent 3 messages")
            await self.plugin.leave_room(room=room_id)

            # Track received history messages
            received_history = []

            def on_message(data):
                received_history.append(data)
                logger.info(f"Received history message: {data.get('text', '')}")

            # Register message handler before rejoining
            self.plugin.on_event(TextRoomEventType.MESSAGE, on_message)

            # Rejoin and check if history is received
            await self.plugin.join_room(
                room=room_id,
                username="user1",
                history=True,
            )
            logger.info("Rejoined room with history")

            # Wait for history messages to be delivered
            await asyncio.sleep(2.0)

            # Verify that we received the 3 messages from history
            self.assertEqual(
                len(received_history), 3, "Should receive 3 messages from history"
            )

            # Verify message content and order
            for i, msg in enumerate(received_history):
                expected_text = f"Message {i+1}"
                self.assertEqual(
                    msg.get("text"),
                    expected_text,
                    f"Message {i+1} text should match",
                )
                self.assertEqual(
                    msg.get("from"), "user1", f"Message {i+1} should be from user1"
                )

            logger.info("Verified message history received correctly")

            # Clean up
            await self.plugin.leave_room(room=room_id)
            await self.plugin.destroy_room(room=room_id)

            await self.detach_plugin()


class TestTransportHttp(BaseTestClass.TestClass):
    server_url = urljoin(
        os.getenv("JANUS_HTTP_URL", ""),
        os.getenv("JANUS_HTTP_BASE_PATH", ""),
    )


class TestTransportWebsocket(BaseTestClass.TestClass):
    server_url = os.getenv("JANUS_WS_URL", "")
