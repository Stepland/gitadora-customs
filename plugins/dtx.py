# Docs:
# https://osdn.net/projects/dtxmania/wiki/DTX%20data%20format
# https://osdn.net/projects/dtxmania/wiki/%E3%83%81%E3%83%A3%E3%83%B3%E3%83%8D%E3%83%AB%E5%AE%9A%E7%BE%A9%E8%A1%A8

# Auto lane override details: https://osdn.net/projects/dtxmania/ticket/26338

import copy
from fractions import Fraction
import json
import math
from numpy import base_repr
import os
import re

import audio

dtx_bonus_mapping = {
    "leftcymbal": 0x01,
    "hihat": 0x02,
    "leftpedal": 0x03,
    "snare": 0x04,
    "hightom": 0x05,
    "bass": 0x06,
    "lowtom": 0x07,
    "floortom": 0x08,
    "rightcymbal": 0x09,
}

drum_mapping = {
    "hihat": 0x11,
    "snare": 0x12,
    "bass": 0x13,
    "hightom": 0x14,
    "lowtom": 0x15,
    "rightcymbal": 0x16,
    "floortom": 0x17,
    "leftcymbal": 0x1a,
    "leftpedal": 0x1b,
}

guitar_mapping = {
    "g_open": 0x20,
    "g_xxbxx": 0x21,
    "g_xgxxx": 0x22,
    "g_xgbxx": 0x23,
    "g_rxxxx": 0x24,
    "g_rxbxx": 0x25,
    "g_rgxxx": 0x26,
    "g_rgbxx": 0x27,
    "g_xxb": 0x21,
    "g_xgx": 0x22,
    "g_xgb": 0x23,
    "g_rxx": 0x24,
    "g_rxb": 0x25,
    "g_rgx": 0x26,
    "g_rgb": 0x27,
    "g_xxxyx": 0x93,
    "g_xxbyx": 0x94,
    "g_xgxyx": 0x95,
    "g_xgbyx": 0x96,
    "g_rxxyx": 0x97,
    "g_rxbyx": 0x98,
    "g_rgxyx": 0x99,
    "g_rgbyx": 0x9a,
    "g_xxxxp": 0x9b,
    "g_xxbxp": 0x9c,
    "g_xgxxp": 0x9d,
    "g_xgbxp": 0x9e,
    "g_rxxxp": 0x9f,
    "g_rxbxp": 0xa9,
    "g_rgxxp": 0xaa,
    "g_rgbxp": 0xab,
    "g_xxxyp": 0xac,
    "g_xxbyp": 0xad,
    "g_xgxyp": 0xae,
    "g_xgbyp": 0xaf,
    "g_rxxyp": 0xd0,
    "g_rxbyp": 0xd1,
    "g_rgxyp": 0xd2,
    "g_rgbyp": 0xd3,
}

bass_mapping = {
    "b_open": 0xa0,
    "b_xxbxx": 0xa1,
    "b_xgxxx": 0xa2,
    "b_xgbxx": 0xa3,
    "b_rxxxx": 0xa4,
    "b_rxbxx": 0xa5,
    "b_rgxxx": 0xa6,
    "b_rgbxx": 0xa7,
    "b_xxb": 0xa1,
    "b_xgx": 0xa2,
    "b_xgb": 0xa3,
    "b_rxx": 0xa4,
    "b_rxb": 0xa5,
    "b_rgx": 0xa6,
    "b_rgb": 0xa7,
    "b_xxxyx": 0xc5,
    "b_xxbyx": 0xc6,
    "b_xgxyx": 0xc8,
    "b_xgbyx": 0xc9,
    "b_rxxyx": 0xca,
    "b_rxbyx": 0xcb,
    "b_rgxyx": 0xcc,
    "b_rgbyx": 0xcd,
    "b_xxxxp": 0xce,
    "b_xxbxp": 0xcf,
    "b_xgxxp": 0xda,
    "b_xgbxp": 0xdb,
    "b_rxxxp": 0xdc,
    "b_rxbxp": 0xdd,
    "b_rgxxp": 0xde,
    "b_rgbxp": 0xdf,
    "b_xxxyp": 0xe1,
    "b_xxbyp": 0xe2,
    "b_xgxyp": 0xe3,
    "b_xgbyp": 0xe4,
    "b_rxxyp": 0xe5,
    "b_rxbyp": 0xe6,
    "b_rgxyp": 0xe7,
    "b_rgbyp": 0xe8,
}

