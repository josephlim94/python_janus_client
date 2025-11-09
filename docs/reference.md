# API Reference

Complete API reference for all classes, methods, and types in the Python Janus Client library.

## Session Classes

### JanusSession

::: janus_client.session.JanusSession
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true

### PluginAttachFail Exception

::: janus_client.session.PluginAttachFail
    options:
      show_root_heading: true
      show_source: false
      docstring_section_style: table

## Plugin Classes

### Base Plugin Class

::: janus_client.plugin_base.JanusPlugin
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true

### EchoTest Plugin

::: janus_client.plugin_echotest.JanusEchoTestPlugin
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true

### VideoCall Plugin

::: janus_client.plugin_video_call.JanusVideoCallPlugin
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true

#### VideoCallError Exception

::: janus_client.plugin_video_call.VideoCallError
    options:
      show_root_heading: true
      show_source: false
      docstring_section_style: table

#### VideoCallEventType Enum

::: janus_client.plugin_video_call.VideoCallEventType
    options:
      show_root_heading: true
      show_source: false
      docstring_section_style: table

### VideoRoom Plugin

::: janus_client.plugin_video_room.JanusVideoRoomPlugin
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true

#### VideoRoomError Exception

::: janus_client.plugin_video_room.VideoRoomError
    options:
      show_root_heading: true
      show_source: false
      docstring_section_style: table

#### VideoRoomEventType Enum

::: janus_client.plugin_video_room.VideoRoomEventType
    options:
      show_root_heading: true
      show_source: false
      docstring_section_style: table

#### ParticipantType Enum

::: janus_client.plugin_video_room.ParticipantType
    options:
      show_root_heading: true
      show_source: false
      docstring_section_style: table

### TextRoom Plugin

::: janus_client.plugin_textroom.JanusTextRoomPlugin
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true

#### TextRoomError Exception

::: janus_client.plugin_textroom.TextRoomError
    options:
      show_root_heading: true
      show_source: false
      docstring_section_style: table

#### TextRoomEventType Enum

::: janus_client.plugin_textroom.TextRoomEventType
    options:
      show_root_heading: true
      show_source: false
      docstring_section_style: table

## Transport Classes

### Base Transport Class

::: janus_client.transport.JanusTransport
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true

### HTTP Transport

::: janus_client.transport_http.JanusTransportHTTP
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true

### WebSocket Transport

::: janus_client.transport_websocket.JanusTransportWebsocket
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true
