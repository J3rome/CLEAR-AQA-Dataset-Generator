import sqlite3
import json
import os
from operator import attrgetter
from shutil import rmtree as rmdir
import argparse

from pydub import AudioSegment
from pydub.silence import split_on_silence

from utils.audio_processing import get_perceptual_loudness
from utils.misc import init_random_seed

'''
Arguments definition
'''
parser = argparse.ArgumentParser()

parser.add_argument('--good_sounds_folder', type=str, default="./good-sounds",
                    help='Path to the good-sounds audio folder')

parser.add_argument('--good_sounds_database_filename', type=str, default="database.sqlite",
                    help='Path to the good-sounds sqlite database')

parser.add_argument('--output_path', type=str, default="./elementary_sounds",
                    help='Path were the extracted elementary sounds will be copied')

parser.add_argument('--output_definition_filename', type=str, default="elementary_sounds.json",
                    help='Filename for the json file that store the attributes of the elementary sounds')

parser.add_argument('--random_seed', type=int, default=42, help='Random seed')

# Preprocessing parameters
# FIXME : Write the help messages
parser.add_argument('--silence_threshold', type=float, default=-45,
                    help='')

parser.add_argument('--min_silence_duration', type=int, default=100,
                    help='')

parser.add_argument('--amplification_factor', type=float, default=-10,
                    help='')

parser.add_argument('--amplification_low_bound', type=float, default=-30.5,
                    help='')

parser.add_argument('--amplification_high_bound', type=float, default=-24.0,
                    help='')


def connect_db(database_path):
    """
    SQL Database connection
    """
    connection = sqlite3.connect(database_path)
    return connection.cursor()


def retrieve_CLEAR_elementary_sounds_infos_from_goodsounds_db(database):
    """
    SQL Query
    """
    # Super inefficient SQL query.. We need to sort in descending order to get the correct
    database.execute("SELECT instrument, note, octave, filename, reference, name from  \
                        ( \
                          SELECT sounds.instrument, sounds.note, sounds.octave, takes.filename, sounds.reference, packs.name from sounds   \
                          LEFT JOIN takes on takes.sound_id = sounds.id  \
                          LEFT JOIN packs on packs.id = sounds.pack_id  \
                            WHERE (  \
                            (sounds.instrument = 'flute' and sounds.octave IN (4, 5) and packs.name = 'flute_almudena_reference')  \
                            OR (sounds.instrument = 'trumpet' and sounds.octave IN (4, 5) and packs.name = 'trumpet_ramon_reference')  \
                            OR (sounds.instrument = 'violin' and sounds.octave IN (4, 5) and packs.name = 'violin_raquel_reference')  \
                            OR (sounds.instrument = 'clarinet' and sounds.octave IN (3, 4) and packs.name = 'clarinet_pablo_reference')  \
                            OR (sounds.instrument = 'cello' and sounds.octave IN (3, 4) and packs.name = 'cello_nico_improvement_recordings') \
                            OR (sounds.instrument = 'bass' and sounds.octave IN (3, 4) and packs.name = 'bass_alejandro_recordings') \
                            )  \
                            AND sounds.reference = 1  \
                            AND sounds.klass LIKE 'good-sound%'  \
                            AND takes.microphone = 'neumann' \
                            ORDER BY sounds.instrument, sounds.note, sounds.octave, takes.filename DESC \
                        ) \
                        GROUP BY instrument, note, octave")

    return db_rows_to_dict(database.fetchall())


def db_rows_to_dict(results):
    """
    Convert SQL rows to dict
    """
    sounds = []

    for row in results:
        sounds.append({
            'instrument': row[0],
            'note': row[1],
            'octave': row[2],
            'filename': row[3],
            'is_ref': row[4] == 1,
            'pack': row[5]
        })

    return sounds


def load_sounds_in_memory(sounds, good_sounds_folder):
    """
    Load audio segments into memory
    """
    print("Loading audio files in memory...")
    for sound in sounds:
        audio_segment = AudioSegment.from_wav(os.path.join(good_sounds_folder, sound['filename']))
        sound['audio_segment'] = audio_segment

    return sounds