dtx_mapping = {
    "auto": 0x61,
}
dtx_mapping.update(drum_mapping)
dtx_mapping.update(guitar_mapping)
dtx_mapping.update(bass_mapping)

reverse_dtx_mapping = {dtx_mapping[k]: k for k in dtx_mapping if k != "auto"}
reverse_dtx_mapping[0x1c] = "leftpedal"  # Because there are multiple mappings for the left pedal
reverse_dtx_mapping[0x18] = "hihat"  # Because there are multiple mappings for hihat

# TODO: How to handle ride? For now, just put it as an auto field
reverse_dtx_mapping[0x19] = "auto"  # RideCymbal

# For default note chips
reverse_dtx_mapping[0xb1] = "hihat"
reverse_dtx_mapping[0xb2] = "snare"
reverse_dtx_mapping[0xb3] = "bass"
reverse_dtx_mapping[0xb4] = "hightom"
reverse_dtx_mapping[0xb5] = "lowtom"
reverse_dtx_mapping[0xb6] = "rightcymbal"
reverse_dtx_mapping[0xb7] = "floortom"
reverse_dtx_mapping[0xb8] = "hihat"
reverse_dtx_mapping[0xbc] = "leftcymbal"
reverse_dtx_mapping[0xbd] = "leftpedal"
reverse_dtx_mapping[0xbe] = "leftpedal"

auto_play_ranges = list(range(0x61, 0x69 + 1)) + \
    list(range(0x70, 0x79 + 1)) + \
    list(range(0x80, 0x89 + 1)) + \
    list(range(0x90, 0x92 + 1))

default_note_events = list(range(0xb1, 0xb8 + 1)) + \
    list(range(0xbc, 0xbf + 1))  # b9 = ride, but we can't use the ride

drum_range = list(range(0x11, 0x1b + 1))

guitar_range = list(range(0x20, 0x27 + 1)) + \
    list(range(0x93, 0x9f + 1)) + \
    list(range(0xa9, 0xaf + 1)) + \
    list(range(0xd0, 0xd3 + 1))

bass_range = list(range(0xa0, 0xa7 + 1)) + \
    list(range(0xc5, 0xcf + 1)) + \
    list(range(0xda, 0xe8 + 1))


def convert_base36(val, padding):
    return base_repr(val, 36, padding=padding)[-padding:]


def create_json_from_dtx(params):
    pass


