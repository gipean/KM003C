
import struct
from enum import IntEnum

# Enum for command control message types
class CmdCtrlMsgType(IntEnum):
    CMD_SYNC = 1
    CMD_CONNECT = 2
    CMD_DISCONNECT = 3
    CMD_RESET = 4
    CMD_ACCEPT = 5
    CMD_REJECT = 6
    CMD_FINISHED = 7
    CMD_JUMP_APROM = 8
    CMD_JUMP_DFU = 9
    CMD_GET_STATUS = 10
    CMD_ERROR = 11
    CMD_GET_DATA = 12
    CMD_GET_FILE = 13
    CMD_SET_RATE = 14


# Enum for data message types
class CmdDataMsgType(IntEnum):
    CMD_HEAD = 64
    CMD_PUT_DATA = 65  # Reserved 0–63


# Enum for attribute types
class AttributeDataType(IntEnum):
    ATT_NONE = 0x000
    ATT_ADC = 0x001
    ATT_ADC_QUEUE = 0x002
    ATT_ADC_QUEUE_10K = 0x004
    ATT_SETTINGS = 0x008
    ATT_PD_PACKET = 0x010
    ATT_PD_STATUS = 0x020
    ATT_QC_PACKET = 0x040

class Rate(IntEnum):
    _2SPS = 0
    _10SPS = 1
    _50SPS = 2
    _1KSPS = 3

# Header class definition
class MsgHeader:
    def __init__(self, type, extend, id, att=None, obj=None):
        self.type = type      # 7 bits
        self.extend = extend  # 1 bit
        self.id = id          # 8 bits
        self.att = att        # 15 bits (for control messages)
        self.obj = obj        # 10 bits (for data messages)

    @classmethod
    def from_bytes(cls, data):
        """
        Parses a 4-byte representation into a MsgHeader object.
        """
        if len(data) != 4:
            raise ValueError("Data must be exactly 4 bytes.")

        # Unpack the 4 bytes into a 32-bit unsigned integer
        packed = struct.unpack('<I', data)[0]

        # Extract common fields
        type = packed & 0x7F
        extend = (packed >> 7) & 0x1
        id = (packed >> 8) & 0xFF

        # Parse based on type
        if type > 63:  # Data message
            obj = (packed >> 22) & 0x03FF  # 10 bits for obj
            return cls(type, extend, id, obj=obj)
        else:  # Control message
            att = (packed >> 17) & 0x7FFF  # 15 bits for att
            return cls(type, extend, id, att=att)

    def to_bytes(self):
        """
        Converts the MsgHeader object into a 4-byte representation.
        """
        if self.type > 63:  # Data message
            header = (
                (self.type & 0x7F) |               # Type (7 bits)
                ((self.extend & 0x1) << 7) |      # Extend (1 bit)
                ((self.id & 0xFF) << 8) |         # ID (8 bits)
                ((self.obj & 0x03FF) << 22)       # Object (10 bits)
            )
        else:  # Control message
            header = (
                (self.type & 0x7F) |               # Type (7 bits)
                ((self.extend & 0x1) << 7) |      # Extend (1 bit)
                ((self.id & 0xFF) << 8) |         # ID (8 bits)
                ((self.att & 0x7FFF) << 17)       # Attribute (15 bits)
            )
        return struct.pack('<I', header)

    def __str__(self):
        """
        Returns a readable string representation of the MsgHeader object.
        """
        if self.type > 63:  # Data message
            type_name = CmdDataMsgType(self.type).name if self.type in CmdDataMsgType._value2member_map_ else f"Unknown({self.type})"
            return (
                f"MsgHeader (Data):\n"
                f"  Type: {type_name} (Data Message)\n"
                f"  Extend: {self.extend}\n"
                f"  ID: {self.id}\n"
                f"  Object: {self.obj*4}"
            )
        else:  # Control message
            type_name = CmdCtrlMsgType(self.type).name if self.type in CmdCtrlMsgType._value2member_map_ else f"Unknown({self.type})"
            att_name = AttributeDataType(self.att).name if self.att in AttributeDataType._value2member_map_ else f"Unknown({self.att})"

            return (
                f"MsgHeader (Control):\n"
                f"  Type: {type_name} ({self.type})\n"
                f"  Extend: {self.extend}\n"
                f"  ID: {self.id}\n"
                f"  Attribute: {att_name} ({self.att})"
            )

