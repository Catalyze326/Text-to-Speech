from gtts import gTTS
import os
from pydub import AudioSegment
import threading
import sys


# List files in a directory going recursively.
def list_files(loc):
    filelist = []
    for path, dirs, files in os.walk(loc):
        for f in files:
            filelist.append(path + "/" + f)
    for file in filelist:
        print("We found " + file)
    return filelist


def ask_google(string, i):
    tts = gTTS(text=string, lang='en')
    tts.save("audio/piece" + str(i) + ".mp3")


f = open(sys.argv[1], "r")
s = f.read()

t1 = 0
t2 = 128

za = s.split(" ")

lol = ""
rip = []
j = 0
for i in range(len(za)):
    lol += za[i] + " "
    print (lol)
    if len(lol) >= 120:
        rip.append(lol)
        lol = ""

i = 0
for j in range(len(za)):
    print (str(i) + "/" + str(len(za)))
    t1 = threading.Thread(target=ask_google, args=(za[1], i,))
    i += 1
    t1.start()
    print("There are currently " + str(threading.active_count()) + " threads running")

full_track = AudioSegment.from_mp3("audio/piece0.mp3")
for i in range(len(list_files("audio/"))):
    if i == 0:
        i += 1
        new_track = AudioSegment.from_mp3("audio/piece" + str(i) + ".mp3")
        full_track += new_track
        full_track.export("audio/full_track.mp3", format='mp3')

for file in list_files("audio/"):
    folder, filename = os.path.split(file)
    if filename[0:4] == "piece":
        os.remove(file)
