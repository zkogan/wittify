import pyaudio
import wave
import audioop
from collections import deque
import os
import urllib
import time
import math
import subprocess as sub

FLAC_CONV = 'flac -f'  # We need a WAV to FLAC converter. flac is available
                       # on Linux

# Microphone stream config.
CHUNK = 1024  # CHUNKS of bytes to read each time from mic
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
THRESHOLD = 1000  # The threshold intensity that defines silence
                  # and noise signal (an int. lower than THRESHOLD is silence).

SILENCE_LIMIT = 3  # Silence limit in seconds. The max amount of seconds where
                   # only silence is recorded. When this time passes the
                   # recording finishes and the file is delivered.

PREV_AUDIO = 0.5  # Previous audio (in seconds) to prepend. When noise
                  # is detected, how much of previously recorded audio is
                  # prepended. This helps to prevent chopping the beggining
                  # of the phrase.

DURATION = 40     # Maximum chunk duration

rel = RATE/CHUNK

def audio_int(num_samples=50):
    """ Gets average audio intensity of your mic sound. You can use it to get
        average intensities while you're talking and/or silent. The average
        is the avg of the 20% largest intensities recorded.
    """

    print ("Getting intensity values from mic.")
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    values = [math.sqrt(abs(audioop.avg(stream.read(CHUNK), 4))) 
              for x in range(num_samples)] 
    values = sorted(values, reverse=True)
    r = sum(values[:int(num_samples * 0.2)]) / int(num_samples * 0.2)
    print (" Finished ")
    print (" Average audio intensity is ", r)
    stream.close()
    p.terminate()
    return r


def listen_for_speech(threshold=THRESHOLD, num_phrases=-1):
    """
    Listens to Microphone, extracts phrases from it and sends it to 
    Google's TTS service and returns response. a "phrase" is sound 
    surrounded by silence (according to threshold). num_phrases controls
    how many phrases to process before finishing the listening process 
    (-1 for infinite). 
    """

    # Open stream
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print ("* Listening to microphone... ")
    audio2send = []
    cur_data = ''  # current chunk  of audio data
    slid_win = deque(maxlen = int(SILENCE_LIMIT * rel))
    # Prepend audio from 0.5 seconds before noise was detected
    prev_audio = deque(maxlen = int(PREV_AUDIO * rel))
    started = False
    n = num_phrases
    response = []

    while (num_phrases == -1 or n > 0):
        cur_data = stream.read(CHUNK)
        slid_win.append(math.sqrt(abs(audioop.avg(cur_data, 4))))
        #print slid_win[-1]
        if(sum([x > THRESHOLD for x in slid_win]) > 0):
            if(not started):
                print ("   Starting phrase recording")
                started = True
            audio2send.append(cur_data)
        elif (started is True):
            print ("   Finished")
            # The limit was reached, finish capture and deliver.
            filename = save_speech(list(prev_audio) + audio2send, p)
            # Send file to Google and get response
            # r = stt_google_wav(filename) 
            # if num_phrases == -1:
            #     print ("Response", r)
            # else:
            #     response.append(r)
            # Remove temp file. Comment line to review.
            # os.remove(filename)
            # Reset all
            started = False
            slid_win = deque(maxlen = int(SILENCE_LIMIT * rel))
            prev_audio = deque(maxlen = int(PREV_AUDIO * rel))
            audio2send = []
            n -= 1
            print ("Listening ...")
        else:
            prev_audio.append(cur_data)

    print ("* Done recording")
    stream.close()
    p.terminate()

    return response

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

def save_speech(data, p):
    """ Saves mic data to temporary WAV file. Returns filename of saved 
        file """

    data = b''.join(data)

    output_folder = str(time.strftime('%d%m%Y'))
    if os.path.exists(output_folder) == False:
            os.mkdir(output_folder)

    if os.path.exists(output_folder + "/" + "noise") == False:
            os.mkdir(output_folder + "/" + "noise")
    
    if len(data) > (rel * DURATION):
        dur = int(32768 * DURATION)
        print (len(data), dur)
        dataset = chunks(data, dur)
        # dataset = [data[i:i + dur] for i in range(0, len(data), dur)]
        filenames = []
        current_time = str(time.strftime('%H%M%S'))

        for index, item in enumerate(dataset):
            filename = current_time + '_' + str(index)
            wf = wave.open(output_folder + "/" + filename + '.wav', 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(RATE) 
            wf.writeframes(item)
            filenames.append(filename)
            wf.close()
        return filenames

    else:
        if len(data) < (rel * SILENCE_LIMIT + PREV_AUDIO * 1.5):
            print("Audio too short, likely to be noise.")
            filename = str(time.strftime('%H%M%S'))
            wf = wave.open(output_folder + "/" + "noise" + "/" + filename + '.wav', 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(RATE) 
            wf.writeframes(data)
            wf.close()
        else:
            filename = str(time.strftime('%H%M%S'))
            wf = wave.open(output_folder + "/" + filename + '.wav', 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(RATE)  
            wf.writeframes(data)
            wf.close()
        return filename


if(__name__ == '__main__'):
    audio_int()  # To measure your mic levels
    listen_for_speech()  # listen to mic.
    #print stt_google_wav('hello.flac')  # translate audio file