import json
import struct

from plugins.sq import generate_json_from_data

EVENT_ID_MAP = {
    0x10: "bpm",
    0x20: "barinfo",
    0x30: "baron",
    0x40: "baroff",
    0x50: "measure",
    0x60: "beat",
    0x70: "chipstart",
    0x80: "chipend",
    0xe0: "startpos",
    0xf0: "endpos",
    0x00: "note",
    0x01: "auto",
}

EVENT_ID_REVERSE = {EVENT_ID_MAP[k]: k for k in EVENT_ID_MAP}

DIFFICULTY_LEVELS_MAP = {
    0x00: "NOV",
    0x01: "BSC",
    0x02: "ADV",
    0x03: "EXT",
    0x04: "MST"
}

GAMES_MAP = {
    0x00: "Drums",
    0x01: "Guitar",
    0x02: "Bass",
    0x03: "Open",
}

NOTE_MAPPING = {
    'drum': {
        0x00: "hihat",
        0x01: "snare",
        0x02: "bass",
        0x03: "hightom",
        0x04: "lowtom",
        0x05: "rightcymbal",
        0xff: "auto",
    },
    'guitar': {
        0x01: "g_rxx",
        0x02: "g_xgx",
        0x03: "g_rgx",
        0x04: "g_xxb",
        0x05: "g_rxb",
        0x06: "g_xgb",
        0x07: "g_rgb",
        0x10: 'g_open',
        0xff: "auto",
    },
    'bass': {
        0x01: "b_rxx",
        0x02: "b_xgx",
        0x03: "b_rgx",
        0x04: "b_xxb",
        0x05: "b_rxb",
        0x06: "b_xgb",
        0x07: "b_rgb",
        0x10: 'b_open',
        0xff: "auto",
    },
    'open': {
        0x01: "g_rxx",
        0x02: "g_xgx",
        0x03: "g_rgx",
        0x04: "g_xxb",
        0x05: "g_rxb",
        0x06: "g_xgb",
        0x07: "g_rgb",
        0x10: "g_open",
        0xff: "auto",
    },
}

REVERSE_NOTE_MAPPING = {
    # Drum
    "hihat": 0x00,
    "snare": 0x01,
    "bass": 0x02,
    "hightom": 0x03,
    "lowtom": 0x04,
    "rightcymbal": 0x05,
    "auto": 0xff,

    # Guitar
    "g_rxx": 0x01,
    "g_xgx": 0x02,
    "g_rgx": 0x03,
    "g_xxb": 0x04,
    "g_rxb": 0x05,
    "g_xgb": 0x06,
    "g_rgb": 0x07,
    "g_rxxxx": 0x01,
    "g_xgxxx": 0x02,
    "g_rgxxx": 0x03,
    "g_xxbxx": 0x04,
    "g_rxbxx": 0x05,
    "g_xgbxx": 0x06,
    "g_rgbxx": 0x07,
    "g_open": 0x10,

    # Bass
    "b_rxx": 0x01,
    "b_xgx": 0x02,
    "b_rgx": 0x03,
    "b_xxb": 0x04,
    "b_rxb": 0x05,
    "b_xgb": 0x06,
    "b_rgb": 0x07,
    "b_rxxxx": 0x01,
    "b_xgxxx": 0x02,
    "b_rgxxx": 0x03,
    "b_xxbxx": 0x04,
    "b_rxbxx": 0x05,
    "b_xgbxx": 0x06,
    "b_rgbxx": 0x07,
}


