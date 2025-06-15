#! /usr/bin/env python3

from .km003c import *
import traceback
import argparse
import time
import csv

def log_data(power_meter: PowerZ_KM003C, output_file, rate):
    power_meter.set_rate(rate)

    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = ['timestamp_ms', 'vbus_µV', 'ibus_µA', 'vcc1_mV', 'vcc2_mV', 'vdp_mV', 'vdm_mV']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        while True:

            data_objs = power_meter.get_data()
            if len(data_objs):
                for entry in data_objs[0][1]:
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
            time.sleep(1)

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
