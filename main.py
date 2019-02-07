from gtts import gTTS
import os
from pydub import AudioSegment
import threading
import sys
import PyPDF2
import time
from pdf2image import convert_from_path
from PIL import Image
from pytesseract import image_to_string
import multiprocessing


def ask_google(string, i):
    tts = gTTS(text=string, lang='en')
    tts.save("audio/piece" + str(i) + ".mp3")


time1 = time.time()
s = ""
if (sys.argv[1][-4:] == ".pdf"):
    try:
        if sys.argv[2] == "true":
            i = 0
            if not os.path.exists("images/"):
                os.mkdir("images/")
            images = convert_from_path(sys.argv[1])
            for image in images:
                image.save("images/test" + str(i) + ".jpg")
                image = Image.open("images/test" + str(i) + ".jpg", mode='r')
                print(image_to_string(image))
                s += image_to_string(image)
                i += 1
            i = 0
    except:
        print("It is a normal pdf file")
        pdfFileObj = open(sys.argv[1], 'rb')
        pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
        print(pdfReader.numPages)
        for i in range(pdfReader.numPages):
            s += str(pdfReader.getPage(i))

elif sys.argv[1][-4:] == ".txt":
    f = open(sys.argv[1], "r")
    s = f.read()

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
length = len(rip)
while threadingCounter != length:
    threads = threading.activeCount()
    if not threads >= multiprocessing.cpu_count():
        print (str(threadingCounter) + "/" + str(length))
        t1 = threading.Thread(target=ask_google, args=(rip[threadingCounter], threadingCounter,))
        t1.start()
        print("There are currently " + str(threads) + " threads running")
        threadingCounter += 1
    else:
        t1.join()
t1.join()

full_track = AudioSegment.from_mp3("audio/piece0.mp3")
for i in range(len(rip)):
    if i == 0:
        i = 1
    new_track = AudioSegment.from_mp3("audio/piece" + str(i) + ".mp3")
    print("adding track num " + str(length))
    full_track += new_track

full_track.export("audio/full_track.mp3", format='mp3')

# for i in range(length):
#     os.remove("audio/piece" + str(i) + ".mp3")
time2 = time.time()
print ("Time taken is " + str(time1 - time2))
