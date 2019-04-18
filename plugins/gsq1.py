import json
import os
import struct

USE_THREADS = True

EVENT_ID_MAP = {
    0x00: "note",
    0x10: "measure",
    0x20: "note",
    0x40: "note",
    0x60: "note",
}

EVENT_ID_REVERSE = {EVENT_ID_MAP[k]: k for k in EVENT_ID_MAP}

NOTE_MAPPING = {
    'guitar': {
        0x01: "g_rxx",
        0x02: "g_xgx",
        0x03: "g_rgx",
        0x04: "g_xxb",
        0x05: "g_rxb",
        0x06: "g_xgb",
        0x07: "g_rgb",
        0x08: "auto",
        0x10: 'g_open',
    },

    'bass': {
        0x01: "b_rxx",
        0x02: "b_xgx",
        0x03: "b_rgx",
        0x04: "b_xxb",
        0x05: "b_rxb",
        0x06: "b_xgb",
        0x07: "b_rgb",
        0x08: "auto",
        0x10: 'b_open',
    },

    'open': {
        0x01: "g_rxx",
        0x02: "g_xgx",
        0x03: "g_rgx",
        0x04: "g_xxb",
        0x05: "g_rxb",
        0x06: "g_xgb",
        0x07: "g_rgb",
        0x08: "auto",
        0x10: 'g_open',
    },
}