def read_sq2_data(data, events, other_params):
    def parse_event_block(mdata, game, is_metadata=False):
        packet_data = {}

        timestamp = struct.unpack("<I", mdata[0x00:0x04])[0]

        event_name = EVENT_ID_MAP[mdata[0x05]]

        if mdata[0x05] == 0x10:
            bpm_bpm = struct.unpack("<I", mdata[0x08:0x0c])[0]
            packet_data['bpm'] = 60000000 / bpm_bpm
        elif mdata[0x05] == 0x20:
            # Time signature is represented as numerator/(1<<denominator)
            packet_data['numerator'] = mdata[0x0c]
            packet_data['denominator'] = 1 << mdata[0x0d]
        elif mdata[0x05] == 0x00:
            packet_data['sound_id'] = struct.unpack("<H", mdata[0x08:0x0A])[0]
            packet_data['sound_unk'] = struct.unpack("<H", mdata[0x0A:0x0C])[0]
            packet_data['volume'] = mdata[0x0c]

            if (mdata[0x04] & 0x10) == 0x10:
                # Open note
                packet_data['note'] = NOTE_MAPPING[game][mdata[0x04] & 0x10] # note
            else:
                packet_data['note'] = NOTE_MAPPING[game][mdata[0x04] & 0x0f] # note

            is_wail = (mdata[0x04] & 0x20) == 0x20

            packet_data['wail_misc'] = 1 if is_wail else 0
            packet_data['guitar_special'] = 1 if is_wail else 0

            # TODO: Update code to work with .EVT file data
            # if beat in events:
            #     for event in events[beat]:
            #         is_gametype = event['game_type'] == game_type_id
            #         is_eventtype = event['event_type'] == 0
            #         is_note = packet_data['sound_id'] == event['note']
            #         is_diff = (event['gamelevel'] & (1 << difficulty)) != 0

            #         if is_gametype and is_eventtype and is_note and is_diff:
            #             packet_data['bonus_note'] = True

            if is_metadata:
                event_name = "meta"

        elif mdata[0x05] == 0x01:
            # Auto note
            packet_data['sound_id'] = struct.unpack("<H", mdata[0x08:0x0A])[0]
            packet_data['sound_unk'] = struct.unpack("<H", mdata[0x0A:0x0C])[0]
            packet_data['volume'] = mdata[0x0c]
            packet_data['note'] = "auto"
            packet_data['auto_volume'] = 1
            packet_data['auto_note'] = 1
            event_name = "note"

        timestamp = struct.unpack("<I", mdata[0x00:0x04])[0]

        return {
            "id": mdata[0x04],
            "name": event_name,
            'timestamp': timestamp,
            'timestamp_ms': timestamp / 300,
            "data": packet_data
        }

    output = {
        "beat_data": []
    }

    if data is None:
        return None

    magic = data[0:4]
    if magic != bytearray("SEQT", encoding="ascii"):
        print("Not a valid SEQT chart")
        exit(-1)

    # TODO: What is unk_sys? Look into that
    unk_sys, is_metadata, difficulty, game_type = data[0x14:0x18]
    header_size = struct.unpack("<I", data[0x0c:0x10])[0]
    entry_count = struct.unpack("<I", data[0x10:0x14])[0]
    time_division = 300
    beat_division = 480
    entry_size = 0x10

    if is_metadata not in [0, 1]: # Only support metadata and note charts. Not sure what type 2 is yet
        return None

    output['header'] = {
        "unk_sys": unk_sys,
        "is_metadata": is_metadata,
        "difficulty": difficulty,
        "game_type": game_type,
        "time_division": time_division,
        "beat_division": beat_division,
    }

    for i in range(entry_count):
        mdata = data[header_size + (i * entry_size):header_size + (i * entry_size) + entry_size]
        part = ["drum", "guitar", "bass", "open", "guitar1", "guitar2"][game_type]
        parsed_data = parse_event_block(mdata, part, is_metadata=is_metadata)
        output['beat_data'].append(parsed_data)

    return output


def generate_json_from_sq2(params):
    data = open(params['input'], "rb").read() if 'input' in params else None

    if not data:
        print("No input file data")
        return

    output_data = {}

    magic = data[0:4]
    if magic != bytearray("SEQP", encoding="ascii"):
        print("Not a valid SQ2 file")
        exit(-1)

    data_offset = 0x20
    musicid, num_charts = struct.unpack("<II", data[0x14:0x1c])

    raw_charts = []
    for i in range(num_charts):
        data_size = struct.unpack("<I", data[data_offset:data_offset+4])[0]
        chart_data = data[data_offset+0x10:data_offset+0x10+data_size]
        raw_charts.append((chart_data, None, None, None))
        data_offset += data_size

    output_data = generate_json_from_data(params, read_sq2_data, raw_charts)
    output_data['musicid'] = musicid
    output_data['format'] = Sq2Format.get_format_name()

    return json.dumps(output_data, indent=4, sort_keys=True)


class Sq2Format:
    @staticmethod
    def get_format_name():
        return "SQ2"

    @staticmethod
    def to_json(params):
        return generate_json_from_sq2(params)

    @staticmethod
    def to_chart(params):
        raise NotImplementedError()

    @staticmethod
    def is_format(filename):
        header = open(filename, "rb").read(0x40)

        try:
            is_seqp = header[0x00:0x04].decode('ascii') == "SEQP"
            is_seqt = header[0x30:0x34].decode('ascii') == "SEQT"
            is_ver2 = header[0x36] == 0x02
            if is_seqp and is_ver2 and is_seqt:
                return True
        except:
            return False

        return False


def get_class():
    return Sq2Format
