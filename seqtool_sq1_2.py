# Used by older GFDM AC games
import argparse
import glob
import os

import seqtool_main

def main():
    parser = argparse.ArgumentParser()
    input_group = parser.add_argument_group('input')
    input_group.add_argument('--input-folder', help='Input folder with wildcard path (batch import)', default="")
    input_group.add_argument('--input-format', help='Input file format')
    input_group.add_argument('--sound-folder', help='Input folder containing sounds', required=True)

    input_split_group = parser.add_argument_group('input_split')
    for part in ['drum', 'guitar', 'bass', 'open']:
        input_split_group.add_argument('--input-%s-bsc' % part, help="Basic %s chart input" % part)
        input_split_group.add_argument('--input-%s-adv' % part, help="Advanced %s chart input" % part)
        input_split_group.add_argument('--input-%s-ext' % part, help="Extreme %s chart input" % part)

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
        args.difficulty = ['bsc', 'adv', 'ext']
    elif 'min' in args.difficulty:
        args.difficulty = ['min']
    elif 'max' in args.difficulty:
        args.difficulty = ['max']

    if '*' in args.input_folder:
        charts = glob.glob(args.input_folder)

        difficulty = ['bsc', 'adv', 'ext']
        parts_mapping = {
            'sp': "guitar",
            'sb': "bass",
            'op': "open",
        }

        for filename in charts:
            base_filename = os.path.splitext(os.path.basename(filename))[0]

            game_part = base_filename[0].upper()
            music_id = int(base_filename[1:5])
            diff = base_filename[5:8]
            part = None

            if game_part == 'G':
                part_key = base_filename[9:14]

                if part_key in parts_mapping:
                    part = parts_mapping[part_key]

            else:
                part = "drum"

            if not part or diff not in difficulty:
                continue

            attr_name = "input_%s_%s" % (part, diff)
            setattr(args, attr_name, filename)
            args.music_id = music_id

    params = {
        "input_format": args.input_format if args.input_format else None,
        "output": args.output,
        "output_format": args.output_format,
        "sound_folder": args.sound_folder,
        "sound_metadata": seqtool_main.get_sound_metadata(args.sound_folder),
        "parts": args.parts,
        "difficulty": args.difficulty,
        "musicid": args.music_id,
        "input_split": {
            "drum": {
                "bsc": args.input_drum_bsc,
                "adv": args.input_drum_adv,
                "ext": args.input_drum_ext,
            },
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
        "no_sounds": False,
    }

    seqtool_main.add_task(params)
    seqtool_main.run_tasks()

if __name__ == "__main__":
    main()