import json
import struct

from plugins.sq import generate_json_from_data

EVENT_ID_MAP = {
    0x01: "bpm",
    0x02: "barinfo",
    0x03: "baron",
    0x04: "baroff",
    0x05: "measure",
    0x06: "beat",
    0x07: "chipstart",
    0x08: "chipend",
    0x0c: "unk0c", # Almost never used, no idea what it's for. Part of the metadata chart
    0x0e: "startpos",
    0x0f: "endpos",
    0x10: "note",
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
    0x03: "Bass"
}

NOTE_MAPPING = {
    'drum': {
        0x00: "hihat",
        0x01: "snare",
        0x02: "bass",
        0x03: "hightom",
        0x04: "lowtom",
        0x05: "rightcymbal",
        0x06: "leftcymbal",
        0x07: "floortom",
        0x08: "leftpedal",
        0xff: "auto",
    },
    'guitar': {
        0x00: "g_open",
        0x01: "g_rxxxx",
        0x02: "g_xgxxx",
        0x03: "g_rgxxx",
        0x04: "g_xxbxx",
        0x05: "g_rxbxx",
        0x06: "g_xgbxx",
        0x07: "g_rgbxx",
        0x08: "g_xxxyx",
        0x09: "g_rxxyx",
        0x0a: "g_xgxyx",
        0x0b: "g_rgxyx",
        0x0c: "g_xxbyx",
        0x0d: "g_rxbyx",
        0x0e: "g_xgbyx",
        0x0f: "g_rgbyx",
        0x10: "g_xxxxp",
        0x11: "g_rxxxp",
        0x12: "g_xgxxp",
        0x13: "g_rgxxp",
        0x14: "g_xxbxp",
        0x15: "g_rxbxp",
        0x16: "g_xgbxp",
        0x17: "g_rgbxp",
        0x18: "g_xxxyp",
        0x19: "g_rxxyp",
        0x1a: "g_xgxyp",
        0x1b: "g_rgxyp",
        0x1c: "g_xxbyp",
        0x1d: "g_rxbyp",
        0x1e: "g_xgbyp",
        0x1f: "g_rgbyp",
        0xff: "auto",
    },
    'bass': {
        0x00: "b_open",
        0x01: "b_rxxxx",
        0x02: "b_xgxxx",
        0x03: "b_rgxxx",
        0x04: "b_xxbxx",
        0x05: "b_rxbxx",
        0x06: "b_xgbxx",
        0x07: "b_rgbxx",
        0x08: "b_xxxyx",
        0x09: "b_rxxyx",
        0x0a: "b_xgxyx",
        0x0b: "b_rgxyx",
        0x0c: "b_xxbyx",
        0x0d: "b_rxbyx",
        0x0e: "b_xgbyx",
        0x0f: "b_rgbyx",
        0x10: "b_xxxxp",
        0x11: "b_rxxxp",
        0x12: "b_xgxxp",
        0x13: "b_rgxxp",
        0x14: "b_xxbxp",
        0x15: "b_rxbxp",
        0x16: "b_xgbxp",
        0x17: "b_rgbxp",
        0x18: "b_xxxyp",
        0x19: "b_rxxyp",
        0x1a: "b_xgxyp",
        0x1b: "b_rgxyp",
        0x1c: "b_xxbyp",
        0x1d: "b_rxbyp",
        0x1e: "b_xgbyp",
        0x1f: "b_rgbyp",
        0xff: "auto",
    }
}

REVERSE_NOTE_MAPPING = {
    # Drum
    "hihat": 0x00,
    "snare": 0x01,
    "bass": 0x02,
    "hightom": 0x03,
    "lowtom": 0x04,
    "rightcymbal": 0x05,
    "leftcymbal": 0x06,
    "floortom": 0x07,
    "leftpedal": 0x08,
    "auto": 0xff,

    # Guitar
    "g_open": 0x00,
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
    "g_xxxyx": 0x08,
    "g_rxxyx": 0x09,
    "g_xgxyx": 0x0a,
    "g_rgxyx": 0x0b,
    "g_xxbyx": 0x0c,
    "g_rxbyx": 0x0d,
    "g_xgbyx": 0x0e,
    "g_rgbyx": 0x0f,
    "g_xxxxp": 0x10,
    "g_rxxxp": 0x11,
    "g_xgxxp": 0x12,
    "g_rgxxp": 0x13,
    "g_xxbxp": 0x14,
    "g_rxbxp": 0x15,
    "g_xgbxp": 0x16,
    "g_rgbxp": 0x17,
    "g_xxxyp": 0x18,
    "g_rxxyp": 0x19,
    "g_xgxyp": 0x1a,
    "g_rgxyp": 0x1b,
    "g_xxbyp": 0x1c,
    "g_rxbyp": 0x1d,
    "g_xgbyp": 0x1e,
    "g_rgbyp": 0x1f,

    # Bass
    "b_open": 0x00,
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
    "b_xxxyx": 0x08,
    "b_rxxyx": 0x09,
    "b_xgxyx": 0x0a,
    "b_rgxyx": 0x0b,
    "b_xxbyx": 0x0c,
    "b_rxbyx": 0x0d,
    "b_xgbyx": 0x0e,
    "b_rgbyx": 0x0f,
    "b_xxxxp": 0x10,
    "b_rxxxp": 0x11,
    "b_xgxxp": 0x12,
    "b_rgxxp": 0x13,
    "b_xxbxp": 0x14,
    "b_rxbxp": 0x15,
    "b_xgbxp": 0x16,
    "b_rgbxp": 0x17,
    "b_xxxyp": 0x18,
    "b_rxxyp": 0x19,
    "b_xgxyp": 0x1a,
    "b_rgxyp": 0x1b,
    "b_xxbyp": 0x1c,
    "b_rxbyp": 0x1d,
    "b_xgbyp": 0x1e,
    "b_rgbyp": 0x1f,
}


