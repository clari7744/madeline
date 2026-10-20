import os
from logging import addLevelName

import jishaku
from dotenv import load_dotenv

load_dotenv(verbose=True)
TESTING = os.getenv("TESTING", "False").lower() in ("true", "1", "t", "y", "yes")
TOKEN = os.getenv("TOKEN")

if TESTING:
    GUILD_ID = 1555644504181317805
    DATABASE_NAME = "manor_test.db"
else:
    GUILD_ID = 1375726989805092874
    DATABASE_NAME = "manor.db"

LOCAL_DEBUG = 15
CURRENT_DEBUG = 18
addLevelName(LOCAL_DEBUG, "LDEBUG")
addLevelName(CURRENT_DEBUG, "CDEBUG")

VALID_CATEGORIES = [1555644667146670100, 1555644808788312115]


jishaku.Flags.NO_DM_TRACEBACK = True
jishaku.Flags.NO_UNDERSCORE = True
