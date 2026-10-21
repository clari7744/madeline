INSERT INTO
    zones (zone_name)
VALUES
    ('outside'),
    ('basement'),
    ('main floor'),
    ('top floor') ON CONFLICT (zone_name) DO NOTHING;

INSERT INTO
    rooms (room_name, zone, description)
VALUES
    (
        'kitchen',
        'main floor',
        'The kitchen is pristine and well stocked. The glass cupboards are full of utensils and cookware, ready to use.'
    ),
    (
        'pantry',
        'main floor',
        'The pantry is home to every shape of pasta ever made available in stores, and not much else.'
    ),
    (
        'living room',
        'main floor',
        'There are four couches in the living room, making it seem like the most sittable place in the whole house.'
    ),
    (
        'dining room',
        'main floor',
        'Around the dining room table sit four rigid, cushionless wood chairs. a screen door shows a clear view of the back yard.'
    ),
    (
        'back yard',
        'outside',
        'A vast expanse of green grass, with a little plastic playhouse in the center.'
    ),
    (
        'closet',
        'main floor',
        'Coats dangle from hangers inside, beneath a shelf that props up about four board games and a deck of cards.'
    ),
    (
        'front room',
        'main floor',
        "There's not much in this room, aside from a staircase leading to floors above and below, and also a nifty shoe shelf."
    ),
    (
        'front yard',
        'outside',
        "For whatever reason, the mailbox for the house is planted firmly in the center of the front yard, about six feet away from the front door. There's a small worn path in the grass leading out to the road, made by and for the poor mailman who uses it."
    ),
    (
        'upstairs landing',
        'top floor',
        "A small, plain area lined with doors."
    ),
    (
        'bathroom',
        'top floor',
        "The bathroom, aside from its necessary shower, toilet, and sink, contains a wardrobe full of towels."
    ),
    (
        'master bedroom',
        'top floor',
        "The master bedroom has a king size bed, surrounded by a plush rug and two neat nightstands. It appears to have its own closet and bathroom."
    ),
    (
        'master bathroom',
        'top floor',
        "The master bathroom, the master of all bathrooms, has its own jacuzzi to the side of the shower, but no plain bathtub. There are two sinks, one toilet, and a whole lot of skincare products."
    ),
    (
        'walk-in closet',
        'top floor',
        "The walk-in closet unlike the rest of the house, is completely empty, save for a spot of lint on the carpet."
    ),
    (
        'kids room',
        'top floor',
        "A racecar bed and a road themed rug give this room the appearance of a comfy cozy NASCAR track. Some toy cars litter the floor in no particular arrangement."
    ),
    (
        'toy closet',
        'top floor',
        "In the toy closet, buckets of hot wheels and green army men wait for action."
    ),
    (
        'home office',
        'top floor',
        "Two desks sit against either wall, both littered with paperwork and supplies. One desk bears an unopened laptop."
    ),
    (
        'downstairs landing',
        'basement',
        "The downstairs landing is a mostly vacant space, save for some movie posters on the walls and a few stray toy cars on the carpet."
    ),
    (
        'guest bedroom',
        'basement',
        "A plain white queen bed sits neatly made and ready for use. A dresser full of linens stands tall, but smells untouched."
    ),
    (
        'movie theater',
        'basement',
        "A leather couch with reclining seats faces a projector screen. The projector hangs from the ceiling with some unconcealed wires dangling by."
    ),
    (
        'game room',
        'basement',
        "A green felt table sits as the room's centerpiece, with folding chairs around it. Cards and chips are stacked neatly, waiting to be used."
    ) ON CONFLICT (room_name) DO NOTHING;

INSERT INTO
    connections (room, connected_to, direction)
VALUES
    ('kitchen', 'pantry', 'north'),
    ('kitchen', 'living room', 'south'),
    ('kitchen', 'dining room', 'west'),
    ('pantry', 'kitchen', 'south'),
    ('living room', 'kitchen', 'north'),
    ('living room', 'front room', 'west'),
    ('living room', 'closet', 'east'),
    ('dining room', 'kitchen', 'east'),
    ('dining room', 'back yard', 'west'),
    ('back yard', 'dining room', 'east'),
    ('closet', 'living room', 'west'),
    ('front room', 'living room', 'east'),
    ('front room', 'front yard', 'east'),
    ('front room', 'upstairs landing', 'up'),
    ('front room', 'downstairs landing', 'down'),
    ('front yard', 'front room', 'west'),
    ('upstairs landing', 'bathroom', 'north'),
    ('upstairs landing', 'home office', 'east'),
    ('upstairs landing', "kids room", "south"),
    ('upstairs landing', 'master bedroom', 'west'),
    ('upstairs landing', 'front room', 'down'),
    ('bathroom', 'upstairs landing', 'south'),
    ('home office', 'upstairs landing', 'west'),
    ('kids room', 'upstairs landing', 'north'),
    ('kids room', 'toy closet', 'east'),
    ('toy closet', 'kids room', 'west'),
    ('master bedroom', 'upstairs landing', 'east'),
    ('master bedroom', 'master bathroom', 'north'),
    ('master bedroom', 'walk-in closet', 'south'),
    ('master bathroom', 'master bedroom', 'south'),
    ('walk-in closet', 'master bedroom', 'north'),
    ('downstairs landing', 'movie theater', 'east'),
    ('downstairs landing', 'guest bedroom', 'west'),
    ('downstairs landing', 'game room', 'south'),
    ('downstairs landing', 'front room', 'up'),
    ('movie theater', 'downstairs landing', 'west'),
    ('guest bedroom', 'downstairs landing', 'east'),
    ('game room', 'downstairs landing', 'north') ON CONFLICT (room, connected_to) DO NOTHING;