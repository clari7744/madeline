CREATE TABLE
    IF NOT EXISTS zones (
        zone_name TEXT NOT NULL,
        description TEXT DEFAULT NULL,
        PRIMARY KEY (zone_name)
    );

CREATE TABLE
    IF NOT EXISTS rooms (
        room_name TEXT NOT NULL,
        zone TEXT NOT NULL REFERENCES zones (zone_name) ON DELETE CASCADE ON UPDATE CASCADE,
        description TEXT DEFAULT NULL,
        color INTEGER DEFAULT NULL,
        locked BOOLEAN NOT NULL DEFAULT FALSE CHECK (locked IN (0, 1)),
        PRIMARY KEY (room_name)
    );

CREATE TABLE
    IF NOT EXISTS connections (
        room TEXT NOT NULL REFERENCES rooms (room_name) ON DELETE CASCADE ON UPDATE CASCADE,
        connected_to TEXT NOT NULL REFERENCES rooms (room_name) ON DELETE CASCADE ON UPDATE CASCADE,
        direction TEXT NOT NULL CHECK (
            direction IN ('north', 'south', 'east', 'west', 'up', 'down')
        ),
        hidden BOOLEAN NOT NULL DEFAULT FALSE CHECK (hidden IN (0, 1)),
        PRIMARY KEY (room, connected_to)
    );

CREATE TABLE
    IF NOT EXISTS players (
        channel_id INTEGER NOT NULL,
        short_name TEXT NOT NULL,
        full_name TEXT NOT NULL,
        notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE CHECK (notifications_enabled IN (0, 1)),
        emoji_id INTEGER DEFAULT NULL,
        appearance TEXT DEFAULT NULL,
        action TEXT DEFAULT NULL,
        subtle TEXT DEFAULT NULL,
        location TEXT NOT NULL REFERENCES rooms (room_name) ON DELETE CASCADE ON UPDATE CASCADE,
        following INTEGER DEFAULT NULL REFERENCES players (channel_id) ON DELETE SET NULL,
        PRIMARY KEY (channel_id)
    );

CREATE TABLE
    IF NOT EXISTS roleplay_messages (
        original_message_id INTEGER NOT NULL,
        received_message_id INTEGER NOT NULL,
        sent_by INTEGER NOT NULL REFERENCES players (channel_id) ON DELETE CASCADE ON UPDATE CASCADE,
        sent_to INTEGER NOT NULL REFERENCES players (channel_id) ON DELETE CASCADE ON UPDATE CASCADE,
        sent_in_room TEXT NOT NULL REFERENCES rooms (room_name) ON DELETE CASCADE ON UPDATE CASCADE,
        updated_at TIMESTAMP NOT NULL,
        message_content TEXT NOT NULL,
        message_type TEXT NOT NULL CHECK (message_type IN ('whisper', 'shout', 'rp')),
        PRIMARY KEY (original_message_id, sent_to)
    )

-- in theory, roleplay_messages can also be done with two tables,
-- roleplay_messages & crossposted_messages.
-- roleplay_messages holds the type, original id, content(?), room, timestamp, and sender (1/rpm)
--  pk would be original id (like current)
-- crossposted_messages holds the original id [source], the recipient, and the received message id (n/rpm)
--  pk would be original id x recipient (same as current)
-- with the way I did caching, I don't want to deal, but this might be more efficient in some ways.
