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
    input_group.add_argument('--sound-folder', help='Input folder containing sounds', default="")

    input_split_group = parser.add_argument_group('input_split')
    for part in ['drum', 'guitar', 'bass', 'guitar1', 'guitar2']:
        input_split_group.add_argument('--input-%s-bsc' % part, help="Basic %s chart input" % part)
        input_split_group.add_argument('--input-%s-adv' % part, help="Advanced %s chart input" % part)
        input_split_group.add_argument('--input-%s-ext' % part, help="Extreme %s chart input" % part)

    parser.add_argument('--output', help='Output file/folder', required=True)
    parser.add_argument('--output-format', help='Output file format', required=True)

    parser.add_argument('--parts', nargs='*', choices=['drum', 'guitar', 'bass', 'open', 'all'], default="all")
    parser.add_argument('--difficulty', nargs='*', choices=['nov', 'bsc', 'adv', 'ext', 'mst', 'all', 'max', 'min'], default="all")

    parser.add_argument('--no-sounds', action='store_true', help="Don't convert sound files", default=False)

    parser.add_argument('--music-id', type=int, help="Force a music ID", default=None)

    args = parser.parse_args()

    # Clean parts and difficulty
    if 'all' in args.parts:
        args.parts = ['drum', 'guitar', 'bass',  'guitar1', 'guitar2']

    if 'all' in args.difficulty:
        args.difficulty = ['bsc', 'adv', 'ext']
    elif 'min' in args.difficulty:
        args.difficulty = ['min']
    elif 'max' in args.difficulty:
        args.difficulty = ['max']

    if '*' in args.input_folder:
        charts = glob.glob(args.input_folder)

        difficulty = ['bsc', 'adv', 'ext']
        drum_parts = ['drum']
        guitar_parts = ['guitar', None, 'bass', 'guitar1', 'guitar2']
        parts = {
            'D': drum_parts,
            'G': guitar_parts
        }

        for filename in charts:
            base_filename = os.path.splitext(os.path.basename(filename))[0]

            game_part = base_filename[0].upper()
            music_id = int(base_filename[1:4])
            diff_idx = int(base_filename[4])
            part_idx = int(base_filename[5]) if game_part == 'G' else 0

            if game_part not in parts or part_idx > len(parts[game_part]) or not parts[game_part][part_idx]:
                continue

            attr_name = "input_%s_%s" % (parts[game_part][part_idx], difficulty[diff_idx])
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
            "guitar1": {
                "bsc": args.input_guitar1_bsc,
                "adv": args.input_guitar1_adv,
                "ext": args.input_guitar1_ext,
            },
            "guitar2": {
                "bsc": args.input_guitar2_bsc,
                "adv": args.input_guitar2_adv,
                "ext": args.input_guitar2_ext,
            }
        },
        "no_sounds": args.no_sounds,
    }

    seqtool_main.add_task(params)
    seqtool_main.run_tasks()

if __name__ == "__main__":
    main()