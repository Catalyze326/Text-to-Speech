from gtts import gTTS
import os
from pydub import AudioSegment
import threading
import sys


def ask_google(string, i):
    tts = gTTS(text=string, lang='en')
    tts.save("audio/piece" + str(i) + ".mp3")


f = open(sys.argv[1], "r")
s = f.read()

za = s.split(" ")

lol = ""
rip = []
for i in range(len(za)):
    lol += za[i] + " "
    if len(lol) >= 120:
        rip.append(lol)
        lol = ""

for i in range(len(rip)):
    print (str(i) + "/" + str(len(rip)))
    t1 = threading.Thread(target=ask_google, args=(rip[i], i,))
    t1.start()
t1.join()

full_track = AudioSegment.from_mp3("audio/piece0.mp3")

for i in range(len(rip)):
    if i == 0:
        i += 1
    new_track = AudioSegment.from_mp3("audio/piece" + str(i) + ".mp3")
    full_track += new_track
full_track.export("audio/full_track.mp3", format='mp3')

for i in range(len(rip)):
    os.remove("audio/piece" + str(i) + ".mp3")