def create_dtx_from_json(params):
    def generate_output_data(chart, game_type, division=192):
        def get_last_bpm(bpms, offset):
            last_bpm = 0

            for k in bpms:
                if k <= offset:
                    last_bpm = k

            return bpms[last_bpm]


        def get_nearest_beat(beats, timestamp):
            nearest_timestamp = 0

            for k in beats:
                if timestamp == k:
                    nearest_timestamp = k
                    break

                if abs(timestamp - k) < abs(timestamp - nearest_timestamp):
                    nearest_timestamp = k

            return beats[nearest_timestamp]


        def get_measures(events):
            measures = []
            for event in events[:]:
                if event['name'] == "measure": # Measure
                    measures.append(event)

                    for event2 in events:
                        if event2['name'] == "beat" and event['timestamp'] == event2['timestamp']: # Beat
                            events.remove(event2)

            return measures


        def get_bpm_per_measure(measures):
            bpm_per_measure = {}

            for i in range(0, len(measures) - 1):
                time_diff = measures[i+1]['timestamp'] - measures[i]['timestamp']
                bpm = 300 / (time_diff / 4 / 60)
                bpm_per_measure[measures[i]['timestamp']] = bpm

            return bpm_per_measure


        def get_bpm_list(bpm_per_measure):
            bpm_list = []

            for k in bpm_per_measure:
                bpm = bpm_per_measure[k]

                if bpm not in bpm_list:
                    bpm_list.append(bpm)

            return bpm_list


        def calculate_timestamp_mapping(events, measures, bpm_per_measure, division=192):
            cur_pos = 0
            mapping = {}

            last_measure = None

            for measure_idx, measure in enumerate(measures):
                last_measure = measure
                bpm = get_last_bpm(bpm_per_measure, measure['timestamp'])
                beat_duration = ((4 * (1/bpm)) * 60) / division

                for i in range(0, division):
                    mapping[cur_pos] = (measure_idx, i)
                    cur_pos = cur_pos + beat_duration

            last_event = sorted(events, key=lambda x:x['timestamp'])[-1]
            last_event_timestamp = last_event['timestamp_ms']

            while cur_pos < last_event_timestamp:
                measure_idx += 1

                bpm = get_last_bpm(bpm_per_measure, last_measure['timestamp'])
                beat_duration = ((4 * (1/bpm)) * 60) / division

                for i in range(0, division):
                    mapping[cur_pos] = (measure_idx, i)
                    cur_pos = cur_pos + beat_duration

            return mapping


        def get_events_from_chart(chart):
            events = []

            for event in sorted(chart['beat_data'], key=lambda x:x['timestamp']):
                events.append(event)

            return events


        def simplify_measures(chart):
            def can_divide_measure(measure, n):
                div = len(measure) // n

                for j in range(0, div):
                    for k in range(1, n):
                        if measure[(j * n) + k] != 0:
                            return False

                return True

            for measure_idx in output_data:
                for event in list(output_data[measure_idx].keys()):
                    # Remove empty measures
                    if len([x for x in output_data[measure_idx][event] if x != 0]) == 0:
                        del output_data[measure_idx][event]
                        continue

                    # Simplify all measures that are evenly divisible
                    div_size = 1
                    for i in range(1, len(output_data[measure_idx][event]) + 1):
                        if len(output_data[measure_idx][event]) % i != 0:
                            continue

                        if can_divide_measure(output_data[measure_idx][event], i):
                            div_size = i

                    output_data[measure_idx][event] = [output_data[measure_idx][event][x] for x in range(0, len(output_data[measure_idx][event]), div_size)]

            return output_data

        def generate_hold_release_events(events):
            _events = []
            for event in events:
                _events.append(event)

                if event['name'] == "note":
                    if 'guitar_special' in event['data'] and event['data']['guitar_special'] & 0x02:
                        # Long note start
                        new_note = copy.deepcopy(event)
                        new_note['name'] = "_note_start"

                        _events.append(new_note)

                        # Long note end
                        new_note = copy.deepcopy(event)
                        new_note['name'] = "_note_release"

                        timestamp_offset = 0
                        while True:
                            new_timestamp = event['timestamp'] + event['data']['hold_duration'] - timestamp_offset

                            found_note = False
                            for event2 in events:
                                if event2['timestamp'] == new_timestamp and event2['name'] == "note":
                                    found_note = True
                                    timestamp_offset += 1
                                    break

                            if not found_note:
                                break

                        new_note['timestamp'] = new_timestamp
                        new_note['timestamp_ms'] = new_timestamp / 300

                        _events.append(new_note)

            return _events


        def generate_sound_id_map(events):
            used_sound_ids = {}
            sound_id_lookup = {}

            cur_sound_id = 1

            for event in events:
                if event['name'] == "note":
                    sound_key = "%d_%d" % (event['data']['sound_id'], event['data'].get('note_length', 0))

                    if sound_key not in sound_id_lookup:
                        sound_id_lookup[sound_key] = cur_sound_id
                        used_sound_ids[cur_sound_id] = {
                            'filename': "%04x" % event['data']['sound_id'],
                            'duration': event['data'].get('note_length', 0)
                        }
                        cur_sound_id += 1

                    event['data']['sound_id'] = sound_id_lookup[sound_key]

            return events, used_sound_ids


        events = get_events_from_chart(chart)
        events, used_sound_ids = generate_sound_id_map(events)
        events = generate_hold_release_events(events)
        measures = get_measures(events)
        bpm_per_measure = get_bpm_per_measure(measures)
        bpm_list = get_bpm_list(bpm_per_measure)
        mapping = calculate_timestamp_mapping(events, measures, bpm_per_measure, division)

        display_bar = True

        output_data = {}
        for event in events:
            measure_idx, beat_idx = get_nearest_beat(mapping, event['timestamp_ms'])

            if measure_idx not in output_data:
                output_data[measure_idx] = {
                    0x08: [0x00] * division, # BPM
                    0x50: [0x00] * division, # Show measure bar
                    0x51: [0x00] * division, # Show beat bar
                    0x2c: [0x00] * division, # Guitar long note
                    0x2d: [0x00] * division, # Bass long note
                    0xc2: [0x00] * division, # End position
                    0x28: [0x00] * division, # Guitar Wail
                    0xa8: [0x00] * division, # Bass Wail
                    0x4c: [0x00] * division, # Bonus note #1
                    0x4d: [0x00] * division, # Bonus note #2
                    0x4e: [0x00] * division, # Bonus note #3
                    0x4f: [0x00] * division, # Bonus note #4
                }

                for k in reverse_dtx_mapping:
                    output_data[measure_idx][k] = [0x00] * division

                for k in auto_play_ranges:
                    output_data[measure_idx][k] = [0x00] * division

            if event['timestamp'] in bpm_per_measure:
                output_data[measure_idx][0x08][beat_idx] = bpm_list.index(bpm_per_measure[event['timestamp']]) + 1

            if event['name'] == "baron":
                display_bar = True

            elif event['name'] == "baroff":
                display_bar = False

            elif event['name'] == "endpos":
                output_data[measure_idx][0xc2][beat_idx] = 0x01

            elif event['name'] == "measure":
                output_data[measure_idx][0x50][beat_idx] = 0x01 if display_bar else 0x00

            elif event['name'] == "beat":
                output_data[measure_idx][0x51][beat_idx] = 0x01 if display_bar else 0x00

            elif event['name'] == "note":
                if event['data']['note'] == "auto":
                    for note in auto_play_ranges:
                        if output_data[measure_idx][note][beat_idx] == 0:
                            break

                    output_data[measure_idx][note][beat_idx] = event['data']['sound_id']

                else:
                    output_data[measure_idx][dtx_mapping[event['data']['note']]][beat_idx] = event['data']['sound_id']

                if 'guitar_special' in event['data'] and event['data']['guitar_special'] & 0x01:
                    if event['data']['wail_misc'] == 2:
                        # Down wail
                        # Currently down wailing isn't supported by any simulator,
                        # so just use up wail's commands for now
                        wail_field = {
                            'd': -1,
                            'g': 0x28,
                            'b': 0xa8,
                            'o': 0x28,
                            'g1': 0x28,
                            'g2': 0xa8,
                        }[game_type]

                        wail_direction = 2

                    else:  # 0, 1, ?
                        # Up wail
                        wail_field = {
                            'd': -1,
                            'g': 0x28,
                            'b': 0xa8,
                            'o': 0x28,
                            'g1': 0x28,
                            'g2': 0xa8,
                        }[game_type]

                        wail_direction = 1

                    output_data[measure_idx][wail_field][beat_idx] = wail_direction

                if event['data'].get('bonus_note') and event['data']['note'] in dtx_bonus_mapping:
                    bonus_note_lane = 0x4f

                    while bonus_note_lane >= 0x4c:
                        if output_data[measure_idx][bonus_note_lane][beat_idx] != 0:
                            bonus_note_lane -= 1
                            continue

                        output_data[measure_idx][bonus_note_lane][beat_idx] = dtx_bonus_mapping[event['data']['note']]
                        break

                    if bonus_note_lane < 0x4c:
                        print("Couldn't find enough bonus note lanes")




        for event in events:
            longnote_fields = {
                'd': None,
                'g': 0x2c,
                'b': 0x2d,
                'o': 0x2c,
                'g1': 0x2c,
                'g2': 0x2d,
            }[game_type]

            if not longnote_fields:
                break

            if event['name'] == "_note_start":
                measure_idx, beat_idx = get_nearest_beat(mapping, event['timestamp_ms'])
                output_data[measure_idx][longnote_fields][beat_idx] = 0x01

            elif event['name'] == "_note_release":
                measure_idx, beat_idx = get_nearest_beat(mapping, event['timestamp_ms'])

                check_events = {
                    'g': guitar_range,
                    'b': bass_range,
                    'o': guitar_range,
                    'g1': guitar_range,
                    'g2': bass_range,
                }[game_type]

                while True:
                    updated = False

                    for check_event in check_events:
                        if measure_idx not in output_data or check_event not in output_data[measure_idx]:
                            continue

                        if output_data[measure_idx][check_event][beat_idx] != 0:
                            if beat_idx == 0:
                                measure_idx -= 1
                                beat_idx = division

                            beat_idx -= 1
                            updated = True
                            break

                    if not updated:
                        if measure_idx not in output_data:
                            output_data[measure_idx] = {
                                longnote_fields: [0x00] * division, # Long note
                            }

                        output_data[measure_idx][longnote_fields][beat_idx] = 0x01
                        break

        return {
            'data': simplify_measures(output_data),
            'sound_ids': used_sound_ids,
            'bpms': bpm_list,
        }


    output_json = {}

    input_json = json.loads(params['input'])
    output_folder = params.get('output', "")

    if 'format' in input_json:
        origin_format = "_%s" % input_json['format'].lower()
    else:
        origin_format = ""

    for chart in input_json['charts']:
        difficulty = ['nov', 'bsc', 'adv', 'ext', 'mst'][chart['header']['difficulty']]
        game_initial = ['d', 'g', 'b', 'o', 'g1', 'g2'][chart['header']['game_type']]
        sound_initial = ['drum', 'guitar', 'guitar', 'guitar', 'guitar', 'guitar'][chart['header']['game_type']]
        bgm_filename = ['_gbk.wav', 'd_bk.wav', 'dg_k.wav', 'd_bk.wav', 'd_bk.wav', 'd_bk.wav'][chart['header']['game_type']]

        output_data = generate_output_data(chart, game_initial)

        output_filename = "%s_%04d_%s%s.dtx" % (game_initial,
                                            input_json.get('musicid', 0),
                                            difficulty,
                                            origin_format)


        print("Saving", output_filename)
        output_filename = os.path.join(output_folder, output_filename)

        with open(output_filename, "w") as outfile:
            outfile.write("""#TITLE: (no title)
            #ARTIST: (no artist)
            #DLEVEL: 0
            #GLEVEL: 0
            #BLEVEL: 0\n""")


            comment_json = {
                'sound_lengths': {}
            }

            for k in output_data['sound_ids']:
                comment_json['sound_lengths'][k] = output_data['sound_ids'][k]['duration']

            outfile.write("#COMMENT %s\n" % json.dumps(comment_json))

            for k in output_data['sound_ids']:
                outfile.write("#WAV%s: %s\n" % (convert_base36(k, 2), os.path.join(sound_initial, "%s.wav" % output_data['sound_ids'][k]['filename'])))

            outfile.write("""#WAVZZ: %s
            #00001: ZZ
            #000C2: 02
            \n""" % (os.path.join(sound_initial, bgm_filename)))

            outfile.write("#BPM %f\n" % output_data['bpms'][0])
            for i, bpm in enumerate(output_data['bpms']):
                outfile.write("#BPM%02d %f\n" % (i + 1, output_data['bpms'][i]))


            for measure_idx in output_data['data']:
                for eidx in output_data['data'][measure_idx]:
                    if eidx == 0x02:
                        outfile.write("#%03d%02X: %f\n" % (measure_idx, eidx, output_data['data'][measure_idx][eidx]))

                    else:
                        outfile.write("#%03d%02X: %s\n" % (measure_idx, eidx, "".join([convert_base36(x, 2) for x in output_data['data'][measure_idx][eidx]])))


class DtxFormat:
    @staticmethod
    def get_format_name():
        return "DTX"

    @staticmethod
    def to_json(params):
        return create_json_from_dtx(params)

    @staticmethod
    def to_chart(params):
        return create_dtx_from_json(params)

    @staticmethod
    def is_format(filename):
        return False


def get_class():
    return DtxFormat