def read_sq3_data(data, events, other_params):
    def parse_event_block(mdata, game, events={}):
        packet_data = {}

        timestamp = struct.unpack("<I", mdata[0x00:0x04])[0]
        beat = struct.unpack("<I", mdata[0x10:0x14])[0]
        game_type_id = {"drum": 0, "guitar": 1, "bass": 2}[game]

        if mdata[0x04] == 0x01:
            bpm_mpm = struct.unpack("<I", mdata[0x34:0x38])[0]
            packet_data['bpm'] = 60000000 / bpm_mpm
            # print(timestamp, packet_data)
        elif mdata[0x04] == 0x02:
            # Time signature is represented as numerator/(1<<denominator)
            packet_data['numerator'] = mdata[0x34]
            packet_data['denominator'] = 1 << mdata[0x35]
            packet_data['denominator_orig'] = mdata[0x35]

            # print(timestamp, packet_data)
        elif mdata[0x04] == 0x07:
            packet_data['unk'] = struct.unpack("<I", mdata[0x14:0x18])[0]  # What is this?
        elif mdata[0x04] == 0x10:
            packet_data['hold_duration'] = struct.unpack("<I", mdata[0x08:0x0c])[0]
            packet_data['unk'] = struct.unpack("<I", mdata[0x14:0x18])[0]  # What is this?
            packet_data['sound_id'] = struct.unpack("<I", mdata[0x20:0x24])[0]

            # Note length (relation to hold duration)
            packet_data['note_length'] = struct.unpack("<I", mdata[0x24:0x28])[0]

            packet_data['volume'] = mdata[0x2d]
            packet_data['auto_volume'] = mdata[0x2e]
            packet_data['note'] = NOTE_MAPPING[game][mdata[0x30]]

            # wail direction? 0/1 = up, 2 = down. Seems to alternate 0 and 1 if wailing in succession
            packet_data['wail_misc'] = mdata[0x31]

            # 2 = hold note, 1 = wail (bitmasks, so 3 = wail + hold)
            packet_data['guitar_special'] = mdata[0x32]

            # Auto note
            packet_data['auto_note'] = mdata[0x34]

            if packet_data['auto_note'] == 1:
                packet_data['note'] = "auto"

            if beat in events:
                for event in events[beat]:
                    is_gametype = event['game_type'] == game_type_id
                    is_eventtype = event['event_type'] == 0
                    is_note = packet_data['sound_id'] == event['note']

                    # This field seems to be maybe left over from previous games?
                    # 1852 doesn't work properly set the gamelevel fields
                    #is_diff = (event['gamelevel'] & (1 << difficulty)) != 0

                    if is_gametype and is_eventtype and is_note:
                        packet_data['bonus_note'] = True

        timestamp = struct.unpack("<I", mdata[0x00:0x04])[0]

        return {
            "id": mdata[0x04],
            "name": EVENT_ID_MAP[mdata[0x04]],
            'timestamp': timestamp,
            'timestamp_ms': timestamp / 300,
            'beat': beat,
            "data": packet_data
        }

    output = {
        "beat_data": []
    }

    if data is None:
        return None

    magic = data[0:4]
    if magic != bytearray("SQ3T", encoding="ascii"):
        print("Not a valid SQ3 file")
        exit(-1)

    # TODO: What is unk_sys? Look into that
    unk_sys, is_metadata, difficulty, game_type = data[0x14:0x18]
    header_size = struct.unpack("<I", data[0x0c:0x10])[0]
    entry_count = struct.unpack("<I", data[0x10:0x14])[0]
    time_division, beat_division, entry_size = struct.unpack("<HHI", data[0x18:0x20])

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
        part = ["drum", "guitar", "bass"][game_type]
        parsed_data = parse_event_block(mdata, part, events)
        output['beat_data'].append(parsed_data)

    return output


def generate_json_from_sq3(params):
    data = open(params['input'], "rb").read() if 'input' in params else None

    if not data:
        print("No input file data")
        return

    magic = data[0:4]
    if magic != bytearray("SEQP", encoding="ascii"):
        print("Not a valid SEQ3 file")
        exit(-1)

    data_offset, musicid, num_charts = struct.unpack("<III", data[0x10:0x1c])

    if 'musicid' not in params:
        params['musicid'] = musicid

    raw_charts = []
    for i in range(num_charts):
        data_size = struct.unpack("<I", data[data_offset:data_offset+4])[0]
        chart_data = data[data_offset+0x10:data_offset+0x10+data_size]
        raw_charts.append((chart_data, None, None, None))
        data_offset += data_size

    output_data = generate_json_from_data(params, read_sq3_data, raw_charts)
    output_data['musicid'] = musicid
    output_data['format'] = Sq3Format.get_format_name()

    return json.dumps(output_data, indent=4, sort_keys=True)


class Sq3Format:
    @staticmethod
    def get_format_name():
        return "SQ3"

    @staticmethod
    def to_json(params):
        return generate_json_from_sq3(params)

    @staticmethod
    def to_chart(params):
        raise NotImplementedError()

    @staticmethod
    def is_format(filename):
        header = open(filename, "rb").read(0x40)

        try:
            is_seqp = header[0x00:0x04].decode('ascii') == "SEQP"
            is_sq3t = header[0x30:0x34].decode('ascii') == "SQ3T"
            is_ver3 = header[0x36] == 0x03
            if is_seqp and is_ver3 and is_sq3t:
                return True
        except:
            return False

        return False


def get_class():
    return Sq3Format
