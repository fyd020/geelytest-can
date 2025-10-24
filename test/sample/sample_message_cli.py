import argparse
from jidutest_can.script.message_subparser import send_msg, recv_msg


def test_send_message():
    arg = argparse.Namespace(
        interface="smartvci",
        channel=1,
        message_list=["0x123=11:22:33"],
        fd=1,
        bitrate=500,
        interval=100,
        duration=None,
        debug=1,
        catch_exc=1
    )
    send_msg(arg)


def test_recv_message():
    arg = argparse.Namespace(
        interface="smartvci",
        channel=1,
        id_list=["0x123"],
        fd=0,
        bitrate=500,
        duration=None,
        debug=1,
        catch_exc=1
    )
    recv_msg(arg)


if __name__ == "__main__":
    test_send_message()
    # test_recv_message()