def write_sounds_to_files(sounds, output_path, definition_filename, override_folder=False):
    """
    Write the audio segments to file and export the definition JSON file
    """

    if os.path.isdir(output_path):
        if not override_folder:
            input(">>> The folder '%s' already exist. \n>>> Press enter to overwrite it. Otherwise CTRL+C" % output_path)
        rmdir(output_path)

    os.mkdir(output_path)

    for sound in sounds:
        new_filename = '%s_%s_%s.wav' % (sound['instrument'], sound['octave'], sound['note'])
        sound['audio_segment'].export(os.path.join(output_path, new_filename), format='wav')
        sound['filename'] = new_filename
        del sound['audio_segment']

    with open(os.path.join(output_path, definition_filename), 'w') as f:
        json.dump(sounds, f, indent=2)

    print("Elementary sounds successfully written in '%s'" % output_path)


def remove_silence(sounds, silence_thresh, min_silence_duration):
    """
    Remove the silence parts of the recordings
    The recordings that we are filtering are sustained note instrumental recordings
    therefore we keep only the longest non silent interval
    """
    print("Trimming silences...")
    for sound in sounds:
        non_silent_audio_chunks = split_on_silence(sound['audio_segment'],
                                                   min_silence_duration,
                                                   silence_thresh,
                                                   100)

        # Sort the non silent part by duration
        non_silent_audio_chunks = sorted(non_silent_audio_chunks, key=attrgetter('duration_seconds'), reverse=True)

        # Use the longest non-silent part
        # (This is suitable only for the recordings of Good-Sounds dataset since they are sustained instrumental notes)
        sound['audio_segment'] = non_silent_audio_chunks[0]

    return sounds


def amplify_by_instrument(sounds, amplification_factors):
    """
    Amplify the signals with different gain based on the instrument
    """
    print("Amplifying sounds by instruments...")
    print(json.dumps(amplification_factors, indent=2))
    for sound in sounds:
        if sound['instrument'] in amplification_factors:
            amplification_factor = amplification_factors[sound['instrument']]
            if amplification_factor:
                sound['audio_segment'] = sound['audio_segment'].apply_gain(amplification_factor)

    return sounds


def amplify_if_perceptual_loudness_in_range(sounds, amplification_factor, low_bound, high_bound):
    """
    If the perceptual loudness of the sound is between low_bound and high_bound --> Amplify it by the amplification_factor
    """
    print("Amplifying sounds...")
    for sound in sounds:
        perceptual_loudness = get_perceptual_loudness(sound['audio_segment'])

        if high_bound > perceptual_loudness > low_bound:
            print(f"Amplifying with factor {amplification_factor}")
            sound['audio_segment'] = sound['audio_segment'].apply_gain(amplification_factor)

    return sounds


def reduce_duration_linear_by_instrument(sounds, keep_ratios, fadeout_ratio=0.2):
    print("Reduce elementary sounds duration by instrument...")
    print(json.dumps(keep_ratios, indent=2))

    for sound in sounds:
        duration = int(sound['audio_segment'].duration_seconds * 1000)

        if sound['instrument'] not in keep_ratios:
            continue

        if keep_ratios[sound['instrument']] is None:
            continue

        new_duration = int(duration * keep_ratios[sound['instrument']])

        sound['audio_segment'] = sound['audio_segment'][:new_duration].fade_out(int(new_duration * fadeout_ratio))

    return sounds


def reduce_duration_linear_violin(sounds, keep_ratio_by_max_duration, fadeout_ratio=0.2):
    for sound in sounds:
        if sound['instrument'] != 'violin':
            continue

        duration = int(sound['audio_segment'].duration_seconds * 1000)

        ratio_to_use = None
        for max_duration, keep_ratio in keep_ratio_by_max_duration.items():
            if duration < max_duration:
                ratio_to_use = keep_ratio
                break

        if ratio_to_use is None:
            ratio_to_use = list(keep_ratio_by_max_duration.values())[-1]

        if ratio_to_use:
            new_duration = int(duration * ratio_to_use)

            sound['audio_segment'] = sound['audio_segment'][:new_duration].fade_out(int(new_duration * fadeout_ratio))

    return sounds

