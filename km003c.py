import usb.core, usb.util
from defs import *

class PowerZ_KM003C:
    def __init__(self):
        self.dev = None

    def __enter__(self):
        dev = usb.core.find(idVendor=0x5fc9, idProduct=0x0063)
        if dev is None:
            raise RuntimeError('Unable to locate POWER-Z KM003C meter')

        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
        usb.util.claim_interface(dev, 0)

        self.dev = dev
        self.in_endpoint = 0x81
        self.out_endpoint = 0x01

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Clean up resources
        if self.dev:
            cmd = MsgHeader(
                type=CmdCtrlMsgType.CMD_DISCONNECT,
                extend=0,
                id=1,
                att=0
            ).to_bytes()
            self.send(cmd)
            self.dev.reset()
            usb.util.dispose_resources(self.dev)

    def send_dbg(self, msg: bytes):
        print(hex(self.out_endpoint), 'OUT', f'SIZE={len(msg)}')
        interpret_response(msg)
        print("-" * 30)
        if self.dev.write(self.out_endpoint, msg) != len(msg):
            print(f'ERROR: sent bytes != {len(msg)}')
            return
        data = self.dev.read(self.in_endpoint, 10240)
        print(hex(self.in_endpoint), 'IN', f'SIZE={len(data)}')
        hdr = interpret_response(data)
        if hdr.extend:
            data = self.dev.read(self.in_endpoint, 10240)
            print(hex(self.in_endpoint), 'IN', f'SIZE={len(data)}')
            print('extend')
        print("-" * 30)

    def send(self, msg: bytes):
        if self.dev.write(self.out_endpoint, msg) != len(msg):
            print(f'ERROR: sent bytes != {len(msg)}')
            return
        data = self.dev.read(self.in_endpoint, 10240)
        hdr = MsgHeader.from_bytes(data[:4])
        if hdr.extend:
            ext_data = self.dev.read(self.in_endpoint, 10240)
            return (hdr, data[4:] + ext_data)
        return (hdr, data[4:])