REVERSE_NOTE_MAPPING = {
    "auto": 0x08,

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


def split_charts_by_parts(charts):
    guitar_charts = []
    bass_charts = []
    open_charts = []

    for chart in charts:
        if chart['header']['is_metadata'] != 0:
            continue

        game_type = ["drum", "guitar", "bass", "open"][chart['header']['game_type']]
        if game_type == "guitar":
            guitar_charts.append(chart)
        elif game_type == "bass":
            bass_charts.append(chart)
        elif game_type == "open":
            open_charts.append(chart)

    # Remove charts from chart list
    for chart in guitar_charts:
        charts.remove(chart)

    for chart in bass_charts:
        charts.remove(chart)

    for chart in open_charts:
        charts.remove(chart)

    return charts, guitar_charts, bass_charts, open_charts


def combine_guitar_charts(guitar_charts, bass_charts):
    # Combine guitar and bass charts
    parsed_bass_charts = []

    for chart in guitar_charts:
        # Find equivalent chart
        for chart2 in bass_charts:
            if chart['header']['difficulty'] != chart2['header']['difficulty']:
                continue

            if 'level' in chart2['header']:
                if 'level' not in chart['header']:
                    chart['header']['level'] = {}

                for k in chart2['header']['level']:
                    chart['header']['level'][k] = chart2['header']['level'][k]

                for event in chart2['timestamp'][timestamp_key]:
                    if event['name'] != "note":
                        continue

                    if timestamp_key not in chart['timestamp']:
                        chart['timestamp'][timestamp_key] = []

                    chart['timestamp'][timestamp_key].append(event)

            parsed_bass_charts.append(chart2)

    for chart in parsed_bass_charts:
        bass_charts.remove(chart)

    return guitar_charts, bass_charts


def add_note_durations(chart, sound_metadata):
    duration_lookup = {}

    if not sound_metadata or 'entries' not in sound_metadata:
        return chart

    for entry in sound_metadata['entries']:
        duration_lookup[entry['sound_id']] = entry.get('duration', 0)

    for k in chart['timestamp']:
        for i in range(0, len(chart['timestamp'][k])):
            if chart['timestamp'][k][i]['name'] in ['note', 'auto']:
                chart['timestamp'][k][i]['data']['note_length'] = int(round(duration_lookup.get(chart['timestamp'][k][i]['data']['sound_id'], 0) * 300))

    return chart


########################
#   GSQ parsing code   #
########################
def parse_event_block(mdata, game):
    packet_data = {}

    timestamp, param1, param2, cmd = struct.unpack("<HHHH", mdata[0:8])
    param3 = cmd & 0xff0f
    cmd &= 0x00f0

    if timestamp == 0xffff:
        timestamp = 0xffffffff
    else:
        timestamp *= 4

    event_name = EVENT_ID_MAP[cmd]

    if cmd in [0x00, 0x20, 0x40, 0x60]:
        packet_data['sound_id'] = param1
        packet_data['volume'] = 127

        if (cmd & 0x40) != 0:
            packet_data['note'] = NOTE_MAPPING[game][0x10] # open note
            packet_data['auto_unk'] = param3
        else:
            packet_data['note'] = NOTE_MAPPING[game][param3 & 0x0f] # note

        if packet_data['note'] == "auto":
            packet_data['auto_volume'] = 1
            packet_data['auto_note'] = 1

        is_wail = (cmd & 0x20) != 0
        packet_data['wail_misc'] = 1 if is_wail else 0
        packet_data['guitar_special'] = 1 if is_wail else 0

    elif cmd not in [0x10]:
        print("Unknown command %04x %02x" % (timestamp, cmd))
        exit(1)

    return {
        "name": event_name,
        'timestamp': timestamp,
        'timestamp_ms': timestamp / 300,
        "data": packet_data
    }


def read_gsq1_data(data, game_type, difficulty, is_metadata):
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


def parse_chart_intermediate(chart, game_type, difficulty, is_metadata):
    chart_raw = read_gsq1_data(chart, game_type, difficulty, is_metadata)

    if not chart_raw:
        return None

    return chart_raw


def generate_json_from_gsq1(params):
    combine_guitars = params['merge_guitars'] if 'merge_guitars' in params else False
    output_data = {}

    def get_data(params, game_type, difficulty, is_metadata):
        part = ["drum", "guitar", "bass", "open"][game_type]
        diff = ['nov', 'bsc', 'adv', 'ext', 'mst'][difficulty]

        if 'input_split' in params and part in params['input_split'] and diff in params['input_split'][part] and params['input_split'][part][diff] and os.path.exists(params['input_split'][part][diff]):
            data = open(params['input_split'][part][diff], "rb").read()
            return (data, game_type, difficulty, is_metadata)

        return None

    raw_charts = [
        # Guitar
        get_data(params, 1, 0, False),
        get_data(params, 1, 1, False),
        get_data(params, 1, 2, False),
        get_data(params, 1, 3, False),
        get_data(params, 1, 4, False),

        # Bass
        get_data(params, 2, 0, False),
        get_data(params, 2, 1, False),
        get_data(params, 2, 2, False),
        get_data(params, 2, 3, False),
        get_data(params, 2, 4, False),

        # Open
        get_data(params, 3, 0, False),
        get_data(params, 3, 1, False),
        get_data(params, 3, 2, False),
        get_data(params, 3, 3, False),
        get_data(params, 3, 4, False),
    ]
    raw_charts = [x for x in raw_charts if x is not None]

    musicid = params.get('musicid', None) or 0

    output_data['musicid'] = musicid
    output_data['format'] = Gsq1Format.get_format_name()

    charts = []
    for chart_info in raw_charts:
        chart, game_type, difficulty, is_metadata = chart_info

        parsed_chart = parse_chart_intermediate(chart, game_type, difficulty, is_metadata)

        if not parsed_chart:
            continue

        game_type = ["drum", "guitar", "bass", "open"][parsed_chart['header']['game_type']]
        if game_type in ["guitar", "bass", "open"]:
            parsed_chart = add_note_durations(parsed_chart, params.get('sound_metadata', []))

        charts.append(parsed_chart)
        charts[-1]['header']['musicid'] = musicid

    charts, guitar_charts, bass_charts, open_charts = split_charts_by_parts(charts)

    if combine_guitars:
        guitar_charts, bass_charts = combine_guitar_charts(guitar_charts, bass_charts)

    # Merge all charts back together after filtering, merging guitars etc
    charts += guitar_charts
    charts += bass_charts
    charts += open_charts

    output_data['charts'] = charts

    return json.dumps(output_data, indent=4, sort_keys=True)


class Gsq1Format:
    @staticmethod
    def get_format_name():
        return "Gsq1"

    @staticmethod
    def to_json(params):
        return generate_json_from_gsq1(params)

    @staticmethod
    def to_chart(params):
        raise NotImplementedError()

    @staticmethod
    def is_format(filename):
        return False


def get_class():
    return Gsq1Format
