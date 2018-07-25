import pydub
from pydub import AudioSegment
from pydub.generators import WhiteNoise as WhiteNoiseGenerator
import os
import ujson
import copy
from multiprocessing import Pool
import matplotlib
# Matplotlib options to reduce memory usage
matplotlib.interactive(False)
matplotlib.use('agg')

import matplotlib.pyplot as plt


######################################################################
# This program will read the scene json file (default ./scenes.json) #
# It will then generate the corresponding audio file & spectrogram   #
######################################################################

# TODO : The audio file must have a fixed length to maintain the same temporal resolution on spectrograms
#        We calculate the scene length by maxNbOfPrimarySoundsInOneScene * longestPrimarySoundLength + maxNbOfPrimarySoundsInOneScene * sleepTimeBetweenSounds + beginSleepTime + endSleepTime
#        Some scenes will require padding. We should pad with silence (Or noise ? Would add more randomness).
#        Instead of padding everything at the end, we should distribute part of the padding between each sounds
#        We should not pad always the same way to reduce bias in data.
#        We should pad or not between each sound according to a certain probability. Then split the rest between beginning and end
# TODO/Investigate : Insert random noise instead of silence between primary sounds

# TODO : Add some threading to this. Its too slow !

# TODO : Load this from config json instead of hardcoding it in every file
sceneFilenamePrefix = 'scene-'

