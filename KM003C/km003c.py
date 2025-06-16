import usb.core, usb.util
from .defs import *

class PowerZ_KM003C:
    def __init__(self, dev: usb.core.Device | None = None):
        if dev is None:
            found = usb.core.find(idVendor=0x5fc9, idProduct=0x0063)
            if not isinstance(found, usb.core.Device):
                raise RuntimeError('Unable to locate POWER-Z KM003C meter')
            dev = found

        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
        usb.util.claim_interface(dev, 0)

        self.dev = dev
        self.in_endpoint = 0x81
        self.out_endpoint = 0x01

        try:
            cmd = MsgHeader(
                type=CmdCtrlMsgType.CMD_CONNECT,
                extend=0,
                id=1,
                att=0
            ).to_bytes()
            response_header, response_data = self.send(cmd)
            if response_header.type == CmdCtrlMsgType.CMD_REJECT:
                raise CommandRejected(response_header)
            if response_header.type != CmdCtrlMsgType.CMD_ACCEPT:
                raise IOError(response_header)

            #Needed to make ADC_QUEUE work
            cmd = b'L\x02\x00\x02-\t\x9f\xb2\xff\xe3g\xdbGr\x84)\x9b\xc6"\xec?\xa1\xea\xf7B\xddY6(\xca\xe3\xd9\x82z\xec\x81'
            response_header, response_data = self.send(cmd)
            if response_header.type == CmdCtrlMsgType.CMD_REJECT:
                raise CommandRejected(response_header)
            if response_header.type != 76:
                raise IOError(response_header)

            self.id = 3
        except:
            usb.util.dispose_resources(self.dev)
            raise

    #Only after stopping an acquisition can the rate be changed
    def stop(self):
        cmd = MsgHeader(
            type=CmdCtrlMsgType.CMD_STOP,
            extend=0,
            id=self.id,
            att=0
        ).to_bytes()
        self.id += 1
        response_header, response_data = self.send(cmd)

        if response_header.type == CmdCtrlMsgType.CMD_REJECT:
            raise CommandRejected(response_header)
        if response_header.type != CmdCtrlMsgType.CMD_ACCEPT:
            raise IOError(response_header)

    #Setting rate also starts the acquisition
    def set_rate(self, rate: Rate):
        cmd = MsgHeader(
            type=CmdCtrlMsgType.CMD_SET_RATE,
            extend=0,
            id=self.id,
            att=rate
        ).to_bytes()
        self.id += 1
        response_header, response_data = self.send(cmd)

        if response_header.type == CmdCtrlMsgType.CMD_REJECT:
            raise CommandRejected(response_header)
        if response_header.type != CmdCtrlMsgType.CMD_ACCEPT:
            raise IOError(response_header)

    def get_data(self, att: int = AttributeDataType.ATT_ADC_QUEUE):
        cmd = MsgHeader(
            type=CmdCtrlMsgType.CMD_GET_DATA,
            extend=0,
            id=self.id,
            att=att
        ).to_bytes()
        self.id += 1

        hdr, data = self.send(cmd)
        if hdr.type == CmdDataMsgType.CMD_PUT_DATA:
            return parse_data(data)

        return []

    def close(self):
        try:
            cmd = MsgHeader(
                type=CmdCtrlMsgType.CMD_DISCONNECT,
                extend=0,
                id=1,
                att=0
            ).to_bytes()
            self.send(cmd)
        except:
            pass
        usb.util.dispose_resources(self.dev)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def send_dbg(self, msg: bytes):
        print(hex(self.out_endpoint), 'OUT', f'SIZE={len(msg)}')
        interpret_response(msg)
        print("-" * 30)
        if self.dev.write(self.out_endpoint, msg) != len(msg):
            print(f'ERROR: sent bytes != {len(msg)}')
            return
        data = self.dev.read(self.in_endpoint, 10240)
        data = bytes(data)
        print(hex(self.in_endpoint), 'IN', f'SIZE={len(data)}')
        hdr = interpret_response(data)
        if hdr.extend:
            ext_data = self.dev.read(self.in_endpoint, 10240)
            ext_data = bytes(ext_data)
            print(hex(self.in_endpoint), 'IN', f'SIZE={len(data)}')
            print('extend')
            data += ext_data
        print("-" * 30)
        return (hdr, data[4:])

    def send(self, msg: bytes):
        if self.dev.write(self.out_endpoint, msg) != len(msg):
            raise IOError(f'sent bytes != {len(msg)}')
        data = self.dev.read(self.in_endpoint, 10240)
        data = bytes(data)
        hdr = MsgHeader.from_bytes(data[:4])
        if hdr.extend:
            ext_data = self.dev.read(self.in_endpoint, 10240)
            ext_data = bytes(ext_data)
            return (hdr, data[4:] + ext_data)
        return (hdr, data[4:])