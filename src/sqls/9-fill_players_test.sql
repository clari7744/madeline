-- Players are important!
-- Fails if rooms are missing
INSERT INTO players
(channel_id, short_name, full_name, emoji_id, location, following) VALUES
    (1555645170026815559, 'joe', 'Joe Schmoe', 1555649600566599723, 'Gallery Entrance', NULL),
    (1555645182735687720, 'abby', 'Abby Schmabby', 1555649650873081886, 'Gallery Entrance', 1555645170026815559),
    (1555645191887650846, 'susan', 'Susan Schmusan', 1555649693688537219, 'Cloakroom', NULL),
    (1555645202792841227, 'hermes', 'Hermes Schmermes', 1555649737766477986, 'Grand Hall', NULL),
    (1555645223714033724, 'alfalfa', 'Alfalfa Schmalfalfa', 1555649774810562671, 'Grand Hall', NULL),
    (1555645270363218060, 'ian', 'Ian Schmian', 1555649799901155338, 'Grand Hall', NULL),
    (1555645327908806686, 'herbert', 'Herbert Schmerbert', 1555649828095000688, 'Grand Hall', NULL),
    (1555645352571445312, 'mabel', 'Mabel Schmabel', 1555649855127289946, 'Grand Hall', NULL),
    (1555645382107603045, 'ellie', 'Ellie Schmellie', 1555649881610264607, 'Grand Hall', 1555645352571445312)
ON CONFLICT (channel_id) DO NOTHING;
