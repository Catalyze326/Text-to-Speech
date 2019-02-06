from gtts import gTTS
import os
from pydub import AudioSegment
import threading
import multiprocessing
import sys
import PyPDF2
import time
from numba import jit

print(time.time())
time1 = time.time()
if sys.argv[1][-4:] == ".pdf":
    pdfFileObj = open(sys.argv[1], 'rb')
    pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
    s = ""
    print(pdfReader.numPages)
    for i in range(pdfReader.numPages):
        s += str(pdfReader.getPage(i))
elif sys.argv[1][-4:] == ".txt":
    f = open(sys.argv[1], "r")
    s = f.read()


def ask_google(string, i):
    tts = gTTS(text=string, lang='en')
    tts.save("audio/piece" + str(i) + ".mp3")

if not os.path.exists("audio/"):
    os.mkdir("audio/")


word_list = s.split(" ")

lol = ""
rip = []
for i in range(len(word_list)):
    lol += word_list[i] + " "
    if len(lol) >= 120:
        rip.append(lol)
        lol = ""

threadingCounter = 0
while threadingCounter != len(rip):
    if not threading.activeCount() >= 250:
        print (str(threadingCounter) + "/" + str(len(rip)))
        t1 = threading.Thread(target=ask_google, args=(rip[threadingCounter], threadingCounter,))
        t1.start()
        print("There are currently " + str(threading.active_count()) + " threads running")
        threadingCounter += 1
    else:
        t1.join()
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
time2 = time.time()
print ("Time taken is " + str(time1 - time2))
