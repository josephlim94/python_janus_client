import unittest
import logging
import asyncio
import os
from urllib.parse import urljoin
import json

from aiortc.contrib.media import MediaPlayer

from janus_client import (
    JanusTransport,
    JanusSession,
    JanusVideoRoomPlugin,
    VideoRoomError,
    VideoRoomEventType,
    ParticipantType,
)
from tests.util import async_test

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


class BaseTestClass:
    class TestClass(unittest.TestCase):
        server_url: str
        public_test_videos: dict

        @classmethod
        def setUpClass(cls):
            with open("./tests/public_test_videos.json", "r", encoding="utf-8") as file:
                cls.public_test_videos = json.load(file)

        def getVideoUrlByIndex(self, index: int):
            return self.public_test_videos["categories"][0]["videos"][index]["sources"][
                0
            ]

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
            logger.info("Attaching VideoRoom plugin")

            self.session = JanusSession(transport=self.transport)
            self.plugin = JanusVideoRoomPlugin()

            await self.plugin.attach(session=self.session)

        async def detach_plugin(self) -> None:
            await self.plugin.destroy()
            await self.session.destroy()
            await self.asyncTearDown()

        @async_test
        async def test_list_rooms(self):
            """Test listing available VideoRooms."""
            await self.attach_plugin()

            rooms = await self.plugin.list_rooms()

            self.assertIsInstance(rooms, list)
            logger.info(f"Found {len(rooms)} rooms")

            await self.detach_plugin()

        @async_test
        async def test_create_and_destroy_room(self):
            """Test creating and destroying a VideoRoom."""
            await self.attach_plugin()

            # Create a room
            room_id = await self.plugin.create_room(
                description="Test VideoRoom",
                is_private=False,
                publishers=3,
                bitrate=128000,
                fir_freq=10,
            )

            with self.assertRaises(VideoRoomError) as context:
                # Creating room with only same name is fine, it will auto
                # generate a different room ID
                await self.plugin.create_room(
                    room_id=room_id,
                    description="Test VideoRoom",
                    is_private=False,
                    publishers=3,
                    bitrate=128000,
                    fir_freq=10,
                )

            self.assertIn("already exists", context.exception.error_message)
            logger.info("Correctly fail to create room with same room ID")

            self.assertIsInstance(room_id, int)
            logger.info(f"Created room with ID: {room_id}")

            # Verify room exists
            exists = await self.plugin.exists(room_id)
            self.assertTrue(exists)

            # Verify room appears in list
            rooms = await self.plugin.list_rooms()
            room_ids = [room["room"] for room in rooms]
            self.assertIn(room_id, room_ids)

            # Destroy the room
            await self.plugin.destroy_room(room_id=room_id)
            logger.info(f"Destroyed room {room_id}")

            with self.assertRaises(VideoRoomError) as context:
                await self.plugin.destroy_room(room_id=room_id)

            self.assertIn("No such room", context.exception.error_message)
            logger.info("Correctly fail to destroy room with same room ID")

            # Verify room no longer exists
            exists = await self.plugin.exists(room_id)
            self.assertFalse(exists)

            await self.detach_plugin()

        @async_test
        async def test_create_room_with_secret(self):
            """Test creating a room with secret and PIN."""
            await self.attach_plugin()

            # Create a room with secret and PIN
            room_id = await self.plugin.create_room(
                description="Secret Room",
                secret="room_secret",
                pin="1234",
                is_private=True,
            )

            logger.info(f"Created secret room {room_id}")

            with self.assertRaises(VideoRoomError) as context:
                await self.plugin.destroy_room(room_id=room_id)

            self.assertIn(
                "Missing mandatory element (secret)", context.exception.error_message
            )
            logger.info("Correctly fail to destroy room without secret")

            # Destroy with secret
            await self.plugin.destroy_room(room_id=room_id, secret="room_secret")
            logger.info("Destroyed secret room")

            await self.detach_plugin()

        @async_test
        async def test_list_participants(self):
            """Test listing participants in a room."""
            await self.attach_plugin()

            # Create a room
            room_id = await self.plugin.create_room(
                description="Participants Test Room",
                is_private=False,
            )

            # Initially no participants
            participants = await self.plugin.list_participants(room_id)
            self.assertListEqual(participants, [])
            logger.info(f"Room {room_id} has {len(participants)} participants")

            # Clean up
            await self.plugin.destroy_room(room_id=room_id)

            await self.detach_plugin()

        @async_test
        async def test_join_as_publisher(self):
            """Test joining a room as a publisher."""
            await self.attach_plugin()

            # Create a room
            room_id = await self.plugin.create_room(
                description="Publisher Test Room",
                is_private=False,
            )

            # Join as publisher
            join_result = await self.plugin.join_as_publisher(
                room_id=room_id,
                display="Test Publisher",
            )

            self.assertIsInstance(join_result, dict)
            self.assertEqual(self.plugin.participant_type, ParticipantType.PUBLISHER)
            self.assertEqual(join_result["room"], room_id)
            self.assertIsNotNone(self.plugin.publisher_id)
            self.assertIsNotNone(self.plugin.private_id)
            logger.info(
                f"Joined room {room_id} as publisher {self.plugin.publisher_id}"
            )

            # Check publisher is in participants list
            participants = await self.plugin.list_participants(room_id)
            participant_found = next(
                (p for p in participants if p["id"] == self.plugin.publisher_id), None
            )
            if not participant_found:
                # Do this for help with type hint
                self.fail("Participant not found")
            self.assertEqual(participant_found["display"], "Test Publisher")
            self.assertEqual(len(participants), 1)

            # Leave the room
            await self.plugin.leave()
            self.assertIsNone(self.plugin.participant_type)
            self.assertIsNone(self.plugin.room_id)
            logger.info("Left the room")

            # Clean up
            await self.plugin.destroy_room(room_id=room_id)

            await self.detach_plugin()

        @async_test
        async def test_join_with_specific_id(self):
            """Test joining with a specific publisher ID."""
            await self.attach_plugin()

            # Create a room
            room_id = await self.plugin.create_room(
                description="Specific ID Test Room",
                is_private=False,
            )

            # Join with specific publisher ID
            publisher_id = 12345
            join_result = await self.plugin.join_as_publisher(
                room_id=room_id,
                publisher_id=publisher_id,
                display="Specific ID Publisher",
            )

            self.assertEqual(join_result["id"], publisher_id)

            # Leave and clean up
            await self.plugin.leave()
            await self.plugin.destroy_room(room_id=room_id)

            await self.detach_plugin()

        @async_test
        async def test_publish(self):
            """Test publishing."""
            await self.attach_plugin()

            # Create a room
            room_id = await self.plugin.create_room(
                description="Publisher Test Room",
                is_private=False,
            )

            # Join as publisher
            join_result = await self.plugin.join_as_publisher(
                room_id=room_id,
                display="Test Publisher",
            )
            self.assertEqual(join_result["room"], room_id)

            # Try to publish without joining
            player = MediaPlayer(self.getVideoUrlByIndex(0))
            publish_result = await self.plugin.publish(player=player)
            self.assertEqual(publish_result["configured"], "ok")

            # It is only really published with webrtc is up
            await self.plugin.webrtcup_event.wait()

            await self.plugin.unpublish()

            # Leave the room
            await self.plugin.leave()
            self.assertIsNone(self.plugin.participant_type)
            self.assertIsNone(self.plugin.room_id)
            logger.info("Left the room")

            # Clean up
            await self.plugin.destroy_room(room_id=room_id)

            await self.detach_plugin()

        @async_test
        async def test_publish_without_join(self):
            """Test that publishing fails without joining as publisher first."""
            await self.attach_plugin()

            # Try to publish without joining
            player = MediaPlayer(self.getVideoUrlByIndex(0))
            with self.assertRaises(VideoRoomError) as context:
                await self.plugin.publish(player=player)

            self.assertTrue(
                any(
                    [
                        "Invalid request on unconfigured participant"
                        in context.exception.error_message,
                        "Must join as publisher" in context.exception.error_message,
                    ]
                )
            )
            logger.info("Correctly rejected publish without join")

            await self.detach_plugin()

        @async_test
        async def test_event_handlers(self):
            """Test VideoRoom event handlers."""
            await self.attach_plugin()

            # Track received events
            received_events = []

            def on_joined(data):
                received_events.append(("joined", data))
                logger.info(f"Received joined event: {data}")

            def on_publishers(data):
                received_events.append(("publishers", data))
                logger.info(f"Received publishers event: {data}")

            # Register event handlers
            self.plugin.on_event(VideoRoomEventType.JOINED, on_joined)
            self.plugin.on_event(VideoRoomEventType.PUBLISHERS, on_publishers)

            # Create a room and join
            room_id = await self.plugin.create_room(
                description="Event Test Room",
                is_private=False,
            )

            await self.plugin.join_as_publisher(
                room_id=room_id,
                display="Event Test Publisher",
            )

            # Give some time for events to be processed
            await asyncio.sleep(1.0)

            # Verify events were received
            self.assertTrue(len(received_events) == 1)
            event_types = [event[0] for event in received_events]
            self.assertIn("joined", event_types)

            # Clean up
            await self.plugin.leave()
            await self.plugin.destroy_room(room_id=room_id)

            await self.detach_plugin()

        @async_test
        async def test_configure_publisher(self):
            """Test configuring publisher settings."""
            await self.attach_plugin()

            # Create room and join as publisher
            room_id = await self.plugin.create_room(
                description="Configure Test Room",
                is_private=False,
            )

            await self.plugin.join_as_publisher(
                room_id=room_id,
                display="Original Display",
            )

            # Configure publisher settings
            await self.plugin.configure(
                bitrate=256000,
                display="Updated Display",
                keyframe=True,
            )

            # Check publisher is in participants list
            participants = await self.plugin.list_participants(room_id)
            participant_found = next(
                (p for p in participants if p["id"] == self.plugin.publisher_id), None
            )
            if not participant_found:
                # Do this for help with type hint
                self.fail("Participant not found")
            self.assertEqual(participant_found["display"], "Updated Display")
            self.assertEqual(len(participants), 1)

            # Clean up
            await self.plugin.leave()
            await self.plugin.destroy_room(room_id=room_id)

            await self.detach_plugin()

        @async_test
        async def test_subscribe_to_non_existent_feed(self):
            """Test subscribing to a non-existent feed."""
            await self.attach_plugin()

            # Create a room
            room_id = await self.plugin.create_room(
                description="Subscribe Test Room",
                is_private=False,
            )

            # For this test, we'll simulate subscribing to a non-existent publisher
            # This should fail gracefully
            streams = [{"feed": 99999}]  # Non-existent publisher

            with self.assertRaises(VideoRoomError) as context:
                await self.plugin.subscribe_to_publisher(
                    room_id=room_id,
                    streams=streams,
                    timeout=5.0,
                )

            self.assertIn("No such feed ", context.exception.error_message)

            # Clean up
            if self.plugin.participant_type is not None:
                await self.plugin.leave()
            await self.plugin.destroy_room(room_id=room_id)

            await self.detach_plugin()

        # @async_test
        # async def test_subscribe_to_publisher(self):
        #     """Test subscribing to a publisher (basic test without media)."""
        #     await self.attach_plugin()

        #     # Create a room
        #     room_id = await self.plugin.create_room(
        #         description="Subscribe Test Room",
        #         is_private=False,
        #     )

        #     # For this test, we'll simulate subscribing to a non-existent publisher
        #     # This should fail gracefully
        #     streams = [{"feed": 99999}]  # Non-existent publisher

        #     try:
        #         await self.plugin.subscribe_to_publisher(
        #             room_id=room_id,
        #             streams=streams,
        #             timeout=5.0,
        #         )
        #         self.fail("Subscription should fail")
        #     except (VideoRoomError, asyncio.TimeoutError) as e:
        #         logger.info(f"Subscription failed as expected: {e}")

        #     # Clean up
        #     if self.plugin.participant_type is not None:
        #         await self.plugin.leave()
        #     await self.plugin.destroy_room(room_id=room_id)

        #     await self.detach_plugin()

        @async_test
        async def test_kick_participant(self):
            """Test kicking a participant (admin function)."""
            await self.attach_plugin()

            # Create a room with secret for admin functions
            room_id = await self.plugin.create_room(
                description="Kick Test Room",
                secret="admin_secret",
                is_private=False,
            )

            with self.assertRaises(VideoRoomError) as context:
                await self.plugin.kick_participant(
                    room_id=room_id,
                    participant_id=99999,
                    secret="admin_secret",
                    timeout=5.0,
                )

            self.assertIn("No such user 99999 in room ", context.exception.error_message)

            # Clean up
            await self.plugin.destroy_room(room_id=room_id, secret="admin_secret")

            await self.detach_plugin()

        @async_test
        async def test_moderate_participant(self):
            """Test moderating a participant (admin function)."""
            await self.attach_plugin()

            # Create a room with secret for admin functions
            room_id = await self.plugin.create_room(
                description="Moderate Test Room",
                secret="admin_secret",
                is_private=False,
            )

            with self.assertRaises(VideoRoomError) as context:
                await self.plugin.moderate_participant(
                    room_id=room_id,
                    participant_id=99999,
                    mid="0",
                    mute=True,
                    secret="admin_secret",
                    timeout=5.0,
                )

            self.assertIn("No such user 99999 in room ", context.exception.error_message)

            # Clean up
            await self.plugin.destroy_room(room_id=room_id, secret="admin_secret")

            await self.detach_plugin()

        @async_test
        async def test_create_multiple_rooms(self):
            """Test creating and managing multiple rooms."""
            await self.attach_plugin()

            # Create multiple rooms
            room_ids = []
            for i in range(3):
                room_id = await self.plugin.create_room(
                    description=f"Multi Room {i+1}",
                    is_private=False,
                )
                room_ids.append(room_id)
                logger.info(f"Created room {room_id}")

            # Verify all rooms exist
            for room_id in room_ids:
                exists = await self.plugin.exists(room_id)
                self.assertTrue(exists)

            # List rooms and verify they're all there
            rooms = await self.plugin.list_rooms()
            listed_room_ids = [room["room"] for room in rooms]
            for room_id in room_ids:
                self.assertIn(room_id, listed_room_ids)

            # Clean up all rooms
            for room_id in room_ids:
                await self.plugin.destroy_room(room_id=room_id)
                logger.info(f"Destroyed room {room_id}")

            await self.detach_plugin()

        @async_test
        async def test_room_configuration_options(self):
            """Test creating rooms with various configuration options."""
            await self.attach_plugin()

            # Create room with all options
            room_id = await self.plugin.create_room(
                description="Full Config Room",
                secret="test_secret",
                pin="9876",
                is_private=True,
                publishers=6,
                bitrate=512000,
                fir_freq=5,
                audiocodec="opus,pcmu",
                videocodec="vp8,h264",
                record=False,
                permanent=False,
            )

            self.assertIsInstance(room_id, int)
            logger.info(f"Created fully configured room {room_id}")

            # Verify room exists
            exists = await self.plugin.exists(room_id)
            self.assertTrue(exists)

            # Clean up
            await self.plugin.destroy_room(room_id=room_id, secret="test_secret")

            await self.detach_plugin()

        @async_test
        async def test_error_handling(self):
            """Test error handling for invalid operations."""
            await self.attach_plugin()

            # Try to destroy non-existent room
            try:
                await self.plugin.destroy_room(room_id=99999, timeout=5.0)
                self.fail("Should have raised VideoRoomError")
            except (VideoRoomError, asyncio.TimeoutError):
                logger.info("Correctly handled non-existent room destruction")

            # Try to join non-existent room
            try:
                await self.plugin.join_as_publisher(room_id=99999, timeout=5.0)
                self.fail("Should have raised VideoRoomError")
            except (VideoRoomError, asyncio.TimeoutError):
                logger.info("Correctly handled joining non-existent room")

            # Try to list participants of non-existent room
            try:
                await self.plugin.list_participants(room_id=99999, timeout=5.0)
                self.fail("Should have raised VideoRoomError")
            except (VideoRoomError, asyncio.TimeoutError):
                logger.info(
                    "Correctly handled listing participants of non-existent room"
                )

            await self.detach_plugin()

        @async_test
        async def test_state_management(self):
            """Test plugin state management."""
            await self.attach_plugin()

            # Initial state
            self.assertIsNone(self.plugin.participant_type)
            self.assertIsNone(self.plugin.room_id)
            self.assertIsNone(self.plugin.publisher_id)
            self.assertIsNone(self.plugin.private_id)
            self.assertIsNone(self.plugin.display_name)
            self.assertFalse(self.plugin.is_publishing)

            # Create room and join
            room_id = await self.plugin.create_room(
                description="State Test Room",
                is_private=False,
            )

            await self.plugin.join_as_publisher(
                room_id=room_id,
                display="State Test User",
            )

            # Verify state after join
            self.assertEqual(self.plugin.participant_type, ParticipantType.PUBLISHER)
            self.assertEqual(self.plugin.room_id, room_id)
            self.assertEqual(self.plugin.display_name, "State Test User")
            self.assertIsNotNone(self.plugin.publisher_id)
            self.assertIsNotNone(self.plugin.private_id)
            self.assertFalse(self.plugin.is_publishing)  # Not publishing yet

            # Leave room
            await self.plugin.leave()

            # Verify state after leave
            self.assertIsNone(self.plugin.participant_type)
            self.assertIsNone(self.plugin.room_id)
            self.assertIsNone(self.plugin.publisher_id)
            self.assertIsNone(self.plugin.private_id)
            self.assertIsNone(self.plugin.display_name)
            self.assertFalse(self.plugin.is_publishing)

            # Clean up
            await self.plugin.destroy_room(room_id=room_id)

            await self.detach_plugin()


class TestTransportHttp(BaseTestClass.TestClass):
    server_url = urljoin(
        os.getenv("JANUS_HTTP_URL", ""),
        os.getenv("JANUS_HTTP_BASE_PATH", ""),
    )


class TestTransportWebsocket(BaseTestClass.TestClass):
    server_url = os.getenv("JANUS_WS_URL", "")
