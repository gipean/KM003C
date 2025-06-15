#!/bin/env python3

from KM003C.defs import *
import pyshark

#Wireshark filter:
#usb.device_address > 4 && !(usb.urb_type == 'S' && usb.endpoint_address.direction == IN) && !(usb.urb_type == 'C' && usb.endpoint_address.direction == OUT) && usb.endpoint_address.number == 1

cap = pyshark.FileCapture("capture.pcapng")

def print_headers(data: bytes):
    if len(data) == 0:
        return
    header = MsgHeader.from_bytes(data[:4])
    print(header)
    if header.type == CmdDataMsgType.CMD_PUT_DATA:
        if header.obj:
            ext_header = MsgHeaderHeader.from_bytes(data[4:8])
            print(ext_header)
    print_headers(data[4+(header.obj*4):])

extend = False
for packet in cap:
    if 'USB' in packet:
        usb = packet.usb

        if not hasattr(packet, 'data'):
            continue
        data = bytes.fromhex(packet.data.usb_capdata.replace(":", ""))
        print(usb.endpoint_address_number, 'IN' if usb.endpoint_address_direction == '1' else 'OUT', f'SIZE={len(data)}')
        if extend:
            print('extended')
            print("-" * 30)
            extend = False
            continue
        print(repr(data))

        extend = interpret_response(data).extend

        print("-" * 30)