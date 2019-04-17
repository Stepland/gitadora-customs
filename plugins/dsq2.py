import collections
import copy
import json
import os
import shutil
import struct
import threading
from lxml import etree
from lxml.builder import E
import uuid

import helper
import mdb
import eamxml
import audio
import vas3tool
import wavbintool
import tmpfile

import plugins.wav as wav

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


def add_song_info(charts, music_id, music_db):
    song_info = None

    if music_db and music_db.endswith(".csv") or not music_db:
        song_info = mdb.get_song_info_from_csv(music_db if music_db else "gitadora_music.csv", music_id)

    if song_info is None or music_db and music_db.endswith(".xml") or not music_db:
        song_info = mdb.get_song_info_from_mdb(music_db if music_db else "mdb_xg.xml", music_id)

    for chart_idx in range(len(charts)):
        chart = charts[chart_idx]

        if not song_info:
            continue

        game_type = ["drum", "guitar", "bass", "open"][chart['header']['game_type']]

        if 'title' in song_info:
            charts[chart_idx]['header']['title'] = song_info['title']

        if 'artist' in song_info:
            charts[chart_idx]['header']['artist'] = song_info['artist']

        if 'classics_difficulty' in song_info:
            diff_idx = (chart['header']['game_type'] * 4) + chart['header']['difficulty']

            if diff_idx < len(song_info['classics_difficulty']):
                difficulty = song_info['classics_difficulty'][diff_idx]
            else:
                difficulty = 0

            charts[chart_idx]['header']['level'] = {
                game_type: difficulty * 10
            }

        if 'bpm' in song_info:
            charts[chart_idx]['header']['bpm'] = song_info['bpm']

        if 'bpm2' in song_info:
            charts[chart_idx]['header']['bpm2'] = song_info['bpm2']

    return charts


def filter_charts(charts, params):
    filtered_charts = []

    for chart in charts:
        if chart['header']['is_metadata'] != 0:
            continue

        part = ["drum", "guitar", "bass", "open"][chart['header']['game_type']]
        has_all = 'all' in params['parts']
        has_part = part in params['parts']
        if not has_all and not has_part:
            filtered_charts.append(chart)
            continue

        diff = ['nov', 'bsc', 'adv', 'ext', 'mst'][chart['header']['difficulty']]
        has_min = 'min' in params['difficulty']
        has_max = 'max' in params['difficulty']
        has_all = 'all' in params['difficulty']
        has_diff = diff in params['difficulty']

        if not has_min and not has_max and not has_all and not has_diff:
            filtered_charts.append(chart)
            continue

    for chart in filtered_charts:
        charts.remove(chart)

    return charts


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
#   DSQ parsing code   #
########################
def parse_event_block(mdata, game, difficulty, is_metadata=False):
    packet_data = {}

    timestamp, cmd, param1, param2 = struct.unpack("<IBBH", mdata[0:8])

    game_type_id = {"drum": 0, "guitar": 1, "bass": 2, "open": 3}[game]

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


def read_dsq2_data(data, game_type, difficulty, is_metadata):
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
        parsed_data = parse_event_block(mdata, part, difficulty, is_metadata=is_metadata)

        if parsed_data:
            if parsed_data['name'] == "measure":
                import copy
                pd = copy.deepcopy(parsed_data)
                pd['name'] = "beat"
                output['beat_data'].append(pd)

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
    chart_raw = read_dsq2_data(chart, game_type, difficulty, is_metadata)

    if not chart_raw:
        return None

    chart_raw = remove_extra_beats(chart_raw)

    return chart_raw


def generate_json_from_dsq2(params):
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
    output_data['format'] = Dsq2Format.get_format_name()

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

    charts = add_song_info(charts, musicid, params['musicdb'])
    charts = filter_charts(charts, params)
    charts, guitar_charts, bass_charts, open_charts = split_charts_by_parts(charts)

    if combine_guitars:
        guitar_charts, bass_charts = combine_guitar_charts(guitar_charts, bass_charts)

    # Merge all charts back together after filtering, merging guitars etc
    charts += guitar_charts
    charts += bass_charts
    charts += open_charts

    output_data['charts'] = charts

    return json.dumps(output_data, indent=4, sort_keys=True)


class Dsq2Format:
    @staticmethod
    def get_format_name():
        return "Dsq2"

    @staticmethod
    def to_json(params):
        return generate_json_from_dsq2(params)

    @staticmethod
    def to_chart(params):
        super()

    @staticmethod
    def is_format(filename):
        return False


def get_class():
    return Dsq2Format
