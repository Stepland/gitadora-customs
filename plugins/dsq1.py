import json
import os
import struct

USE_THREADS = True

EVENT_ID_MAP = {
    0x00: "note",
    0x01: "note",
    0x02: "note",
    0x03: "note",
    0x04: "note",
    0x05: "note",
    0x06: "note",
    0x07: "measure",
    0x08: "beat",
    0x09: "endpos",
    0x0a: "endpos",
}

EVENT_ID_REVERSE = {EVENT_ID_MAP[k]: k for k in EVENT_ID_MAP}

NOTE_MAPPING = {
    'drum': {
        0x00: "hihat",
        0x01: "snare",
        0x02: "bass",
        0x03: "hightom",
        0x04: "lowtom",
        0x05: "rightcymbal",
        0x06: "auto",
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
    "auto": 0x06,
}

########################
#   DSQ parsing code   #
########################
def parse_event_block(mdata, game):
    packet_data = {}

    timestamp, cmd, param1, param2 = struct.unpack("<IBBH", mdata[0:8])
    timestamp *= 4

    event_name = EVENT_ID_MAP[cmd]

    if event_name == "note":
        packet_data['sound_id'] = param2
        packet_data['volume'] = param1
        packet_data['note'] = NOTE_MAPPING[game][cmd]

        if packet_data['note'] == "auto":
            packet_data['auto_volume'] = 1
            packet_data['auto_note'] = 1

    return {
        "name": event_name,
        'timestamp': timestamp,
        'timestamp_ms': timestamp / 300,
        "data": packet_data
    }


def read_dsq1_data(data, game_type, difficulty, is_metadata):
    output = {
        "beat_data": []
    }

    if data is None:
        return None

    unk_sys = 0
    time_division = 300
    beat_division = 480

    output['header'] = {
        "unk_sys": unk_sys,
        "difficulty": difficulty,
        "is_metadata": is_metadata,
        "game_type": game_type,
        "time_division": time_division,
        "beat_division": beat_division,
    }

    header_size = 0
    entry_size = 0x08
    entry_count = len(data) // entry_size

    for i in range(entry_count):
        mdata = data[header_size + (i * entry_size):header_size + (i * entry_size) + entry_size]
        part = ["drum", "guitar", "bass", "open"][game_type]
        parsed_data = parse_event_block(mdata, part)

        if parsed_data:
            output['beat_data'].append(parsed_data)

    return output


def remove_extra_beats(chart):
    new_beat_data = []
    found_measures = []

    for x in sorted(chart['beat_data'], key=lambda x: int(x['timestamp'])):
        if x['name'] == "measure":
            found_measures.append(x['timestamp'])

    discarded_beats = []
    for x in sorted(chart['beat_data'], key=lambda x: int(x['timestamp'])):
        if x['name'] == "beat" and x['timestamp'] in found_measures:
            discarded_beats.append(x['timestamp'])
            continue

        new_beat_data.append(x)

    for idx, x in enumerate(new_beat_data):
        if x['name'] == "measure" and x['timestamp'] in discarded_beats:
            new_beat_data[idx]['merged_beat'] = True

    chart['beat_data'] = new_beat_data

    return chart


def parse_chart_intermediate(chart, game_type, difficulty, is_metadata):
    chart_raw = read_dsq1_data(chart, game_type, difficulty, is_metadata)

    if not chart_raw:
        return None

    chart_raw = remove_extra_beats(chart_raw)

    return chart_raw


def generate_json_from_dsq1(params):
    output_data = {}

    def get_data(params, game_type, difficulty, is_metadata):
        part = ["drum", "guitar", "bass", "open"][game_type]
        diff = ['nov', 'bsc', 'adv', 'ext', 'mst'][difficulty]

        if 'input_split' in params and part in params['input_split'] and diff in params['input_split'][part] and params['input_split'][part][diff] and os.path.exists(params['input_split'][part][diff]):
            data = open(params['input_split'][part][diff], "rb").read()
            return (data, game_type, difficulty, is_metadata)

        return None

    raw_charts = [
        # Drum
        get_data(params, 0, 0, False),
        get_data(params, 0, 1, False),
        get_data(params, 0, 2, False),
        get_data(params, 0, 3, False),
        get_data(params, 0, 4, False),
    ]
    raw_charts = [x for x in raw_charts if x is not None]

    musicid = params.get('musicid', None) or 0

    output_data['musicid'] = musicid
    output_data['format'] = Dsq1Format.get_format_name()

    charts = []
    for chart_info in raw_charts:
        chart, game_type, difficulty, is_metadata = chart_info

        parsed_chart = parse_chart_intermediate(chart, game_type, difficulty, is_metadata)

        if not parsed_chart:
            continue

        charts.append(parsed_chart)
        charts[-1]['header']['musicid'] = musicid

    output_data['charts'] = charts

    return json.dumps(output_data, indent=4, sort_keys=True)


class Dsq1Format:
    @staticmethod
    def get_format_name():
        return "Dsq1"

    @staticmethod
    def to_json(params):
        return generate_json_from_dsq1(params)

    @staticmethod
    def to_chart(params):
        raise NotImplementedError()

    @staticmethod
    def is_format(filename):
        return False


def get_class():
    return Dsq1Format