# FIXME : We should probably clear previously generated audio & images before generating. (We may end up with samples from another run otherwise)
# TODO : Add more comments
# FIXME : Take sample rate as parameter. If primary sounds have a lower sample freq, upscale ?
class AudioSceneProducer:
    def __init__(self,
                 outputFolder = '../output',
                 scenesJsonFilename='generatedScenes.json',
                 primarySoundsJsonFilename='primary_sounds.json',
                 primarySoundFolderPath='../primary_sounds',
                 setType='train'):

        # Paths
        cwd = os.path.dirname(os.path.realpath(__file__))
        self.outputFolder = os.path.join(cwd, outputFolder)
        self.primarySoundFolderPath = os.path.join(cwd, primarySoundFolderPath)

        # Loading primary sounds definition from 'primarySounds.json'
        with open(os.path.join(self.primarySoundFolderPath, primarySoundsJsonFilename)) as primarySoundJson:
            self.primarySounds = ujson.load(primarySoundJson)

        # Loading scenes definition from 'scenes.json'
        sceneFilepath = os.path.join(self.outputFolder, scenesJsonFilename)
        with open(sceneFilepath) as scenesJson:
            self.scenes = ujson.load(scenesJson)['scenes']

        self.setType = setType

        self.currentSceneIndex = -1  # We start at -1 since nextScene() will increment idx at the start of the fct
        self.nbOfLoadedScenes = len(self.scenes)

        if self.nbOfLoadedScenes == 0:
            print("[ERROR] Must have at least 1 scene in '"+sceneFilepath+"'")
            exit(0)     # FIXME : Should probably raise an exception here instead

        # TODO : Add other default sounds such as random noise and other continuous sounds
        self.defaultLoadedSounds = [
            {
                'name': '-SILENCE-',
                'audioSegment': AudioSegment.silent(duration=100)      # 100 ms of silence      # FIXME : Should specify the sample rate
            }
        ]

        # Creating a copy of the default sound list
        self.loadedSounds = copy.deepcopy(self.defaultLoadedSounds)

    def _loadAllPrimarySounds(self):
        for sound in self.primarySounds:
            # Creating the audio segment (Suppose WAV format)
            soundFilepath = os.path.join(self.primarySoundFolderPath, sound['note_str'] + '.wav')
            soundAudioSegment = AudioSegment.from_wav(soundFilepath)
            self.loadedSounds.append({
                'name': sound['note_str'],
                'audioSegment': soundAudioSegment
            })

        print("Done loading primary sounds")


    def _clearLoadedSounds(self):
        # TODO : Destroy all AudioSegments except SILENCE

        # Restoring default loadedSounds list
        self.loadedSounds = copy.deepcopy(self.defaultLoadedSounds)

    def _loadAllCurrentSceneSounds(self):
        scene = self.scenes[self.currentSceneIndex]

        if len(scene['composition']) == 0:
            print("[ERROR] Invalid scene. Must contain at least 1 sound")
            exit(0)     # FIXME : Should probably raise an exception here instead

        # TODO : [IDEA] Add playback attribute in composition (length?)
        for sceneSound in scene['composition']:
            if not self._isLoadedByName(sceneSound['name']):
                soundInfos = self.primarySounds[sceneSound['name']]
                # Creating the audio segment (Suppose WAV format)
                soundFilepath = os.path.join(self.primarySoundFolderPath, soundInfos['category'], soundInfos['filename'])
                soundAudioSegment = AudioSegment.from_wav(soundFilepath)
                self.loadedSounds.append({
                    'name': sceneSound['name'],
                    'audioSegment': soundAudioSegment
                })

    def _isLoadedByName(self, soundName):
        return len(list(filter(lambda sound: sound['name'] == soundName, self.loadedSounds))) == 1

    def _getLoadedAudioSegmentByName(self, name):
        filterResult = list(filter(lambda sound: sound['name'] == name, self.loadedSounds))
        if len(filterResult) == 1:
            return filterResult[0]['audioSegment']
        else:
            print('[ERROR] Could not retrieve loaded audio segment \'' + name + '\' from memory.')
            exit(0)  # FIXME : Should probably raise an exception here instead

    def generateScene(self, sceneId):

        # FIXME : Do not hard code this, should be passed to the class constructor
        imageSize = {
            'height': 480,
            'width': 320
        }
        if sceneId < self.nbOfLoadedScenes:

            scene = self.scenes[sceneId]
            print('Generating scene ' + str(sceneId))
            sceneAudioSegment = AudioSegment.empty()
            silenceSegment100ms = self._getLoadedAudioSegmentByName('-SILENCE-')

            # Insert silence paddig of 200 ms at the beginning of the scene
            sceneAudioSegment += silenceSegment100ms * 2
            for sound in scene['objects']:
                newAudioSegment = self._getLoadedAudioSegmentByName(sound['note'])
                sceneAudioSegment += newAudioSegment

                # Insert a silence padding of 300 ms between the sounds
                sceneAudioSegment += silenceSegment100ms * 3

            # FIXME : Background noise should probably constant ? The scene duration is constant so no need to regen everytime
            backgroundNoise = WhiteNoiseGenerator(sample_rate=sceneAudioSegment.frame_rate).to_audio_segment(sceneAudioSegment.duration_seconds*1000)

            sceneAudioSegment = backgroundNoise.overlay(sceneAudioSegment, gain_during_overlay=-60)

            # Make sure the everything is in Mono (If stereo, will convert to mono)
            sceneAudioSegment.set_channels(1)

            # FIXME : Create the setType folder if doesnt exist
            sceneAudioSegment.export(os.path.join(self.outputFolder, 'audio', self.setType, 'AQA_%s_%06d.wav' % (self.setType, sceneId)), format='wav')

            # Set figure settings to remove all axis
            spectrogram = plt.figure(frameon=False)
            spectrogram.set_size_inches(imageSize['height'], imageSize['width'])
            ax = plt.Axes(spectrogram, [0., 0., 1., 1.])
            ax.set_axis_off()
            spectrogram.add_axes(ax)

            # Generate the spectrogram
            # See https://matplotlib.org/api/_as_gen/matplotlib.pyplot.specgram.html?highlight=matplotlib%20pyplot%20specgram#matplotlib.pyplot.specgram
            # TODO : Use essentia to generate spectrogram, mfcc, etc ?
            Pxx, freqs, bins, im = plt.specgram(x=sceneAudioSegment.get_array_of_samples(), Fs=sceneAudioSegment.frame_rate,
                         window=matplotlib.mlab.window_hanning,
                         NFFT=1024, noverlap=512, mode='magnitude', scale='dB')

            # FIXME : Create the setType folder if doesnt exist
            spectrogram.savefig(os.path.join(self.outputFolder, 'images', self.setType, 'AQA_%s_%06d.png' % (self.setType, sceneId)),dpi=1)

            # Close and Clear the figure
            plt.close(spectrogram)
            spectrogram.clear()

        else:
            print("[ERROR] The scene specified by id '%d' couln't be found" % sceneId)

def mainPool():
    outputFolder = 'output'

    producer = AudioSceneProducer(outputFolder='../output',
                                  scenesJsonFilename='scenes/AQA_V0.1_val_scenes.json',
                                  primarySoundsJsonFilename='primary_sounds.json',
                                  primarySoundFolderPath='../primary_sounds',
                                  setType='val')

    idList = list(range(producer.nbOfLoadedScenes))

    # FIXME : The definition of the threads should be done inside the class

    # FIXME : Each process should load their composition sound instead of loading everything in memory here
    producer._loadAllPrimarySounds()

    # FIXME : All the process should probably not work from the same object attributes
    nbProcess = 4

    pool = Pool(processes=nbProcess)
    pool.map(producer.generateScene, idList)

    print("Job Done !")

if __name__ == '__main__':
    mainPool()