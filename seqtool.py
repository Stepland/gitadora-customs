# Used for SQ2/SQ3 primarily
import argparse
import glob
import importlib
import json
import os
import shutil
import threading

import tmpfile

import wavbintool
import vas3tool
import ifs
import eamxml
import event

import seqtool_main

def main():
    parser = argparse.ArgumentParser()
    input_group = parser.add_argument_group('input')
    input_group.add_argument('--input', help='Input file/folder')
    input_group.add_argument('--input-format', help='Input file format')
    input_group.add_argument('--sound-folder', help='Input folder containing sounds', required=True)
    input_group.add_argument('--event-file', help='Input file containing event information (for SQ2/SQ3)')

    input_split_group = parser.add_argument_group('input_split')
    for part in ['drum', 'guitar', 'bass', 'open', 'guitar2']:
        input_split_group.add_argument('--input-%s-nov' % part, help="Novice %s chart input" % part)
        input_split_group.add_argument('--input-%s-bsc' % part, help="Basic %s chart input" % part)
        input_split_group.add_argument('--input-%s-adv' % part, help="Advanced %s chart input" % part)
        input_split_group.add_argument('--input-%s-ext' % part, help="Extreme %s chart input" % part)
        input_split_group.add_argument('--input-%s-mst' % part, help="Master %s chart input" % part)

    parser.add_argument('--output', help='Output file/folder', required=True)
    parser.add_argument('--output-format', help='Output file format', required=True)

    parser.add_argument('--parts', nargs='*', choices=['drum', 'guitar', 'bass', 'open', 'all'], default="all")
    parser.add_argument('--difficulty', nargs='*', choices=['nov', 'bsc', 'adv', 'ext', 'mst', 'all', 'max', 'min'], default="all")

    parser.add_argument('--music-id', type=int, help="Force a music ID", default=None)

    args = parser.parse_args()

    # Clean parts and difficulty
    if 'all' in args.parts:
        args.parts = ['drum', 'guitar', 'bass', 'open']

    if 'all' in args.difficulty:
        args.difficulty = ['nov', 'bsc', 'adv', 'ext', 'mst']
    elif 'min' in args.difficulty:
        args.difficulty = ['min']
    elif 'max' in args.difficulty:
        args.difficulty = ['max']

    params_drum = {
        "input_format": args.input_format if args.input_format else None,
        "output": args.output,
        "output_format": args.output_format,
        "sound_folder": args.sound_folder,
        "sound_metadata": seqtool_main.get_sound_metadata(args.sound_folder, "drum"),
        "parts": args.parts,
        "difficulty": args.difficulty,
        "musicid": args.music_id,
        "input_split": {
            "drum": {
                "bsc": args.input_drum_bsc,
                "adv": args.input_drum_adv,
                "ext": args.input_drum_ext,
            },
        },
    }

    params_guitar = {
        "input_format": args.input_format if args.input_format else None,
        "output": args.output,
        "output_format": args.output_format,
        "sound_folder": args.sound_folder,
        "sound_metadata": seqtool_main.get_sound_metadata(args.sound_folder, "guitar"),
        "parts": args.parts,
        "difficulty": args.difficulty,
        "musicid": args.music_id,
        "input_split": {
            "guitar": {
                "bsc": args.input_guitar_bsc,
                "adv": args.input_guitar_adv,
                "ext": args.input_guitar_ext,
            },
            "bass": {
                "bsc": args.input_bass_bsc,
                "adv": args.input_bass_adv,
                "ext": args.input_bass_ext,
            },
            "open": {
                "bsc": args.input_open_bsc,
                "adv": args.input_open_adv,
                "ext": args.input_open_ext,
            },
        },
    }

    seqtool_main.add_task(params_drum)
    seqtool_main.add_task(params_guitar)
    seqtool_main.run_tasks()


if __name__ == "__main__":
    main()