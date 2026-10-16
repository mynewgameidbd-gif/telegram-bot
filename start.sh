#!/bin/bash
# দুই বট একসাথে চালানোর জন্য (local testing)
python user_bot.py &
python admin_bot.py &
wait
