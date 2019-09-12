# CLEAR Dataset
# >> Elementary Sounds Wrapper
#
# Author :      Jerome Abdelnour
# Year :        2018-2019
# Affiliations: Universite de Sherbrooke - Electrical and Computer Engineering faculty
#               KTH Stockholm Royal Institute of Technology
#               IGLU - CHIST-ERA

import ujson
import os
import numpy as np
from pydub import AudioSegment
from collections import defaultdict

from timbral_models import timbral_brightness
from utils.audio_processing import get_perceptual_loudness


class Elementary_Sounds:
    """
    Elementary Sounds Wrapper
      - Load the elementary sounds from file
      - Preprocess the sounds
        - Analyse sounds and add new attributes to the definition
      - Give an interface to retrieve sounds
    """

    def __init__(self, folder_path, definition_filename):
        print("Loading Elementary sounds")
        self.folderpath = folder_path

        with open(os.path.join(self.folderpath, definition_filename)) as file:
            self.definition = ujson.load(file)

        self.notes = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

        self.sorted_durations = []

        self.nb_sounds = len(self.definition)

        self._preprocess_sounds()

        self.families_count = {}

        self.id_list = [sound['id'] for sound in self.definition]

        self.id_list_shuffled = self.id_list.copy()

        for sound in self.definition:
            if sound['instrument'] not in self.families_count:
                self.families_count[sound['instrument']] = 1
            else:
                self.families_count[sound['instrument']] += 1

        self.families = self.families_count.keys()
        self.nb_families = len(self.families)

        self.generated_count_by_index = {i: 0 for i in range(self.nb_sounds)}
        self.generated_count_by_families = {fam: 0 for fam in self.families}
        self.gen_index = 0

    def get(self, index):
        return self.definition[index]

    def _preprocess_sounds(self, shuffle_sounds=True):
        """
        Apply some preprocessing on the loaded sounds
          - Calculate the perceptual loudness (ITU-R BS.1770-4 specification) and assign "Loud" or "Quiet" label
          - Calculate perceptual brightness and assign "Bright", "Dark" or None label
          - Retrieve the sound duration
          - Packup the info in the sound dict
        """

        if shuffle_sounds:
            np.random.shuffle(self.definition)

        # Store max and min brightness for each instrument. Used for brightness normalization
        brightness_per_instrument = defaultdict(lambda: {'max': 0, 'min': 9999})

        for id, elementary_sound in enumerate(self.definition):
            elementary_sound_filename = os.path.join(self.folderpath, elementary_sound['filename'])
            elementary_sound_audiosegment = AudioSegment.from_wav(elementary_sound_filename)

            elementary_sound['id'] = id

            elementary_sound['duration'] = int(elementary_sound_audiosegment.duration_seconds * 1000)

            perceptual_loudness = get_perceptual_loudness(elementary_sound_audiosegment)
            elementary_sound['loudness'] = 'quiet' if perceptual_loudness < -27 else 'loud'

            self.sorted_durations.append(elementary_sound['duration'])

            elementary_sound['int_brightness'] = timbral_brightness(elementary_sound_filename)

            if elementary_sound['int_brightness'] > brightness_per_instrument[elementary_sound['instrument']]['max']:
                brightness_per_instrument[elementary_sound['instrument']]['max'] = elementary_sound['int_brightness']
            elif elementary_sound['int_brightness'] < brightness_per_instrument[elementary_sound['instrument']]['min']:
                brightness_per_instrument[elementary_sound['instrument']]['min'] = elementary_sound['int_brightness']

        # Normalize the brightness per instrument and assign the brightness label
        for id, elementary_sound in enumerate(self.definition):
            max_brightness = brightness_per_instrument[elementary_sound['instrument']]['max']
            min_brightness = brightness_per_instrument[elementary_sound['instrument']]['min']
            cur_brightness = elementary_sound['int_brightness']

            # Normalize brightness per instrument
            elementary_sound['rel_brightness'] = (cur_brightness - min_brightness) / (max_brightness - min_brightness)

            # Assign brightness label
            if elementary_sound['rel_brightness'] > 0.6:
                elementary_sound['brightness'] = 'bright'
            elif elementary_sound['rel_brightness'] < 0.4:
                elementary_sound['brightness'] = 'dark'
            else:
                elementary_sound['brightness'] = None

            # Cleanup unused properties
            del elementary_sound['int_brightness']
            del elementary_sound['rel_brightness']

        self.sorted_durations = sorted(self.sorted_durations)
        self.half_longest_durations_mean = np.mean(self.sorted_durations[-int(self.nb_sounds/2):])

    def sounds_to_families_count(self, sound_list):
        """
        Return the frequence of each instrument family
        """
        count = {}

        for sound in sound_list:
            family = sound['instrument']
            if family in count:
                count[family] += 1
            else:
                count[family] = 1

        non_empty_families = count.keys()
        non_empty_families_count = len(non_empty_families)

        empty_families = set(self.families) - set(non_empty_families)
        for family in empty_families:
            count[family] = 0

        return count, non_empty_families_count
