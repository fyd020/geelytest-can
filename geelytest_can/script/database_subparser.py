import logging
import sys
import argparse
from jidutest_can.script.__main__ import MainParser
from jidutest_can.script.tools import set_log
from jidutest_can.script.tools import convert_frame_id_or_name
from jidutest_can.script.tools import get_db_by_file
from jidutest_can.script.tools import rgb_red
from jidutest_can.script.tools import print_db_message
from jidutest_can.script.tools import print_db_signal
from jidutest_can.script.tools import get_message_by_name_id
from jidutest_can.script.tools import get_signal_by_name


logger = logging.getLogger(__name__)


@MainParser.RegisterSubparser("show-db", [
    {"arg_name": "db_path", "type": str, "help": "Database file path"},
    {"arg_name": "names", "type": str, "help": "message name or signal name or can_id", "nargs": "*"},
    {"arg_name": "--debug", "type": int, "help": "Enable or disable debug level", "default": 0, "choices": [0, 1]},
],
    "look at message or signal in database file")
def show_db(args: argparse.Namespace) -> None:
    set_log(args.debug)
    db_object = get_db_by_file(args.db_path)

    if not args.names:
        sys.stdout.write(f"{db_object}")
        sys.exit(1)

    for msg_sgn in args.names:
        msg_sgn = convert_frame_id_or_name(msg_sgn)
        if get_message_by_name_id(db_object, msg_sgn):
            print_db_message(db_object, msg_sgn)
        elif get_signal_by_name(db_object, msg_sgn):
            print_db_signal(db_object, msg_sgn)
        else:
            logger.warning(rgb_red(f"Database {args.db_path} hasn't the signal {msg_sgn} \n"))
