-- Players are important!
-- Fails if rooms are missing
INSERT INTO
    players (
        short_name, full_name, channel_id, emoji_id, location
    )
VALUES
    ('Anna', 'Anna Brambleberries', 1561816373481701436, 1378093189780738110, 'master bedroom'),
    ('Daze', 'Daze Hazydays', 1558182539451965440, 1546022668648845363, 'home office'),
    ('Fox', 'Fox Foxtrot', 1558182589305720892, 1546022640551198832, 'game room'),
    ('Hari', 'Hari Hayes', 1558182796093034646, 1546022511060197406, 'back yard'),
    ('Lucens', 'Lucens Anima', 1558182813537411232, 1546022539753426954, 'kitchen'),
    ('Peepo', 'Peepo Beepo', 1558182850073985115, 1546022602324049930, 'front yard'),
    ('Ruby', 'Ruby Corvid', 1558182942386167850, 1546022442072281198, 'downstairs landing'),
    ('Vinny', 'Vinny Angel', 1558182957812940830, 1546022697643937832, 'guest bedroom'),
    ('Zero', 'Zero Perks', 1558182969406005319, 1546022571370348564, 'pantry')
ON CONFLICT (channel_id) DO NOTHING;