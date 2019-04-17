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


def generate_output_data(chart, division=192):
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

        last_event_timestamp = sorted(events, key=lambda x:x['timestamp'])[-1]['timestamp_ms']

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

        for event in sorted(chart['charts'][0]['beat_data'], key=lambda x:x['timestamp']):
            events.append(event)

        return events


    events = get_events_from_chart(chart)

    measures = get_measures(events)
    bpm_per_measure = get_bpm_per_measure(measures)
    bpm_list = get_bpm_list(bpm_per_measure)
    mapping = calculate_timestamp_mapping(events, measures, bpm_per_measure, division)

    display_bar = True

    output_data = {}
    used_sound_ids = []
    for event in events:
        measure_idx, beat_idx = get_nearest_beat(mapping, event['timestamp_ms'])

        if measure_idx not in output_data:
            output_data[measure_idx] = {
                0x08: [0x00] * division, # BPM
                0x50: [0x00] * division, # Show measure bar
                0x51: [0x00] * division, # Show beat bar
            }

            for k in reverse_dtx_mapping:
                output_data[measure_idx][k] = [0x00] * division

        if event['timestamp'] in bpm_per_measure:
            output_data[measure_idx][0x08][beat_idx] = bpm_list.index(bpm_per_measure[event['timestamp']]) + 1

        if event['name'] == "baron":
            display_bar = True

        elif event['name'] == "baroff":
            display_bar = False

        elif event['name'] == "measure":
            output_data[measure_idx][0x50][beat_idx] = 0x01 if display_bar else 0x00

        elif event['name'] == "beat":
            output_data[measure_idx][0x51][beat_idx] = 0x01 if display_bar else 0x00

        elif event['name'] == "note":
            if event['data']['note'] == "auto":
                continue

            output_data[measure_idx][dtx_mapping[event['data']['note']]][beat_idx] = event['data']['sound_id']

            if event['data']['sound_id'] not in used_sound_ids:
                used_sound_ids.append(event['data']['sound_id'])

    return {
        'data': output_data,
        'sound_ids': used_sound_ids,
        'bpms': bpm_list,
    }



def create_dtx_from_json(params):
    output_json = {}

    output_data = generate_output_data(json.loads(params['input']))

    print("""#TITLE: (no title)
    #ARTIST: (no artist)
    #DLEVEL: 0
    #GLEVEL: 0
    #BLEVEL: 0""")

    for sound_id in sorted(output_data['sound_ids']):
        print("#WAV%02X: %04x.wav" % (sound_id, sound_id))

    print("""#WAVZZ bgm.wav
    #00001: ZZ
    #000C2: 02
    """)

    print("#BPM %f" % output_data['bpms'][0])
    for i, bpm in enumerate(output_data['bpms']):
        print("#BPM%02d %f" % (i + 1, output_data['bpms'][i]))


    for measure_idx in output_data['data']:
        for eidx in output_data['data'][measure_idx]:
            if eidx == 0x02:
                print("#%03d%02X: %f" % (measure_idx, eidx, output_data['data'][measure_idx][eidx]))

            else:
                print("#%03d%02X: %s" % (measure_idx, eidx, "".join(["%02X" % x for x in output_data['data'][measure_idx][eidx]])))


    return json.dumps(output_json, indent=4, sort_keys=True)


class DtxFormat:
    @staticmethod
    def get_format_name():
        return "DTX"

    # @staticmethod
    # def to_json(params):
    #     return create_json_from_dtx(params)

    @staticmethod
    def to_chart(params):
        return create_dtx_from_json(params)

    @staticmethod
    def is_format(filename):
        # How to determine a DTX?
        return False


def get_class():
    return DtxFormat
