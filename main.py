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


def image_pdf(image, i):
    image.save("images/test" + str(i) + ".jpg")
    image = Image.open("images/test" + str(i) + ".jpg", mode='r')
    print(image_to_string(image))
    return image_to_string(image)


def make_phrases(s):
    word_list = s.split(" ")
    phrase = ""
    phrase_list = []
    for i in range(len(word_list)):
        phrase += word_list[i] + " "
        if len(phrase) >= 120:
            phrase_list.append(phrase)
            phrase = ""
    return phrase_list


def make_threads(phrase_list, threadingCounter):
    threadingCounterDefault = threadingCounter
    length = len(phrase_list)
    i = 0
    while i != length:
        threads = threading.activeCount()

        if not threads >= multiprocessing.cpu_count():
            print (str(threadingCounter) + "/" + str(length + threadingCounterDefault))
            t1 = threading.Thread(target=ask_google, args=(phrase_list[i], threadingCounter,))
            t1.start()
            print("There are currently " + str(threads + 1) + " threads running")
            threadingCounter += 1
            i += 1
        else:
            t1.join()
    t1.join()
    return threadingCounter - threadingCounterDefault


time1 = time.time()

s = ""
if (sys.argv[1][-4:] == ".pdf"):
    try:
        if sys.argv[2] == "true":
            images = convert_from_path(sys.argv[1])
            threadingCounter = 0
            for i in range(len(images)):
                threadingCounter += make_threads(make_phrases(image_pdf(images[i], i)), threadingCounter)
    except:
        print("It is a normal pdf file")
        pdfFileObj = open(sys.argv[1], 'rb')
        pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
        print(pdfReader.numPages)
        for i in range(pdfReader.numPages):
            c = pdfReader.getPage(i)
            s += str(c.extractText())
        make_threads(make_phrases(s), 0)


elif sys.argv[1][-4:] == ".txt":
    f = open(sys.argv[1], "r")
    make_threads(make_phrases(f.read()), 0)


i = 0
full_track = AudioSegment.from_mp3("audio/piece0.mp3")

while os.path.isfile("audio/piece" + str(i) + "mp3"):
    if i == 0:
        i = 1

    new_track = AudioSegment.from_mp3("audio/piece" + str(i) + ".mp3")
    print("adding track num " + str(i))

    full_track += new_track

full_track.export("audio/full_track.mp3", format='mp3')


while os.path.isfile("audio/piece" + str(i) + "mp3"):
        os.remove("audio/piece" + str(i) + ".mp3")

while os.path.isfile("image/test" + str(i) + "jpg"):
    os.remove("image/test" + str(i) + ".jpg")

time2 = time.time()

print ("Time taken is " + str(time2 - time1) + " seconds.")
# Read and write
# Kurzweil 3000
