#!/usr/bin/env python

"""
This example shows how sending a single message works.
"""

import can
import time

DEVICE = 'vector' # 'pcan' 'vector' 'tosun'
CHANNEL = 1   # 'PCAN_USBBUS1'
BITRATE = 500000

def send_one():
    """Sends a single message."""

    # Using specific buses works similar:
    with can.Bus(interface=DEVICE, channel=CHANNEL, bitrate=BITRATE) as bus:
        # ...

        msg = can.Message(
            arbitration_id=0xC0FFEE, data=[0, 25, 0, 1, 3, 1, 4, 1], is_extended_id=True
        )

        try:
            bus.send(msg)
            print(f"Message sent on {bus.channel_info}")
        except can.CanError:
            print("Message NOT sent")
            
            
def send_periodic():
    """Sends a periodic message."""

    # Using specific buses works similar:
    with can.Bus(interface=DEVICE, channel=CHANNEL, bitrate=BITRATE) as bus:

        msg = can.Message(
            arbitration_id=0xC0FFEE, data=[0, 25, 0, 1, 3, 1, 4, 1], is_extended_id=True
        )

        try:
            bus.send_periodic(msg, period=1.0)
            print(f"Message sent on {bus.channel_info}")
            time.sleep(5)
        except can.CanError:
            print("Message NOT sent")
            
def recv_one():
    """Receives a single message."""

    # Using specific buses works similar:
    with can.Bus(interface=DEVICE, channel=CHANNEL, bitrate=BITRATE) as bus:
        # ...
        try:
            msg = bus.recv()
            print(f"Message received on {bus.channel_info}: {msg}")
        except can.CanError:
            print("Message NOT received")
            
def recv_periodic(duration=5):
    """Receives a periodic message."""

    # Using specific buses works similar:
    with can.Bus(interface=DEVICE, channel=CHANNEL, bitrate=BITRATE) as bus:
        # ...
        try:
            timeout = time.time() + duration
            while time.time() < timeout:
                msg = bus.recv()
                print(f"Message received on {bus.channel_info}: {msg}")
        except can.CanError:
            print("Message NOT received")
            

if __name__ == "__main__":
    # send_one()
    send_periodic()
    # recv_one()
    # recv_periodic()