def reduce_duration_linear(sounds, keep_ratio, fadeout_ratio=0.2):
    for sound in sounds:
        duration = int(sound['audio_segment'].duration_seconds * 1000)
        new_duration = int(duration * keep_ratio)

        sound['audio_segment'] = sound['audio_segment'][:new_duration].fade_out(int(new_duration * fadeout_ratio))

    return sounds


def reduce_duration_crossfade(sounds, keep_ratio, fadeout_ratio=0.2, crossfade_ratio=0.05):
    print("Reducing durations...")
    for sound in sounds:
        duration = int(sound['audio_segment'].duration_seconds * 1000)
        first_part_duration = int(duration * keep_ratio)
        fadeout_duration = int(duration * fadeout_ratio)
        crossfade_duration = int(crossfade_ratio * (first_part_duration + fadeout_duration))

        first_part = sound['audio_segment'][:first_part_duration]
        first_part_crossfade = first_part[-crossfade_duration:].fade(to_gain=-120, start=0, end=float('inf'))
        second_part = sound['audio_segment'][-fadeout_duration:]
        second_part_crossfade = second_part[:crossfade_duration].fade(from_gain=-120, start=0, end=float('inf'))

        test = first_part[:-crossfade_duration] + (first_part_crossfade * second_part_crossfade) + second_part[
                                                                                                   crossfade_duration:]

        # sound['audio_segment'] = first_part.append(sound['audio_segment'][-fadeout_duration:], crossfade=crossfade_duration)
        sound['audio_segment'] = test

    return sounds


def main(args):
    # Instr     Octaves
    # ------------------
    # Flute         4 5
    # Trumpet       4 5
    # Violin        4 5
    # Clarinet    3 4
    # Cello       3 4
    # Bass        3 4

    init_random_seed(args.random_seed)

    database = connect_db(os.path.join(args.good_sounds_folder, args.good_sounds_database_filename))

    # Loading sounds
    CLEAR_elementary_sounds_infos = retrieve_CLEAR_elementary_sounds_infos_from_goodsounds_db(database)

    CLEAR_elementary_sounds = load_sounds_in_memory(CLEAR_elementary_sounds_infos, args.good_sounds_folder)

    # Preprocessing
    # Remove silence parts
    CLEAR_elementary_sounds_preprocessed = remove_silence(CLEAR_elementary_sounds,
                                                          args.silence_threshold,
                                                          args.min_silence_duration)

    # Reduce the duration of the sounds

    duration_ratios = {
        'flute': 0.18,
        'trumpet': 0.2,
        'clarinet': 0.2,
        'cello': 0.5,
        'bass': 0.45,
        'violin': None      # We use a different function to reduce the size of the violin sounds
    }

    CLEAR_elementary_sounds_preprocessed = reduce_duration_linear_by_instrument(CLEAR_elementary_sounds_preprocessed,
                                                                                keep_ratios=duration_ratios,
                                                                                fadeout_ratio=0.1)

    violin_duration_ratios = {
        4000: 0.3,
        5000: 0.13
    }
    CLEAR_elementary_sounds_preprocessed = reduce_duration_linear_violin(CLEAR_elementary_sounds_preprocessed,
                                                                         keep_ratio_by_max_duration=violin_duration_ratios,
                                                                         fadeout_ratio=0.1)

    amplification_factors = {
        'flute': -8,
        'trumpet': -10.8,
        'violin': -5,
        'clarinet': 1.1,
        'cello': 0.3,
        'bass': -0.5
    }

    amplification_factors = {
        'flute': -9,
        'trumpet': -10,
        'violin': -4,
        'clarinet': 2,
        'cello': 2,
        'bass': -5
    }

    CLEAR_elementary_sounds_preprocessed = amplify_by_instrument(CLEAR_elementary_sounds_preprocessed, amplification_factors)

    # Write to file
    write_sounds_to_files(CLEAR_elementary_sounds_preprocessed, args.output_path, args.output_definition_filename, override_folder=True)


if __name__ == "__main__":
    args = parser.parse_args()
    main(args)
