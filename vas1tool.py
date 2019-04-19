# TODO: Remove unneeded code
# TODO: Add support for audio metadata
# TODO: Figure out differences between GF and DM VAS archives

import argparse
import io
import json
import math
import numpy
import os
import pydub
import struct
import sys
import wavfile
import pydub

import audio
import tmpfile
import helper

FLAG_MAP = {
    "DefaultSound": 0x04,
    "NoFilename": 0x0100
}

def read_vas3(input_filename, output_folder, force_hex=False, mix_audio=False, is_guitar=False):
    data = open(input_filename, "rb").read()

    entry_count = struct.unpack("<I", data[0x00:0x04])[0]
    entry_start = 0x04

    if entry_count <= 0:
        print("No files to extract")
        exit(1)



    default_hihat = 0x64
    default_snare = 0x26
    default_bass = 0x24
    default_hightom = 0x30
    default_lowtom = 0x29
    default_rightcymbal = 0x31
    default_leftcymbal = 0xfff0
    default_floortom = 0xfff1
    default_leftpedal = 0xfff2

    entries = []
    for i in range(entry_count):
        # sound_flag seems to be related to defaults. If something is set to default, it is 0x02. Else it's 0x04 (for GDXG). Always 0 for GDXH?
        # entry_unk4 seems to always be 255??
        metadata_offset, offset, filesize = struct.unpack("<III", data[entry_start+(i*0x0c):entry_start+(i*0x0c)+0x0c])
        metadata_unk1_1, metadata_unk1_2, metadata_unk1_3, sound_id, instrument_id, metadata_unk2_2, metadata_unk2_3, metadata_unk2_4, metadata_unk3, sample_rate = struct.unpack("<BBBBBBBBHH", data[entry_start+metadata_offset+(entry_count*0x0c):entry_start+metadata_offset+(entry_count*0x0c)+0x0c])
        sample_rate *= 2

        #output_filename = os.path.join(basepath, "{}.wav".format(entry['filename']))

        print("%04x | %08x %08x %08x | %02x %02x %02x %02x  %02x %02x %02x %02x  %04x  %04x | %08x" % (i, metadata_offset, offset, filesize, metadata_unk1_1, metadata_unk1_2, metadata_unk1_3, sound_id, instrument_id, metadata_unk2_2, metadata_unk2_3, metadata_unk2_4, sample_rate, metadata_unk3, entry_start+metadata_offset+(entry_count*0x0c)))

        offset += ((entry_count * 0x0c) * 2) + 4

        entries.append((offset, filesize, sound_id))

    entries.append(len(data))

    if output_folder:
        basepath = output_folder
    else:
        basepath = os.path.splitext(os.path.basename(input_filename))[0]

    if not os.path.exists(basepath):
        os.makedirs(basepath)

    metadata = {
        'type': "GDXG" if is_guitar else "GDXH",
        'version': 1,
        'defaults': {
            'default_hihat': default_hihat,
            'default_snare': default_snare,
            'default_bass': default_bass,
            'default_hightom': default_hightom,
            'default_lowtom': default_lowtom,
            'default_rightcymbal': default_rightcymbal,
            'default_leftcymbal': default_leftcymbal,
            'default_floortom': default_floortom,
            'default_leftpedal': default_leftpedal,
        },
        'gdx_type_unk1': 0,
        'gdx_volume_flag': 1,
        'entries': [],
    }

    for idx, entry_info in enumerate(entries[:-1]):
        entry, filesize, sound_id = entry_info
        #filesize = entries[idx + 1] - entry

        output_filename = os.path.join(basepath, "%04x.pcm" % (idx))

        print("Extracting", output_filename)
        with open(output_filename, "wb") as outfile:
            outfile.write(struct.pack(">IHHB", filesize, 0, sample_rate if is_guitar else 44100, 1))
            outfile.write(bytearray([0] * 7))
            outfile.write(bytearray([0] * 0x800))
            outfile.write(data[entry:entry+filesize])

        audio.get_wav_from_pcm(output_filename)
        os.remove(output_filename)

        volume = 127
        pan = 64

        metadata['entries'].append({
            'sound_id': sound_id,
            'filename': "",
            'volume': volume,
            'pan': pan,
            'extra': 255, # Unknown
            'flags': ['NoFilename'],
        })

    open(os.path.join(basepath, "metadata.json"), "w").write(json.dumps(metadata, indent=4))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Input file', required=True)
    parser.add_argument('-o', '--output', help='Output file', required=True)
    parser.add_argument('-m', '--mix', action='store_true', help='Mix output files using volume and pan parameters', required=False, default=False)
    parser.add_argument('-g', '--guitar', action='store_true', help='Is extracting guitar archive', required=False, default=False)
    parser.add_argument('-f', '--force-hex', action='store_true', help='Force hex filenames', required=False, default=False)
    args = parser.parse_args()

    read_vas3(args.input, args.output, args.force_hex, args.mix, args.guitar)