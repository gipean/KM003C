#! /usr/bin/env python3

from .km003c import *
import traceback
import argparse
import csv

def log_data(power_meter: PowerZ_KM003C, output_file, rate):
    cmd = MsgHeader(
        type=CmdCtrlMsgType.CMD_CONNECT,
        extend=0,
        id=1,
        att=0
    ).to_bytes()
    power_meter.send(cmd)

    #Needed to make ADC_QUEUE work
    cmd = b'L\x02\x00\x02-\t\x9f\xb2\xff\xe3g\xdbGr\x84)\x9b\xc6"\xec?\xa1\xea\xf7B\xddY6(\xca\xe3\xd9\x82z\xec\x81'
    power_meter.send(cmd)

    cmd = MsgHeader(
        type=CmdCtrlMsgType.CMD_SET_RATE,
        extend=0,
        id=3,
        att=rate
    ).to_bytes()
    power_meter.send(cmd)

    id = 4

    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = ['timestamp_ms', 'vbus_µV', 'ibus_µA', 'vcc1_mV', 'vcc2_mV', 'vdp_mV', 'vdm_mV']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        while True:
            cmd = MsgHeader(
                type=CmdCtrlMsgType.CMD_GET_DATA,
                extend=0,
                id=id,
                att= AttributeDataType.ATT_ADC_QUEUE #| AttributeDataType.ATT_ADC
            ).to_bytes()
            id += 1

            hdr, data = power_meter.send(cmd)

            if hdr.type == CmdDataMsgType.CMD_PUT_DATA:
                data_objs = parse_data(data)
                if len(data_objs):
                    for entry in data_objs[0]:
                        writer.writerow({
                            'timestamp_ms': entry.timestamp_ms,
                            'vbus_µV': entry.vbus,
                            'ibus_µA': entry.ibus,
                            'vcc1_mV': entry.vcc1/10,
                            'vcc2_mV': entry.vcc2/10,
                            'vdp_mV': entry.vdp,
                            'vdm_mV': entry.vdm
                        })

            csvfile.flush()

def main():
    parser = argparse.ArgumentParser(description="KM003C Data Logger")
    parser.add_argument('output', type=str,
                        help="Path to a CSV file to save the output. This parameter is mandatory.")
    parser.add_argument('--rate', '-r', type=int, choices=[0, 1, 2, 3], default=0,
                        help="Data logging rate: 0 for 2SPS, 1 for 10SPS, 2 for 50SPS, 3 for 1KSPS (default: 0).")

    args = parser.parse_args()

    try:
        with PowerZ_KM003C() as power_meter:
            log_data(power_meter, output_file=args.output, rate=args.rate)
    except KeyboardInterrupt: pass
    except Exception:
        traceback.print_exc()

if __name__ == '__main__':
    main()