class AdcData:
    """
    Represents the AdcData_TypeDef structure.
    """
    STRUCT_FORMAT = '<6ih5HI'  # Format string for struct.unpack based on the AdcData structure.

    def __init__(self, vbus, ibus, vbus_avg, ibus_avg, vbus_ori_avg, ibus_ori_avg,
                 temp, vcc1, vcc2, vdp, vdm, vdd, rate):
        self.vbus = vbus                # Unit: 1 µV
        self.ibus = ibus                # Unit: 1 µA
        self.vbus_avg = vbus_avg        # Smoothed average voltage (1 µV)
        self.ibus_avg = ibus_avg        # Smoothed average current (1 µA)
        self.vbus_ori_avg = vbus_ori_avg  # Uncalibrated average voltage (1 µV)
        self.ibus_ori_avg = ibus_ori_avg  # Uncalibrated average current (1 µA)
        # INA228/9 datasheet LSB = 7.8125 m°C = 1000/128
        print(f'temp={temp}')
        msb = (temp >> 8) & 0xFF
        lsb = temp & 0xFF
        self.temp = (msb*2000 + lsb*1000/128)/1000
        self.vcc1 = vcc1                # Resolution: 0.1 mV
        self.vcc2 = vcc2
        self.vdp = vdp
        self.vdm = vdm
        self.vdd = vdd                  # Internal VDD voltage
        self.rate = (rate >> 16) & 0x3  # Rate: 2 bits

    @classmethod
    def from_bytes(cls, data):
        """
        Parses bytes into an AdcData object.
        """
        if len(data) < struct.calcsize(cls.STRUCT_FORMAT):
            raise ValueError(f"Data size ({len(data)}) is smaller than expected for AdcData ({struct.calcsize(cls.STRUCT_FORMAT)}).")

        # Unpack the data based on the format string
        unpacked = struct.unpack(cls.STRUCT_FORMAT, data[:40])
        return cls(*unpacked)

    def __str__(self):
        """
        Returns a readable string representation of the AdcData object.
        """
        return (
            f"AdcData:\n"
            f"  Vbus: {self.vbus} µV\n"
            f"  Ibus: {self.ibus} µA\n"
            f"  Vbus Avg: {self.vbus_avg} µV\n"
            f"  Ibus Avg: {self.ibus_avg} µA\n"
            f"  Vbus Ori Avg: {self.vbus_ori_avg} µV\n"
            f"  Ibus Ori Avg: {self.ibus_ori_avg} µA\n"
            #else if (type == hwmon_temp && attr == hwmon_temp_input)
            #*val = ((long)data->temp[1]) * 2000 + ((long)data->temp[0]) * 1000 / 128;
            f"  Temp: {self.temp}°C (internal temperature)\n"
            f"  Vcc1: {self.vcc1 / 10.0} mV\n"
            f"  Vcc2: {self.vcc2 / 10.0} mV\n"
            f"  Vdp: {self.vdp} mV\n"
            f"  Vdm: {self.vdm} mV\n"
            f"  Vdd: {self.vdd} mV\n"
            f"  Rate: {self.rate}"
        )

class MsgHeaderHeader:
    """
    Represents the header subtype of MsgHeader.
    """
    STRUCT_FORMAT = '<I'  # 4 bytes (uint32_t)

    def __init__(self, att, next_flag, chunk, size):
        self.att = att              # 15 bits: Attribute code
        self.next_flag = next_flag  # 1 bit: Next flag
        self.chunk = chunk          # 6 bits: Chunk size
        self.size = size            # 10 bits: Size (cannot exceed 1024-8 bytes)

    @classmethod
    def from_bytes(cls, data):
        """
        Parses a 4-byte representation into a MsgHeaderHeader object.
        """
        if len(data) != 4:
            raise ValueError("Data must be exactly 4 bytes.")

        # Unpack the 4 bytes into a 32-bit unsigned integer
        packed = struct.unpack(cls.STRUCT_FORMAT, data)[0]

        # Extract individual fields using bit masking and shifting
        att = packed & 0x7FFF                 # 15 bits for att
        next_flag = (packed >> 15) & 0x1     # 1 bit for next
        chunk = (packed >> 16) & 0x3F        # 6 bits for chunk
        size = (packed >> 22) & 0x03FF       # 10 bits for size

        return cls(att, next_flag, chunk, size)

    def to_bytes(self):
        """
        Converts the MsgHeaderHeader object into a 4-byte representation.
        """
        header = (
            (self.att & 0x7FFF) |            # 15 bits for att
            ((self.next_flag & 0x1) << 15) |  # 1 bit for next
            ((self.chunk & 0x3F) << 16) |    # 6 bits for chunk
            ((self.size & 0x03FF) << 22)     # 10 bits for size
        )
        return struct.pack(self.STRUCT_FORMAT, header)

    def __str__(self):
        """
        Returns a readable string representation of the MsgHeaderHeader object.
        """
        att_name = AttributeDataType(self.att).name if self.att in AttributeDataType._value2member_map_ else f"Unknown({self.att})"
        return (
            f"MsgHeader (Header Subtype):\n"
            f"  Attribute: {att_name}\n"
            f"  Next Flag: {self.next_flag}\n"
            f"  Chunk: {self.chunk}\n"
            f"  Size: {self.size} bytes"
        )

