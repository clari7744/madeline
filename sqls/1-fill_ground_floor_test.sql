-- Zones are required for rooms
INSERT INTO
    zones (zone_name, description)
VALUES
    (
        'Central Wing Ground Floor',
        'The ground floor of the central wing of the manor.'
    ) ON CONFLICT (zone_name) DO NOTHING;

-- Rooms are required for connections and players
-- Fails if zones are missing
INSERT INTO
    rooms (room_name, zone, description, locked)
VALUES
    (
        'Gallery Entrance',
        'Central Wing Ground Floor',
        'As far as first impressions are concerned, le Manoir de Montpellier certainly has high ambitions. Pale brown walls make the gallery entrance feel both large and small at once, but the vaguely patterned wallpaper practically vanishes around the two masterwork paintings displayed on either wall like great trophies. On the Eastern wall hangs *The Acrobats*, and to the West, *The Enigma*, both paintings done by Paul Gustave Doré and labelled so by plaques beneath their frames. Coat hangers rigidly stand guard by the front entrance, their forms accented with hazy sconcelight at all hours. Not far behind them, a pair of symmetrical windows arc around and above a set of rounded double doors with ornate, polished handles made of brass.',
        false
    ),
    (
        'Cloakroom',
        'Central Wing Ground Floor',
        'Few threadbare cloaks remain inside this generously sized closet, the space of which is chokingly filled with dust. There is a tall, narrow table beside the door, and atop of it, an oil lamp which refuses to light on account of emptiness.',
        0
    ),
    (
        'Grand Hall',
        'Central Wing Ground Floor',
        'Gallery windows paint the chalky air with light, when daylight comes, causing the illusion of winter snowfall within the manor, just as without. The deep wooden flooring that merely underscores the Gallery Entrance takes center stage in the Grand Hall. Woodgrain winds around the empty space in meticulous patterns, both angular and swirling, to create a beautiful garden scene underfoot. Flowering trees with deeply burrowing roots, a rocky outcropping with depth imitated by varying values of wood, and birds soaring through the sky on oaken feathers, all captured in one beautiful, natural piece. Thin tables line the walls to the South, and a thick layer of dust dims the shine of each golden brocade tablecloth adorning them. Candles perch wiltingly on blackening silver posts, embraced by cobwebs and frozen saults of wax. Within the hall, a hollowness is embraced by draughty winter air and the moans of shrinking wood, a voiceless song in a lonely place.',
        0
    ),
    (
        'Ground Floor Central Hallway',
        'Central Wing Ground Floor',
        'Lorem ipsum',
        0
    ),
    (
        'West Library',
        'Central Wing Ground Floor',
        'Lorem ipsum',
        0
    ),
    (
        'Reading Nook',
        'Central Wing Ground Floor',
        'Lorem ipsum',
        0
    ),
    (
        'Sitting Room',
        'Central Wing Ground Floor',
        'Lorem ipsum',
        0
    ),
    (
        'West Entrance',
        'Central Wing Ground Floor',
        'Lorem ipsum',
        0
    ),
    (
        'Ballroom',
        'Central Wing Ground Floor',
        'Lorem ipsum',
        0
    ),
    (
        'Hall Lounge',
        'Central Wing Ground Floor',
        'Lorem ipsum',
        0
    ),
    (
        'Smoking Room',
        'Central Wing Ground Floor',
        'Lorem ipsum',
        0
    ),
    (
        'East Entrance',
        'Central Wing Ground Floor',
        'Lorem ipsum',
        0
    ) ON CONFLICT (room_name) DO NOTHING;

-- Connections are required for players to move between rooms
-- Fails if rooms are missing
INSERT INTO
    connections (room, connected_to, direction)
VALUES
    ('Gallery Entrance', 'Grand Hall', 'north'),
    ('Grand Hall', 'Gallery Entrance', 'south'),
    (
        'Grand Hall',
        'Ground Floor Central Hallway',
        'north'
    ),
    (
        'Ground Floor Central Hallway',
        'Grand Hall',
        'south'
    ),
    ('West Entrance', 'Sitting Room', 'north'),
    ('Sitting Room', 'West Entrance', 'south'),
    (
        'Ballroom',
        'Ground Floor Central Hallway',
        'north'
    ),
    (
        'Ground Floor Central Hallway',
        'Ballroom',
        'south'
    ),
    ('Smoking Room', 'Hall Lounge', 'north'),
    ('Hall Lounge', 'Smoking Room', 'south'),
    ('Gallery Entrance', 'Cloakroom', 'east'),
    ('Cloakroom', 'Gallery Entrance', 'west'),
    ('Grand Hall', 'Ballroom', 'east'),
    ('Ballroom', 'Grand Hall', 'west'),
    ('West Library', 'Grand Hall', 'east'),
    ('Grand Hall', 'West Library', 'west'),
    ('Sitting Room', 'West Library', 'east'),
    ('West Library', 'Sitting Room', 'west'),
    ('Ballroom', 'East Entrance', 'east'),
    ('East Entrance', 'Ballroom', 'west'),
    ('West Library', 'Reading Nook', 'east'),
    ('Reading Nook', 'West Library', 'west') ON CONFLICT (room, connected_to) DO NOTHING;