class AdcQueueEntry:
    """
    Represents an extended ADC data structure, including timestamp and multiple voltage/current measurements.
    """
    STRUCT_FORMAT = '<I2i4H'  # Format: Timestamp (uint32), 2 signed integers, 4 unsigned shorts.

    def __init__(self, timestamp_ms, vbus, ibus, vcc1, vcc2, vdp, vdm):
        self.timestamp_ms = timestamp_ms  # Timestamp in milliseconds
        self.vbus = vbus                  # Voltage bus in µV
        self.ibus = ibus                  # Current bus in µA
        self.vcc1 = vcc1                  # Vcc1 in 0.1mV
        self.vcc2 = vcc2                  # Vcc2 in 0.1mV
        self.vdp = vdp                    # Voltage on D+ line in mV
        self.vdm = vdm                    # Voltage on D- line in mV

    @classmethod
    def from_bytes(cls, data):
        """
        Parses bytes into an AdcQueueEntry object.
        """
        if len(data) < struct.calcsize(cls.STRUCT_FORMAT):
            raise ValueError(
                f"Data size ({len(data)}) is smaller than expected for AdcQueueEntry ({struct.calcsize(cls.STRUCT_FORMAT)})."
            )

        # Unpack the data based on the format string
        unpacked = struct.unpack(cls.STRUCT_FORMAT, data)
        return cls(*unpacked)

    def __str__(self):
        """
        Returns a readable string representation of the AdcQueueEntry object.
        """
        return (
            f"AdcQueueEntry:\n"
            f"  Timestamp: {self.timestamp_ms} ms\n"
            f"  Vbus: {self.vbus} µV\n"
            f"  Ibus: {self.ibus} µA\n"
            f"  Vcc1: {self.vcc1/10:.1f} mV\n"
            f"  Vcc2: {self.vcc2/10:.1f} mV\n"
            f"  Vdp: {self.vdp} mV\n"
            f"  Vdm: {self.vdm} mV"
        )

def print_data(data, obj_size):
    #obj size is not reliable
    if len(data) <= 0:
        if len(data):
            print(f'data remaining {len(data)}')
        return
    ext_header = MsgHeaderHeader.from_bytes(data[:4])
    print(ext_header)
    #print(len(data))
    #print(bytes(data[4:4+ext_header.size]).hex())
    if ext_header.att == AttributeDataType.ATT_ADC:
        adc_data = AdcData.from_bytes(data[4:4+ext_header.size])
        print(adc_data)
    elif ext_header.att == AttributeDataType.ATT_ADC_QUEUE:
        for i in range(max(ext_header.chunk, 1)):
            entry = AdcQueueEntry.from_bytes(data[4+(i*ext_header.size):4+((i+1)*ext_header.size)])
            print(entry)
    size = ext_header.size
    if ext_header.chunk:
        size *= ext_header.chunk
    if ext_header.next_flag:
        print_data(data[4+size:], obj_size-size)
    else:
        if len(data[4+size:]):
            print('data remaining')
    return

def parse_data(data: bytes):
    if len(data) == 0:
        return []
    ext_header = MsgHeaderHeader.from_bytes(data[:4])
    obj = None
    if ext_header.att == AttributeDataType.ATT_ADC:
        obj = AdcData.from_bytes(data[4:4+ext_header.size])
    elif ext_header.att == AttributeDataType.ATT_ADC_QUEUE:
        entries = []
        for i in range(max(ext_header.chunk, 1)):
            entries.append(AdcQueueEntry.from_bytes(data[4+(i*ext_header.size):4+((i+1)*ext_header.size)]))
        obj = entries
    else:
        obj = (ext_header.att, data[4:4+ext_header.size])

    size = ext_header.size
    if ext_header.chunk:
        size *= ext_header.chunk
    if ext_header.next_flag:
        return [obj] + parse_data(data[4+size:])
    return [obj]

def interpret_response(data):
    header = MsgHeader.from_bytes(data[:4])
    print(header)
    if header.type == CmdDataMsgType.CMD_PUT_DATA:
        print_data(data[4:], header.obj*4)

    return header