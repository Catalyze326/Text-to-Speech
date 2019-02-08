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
try:
    from xml.etree.cElementTree import XML
except ImportError:
    from xml.etree.ElementTree import XML
import zipfile

WORD_NAMESPACE = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
PARA = WORD_NAMESPACE + 'p'
TEXT = WORD_NAMESPACE + 't'

def delete_old_files():
    # Remove any leftover audio
    i = 0
    while os.path.isfile("audio/piece" + str(i) + ".mp3"):
        os.remove("audio/piece" + str(i) + ".mp3")
        i += 1

    # Remove any leftover images
    i = 0
    while os.path.isfile("images/test" + str(i) + ".jpg"):
        os.remove("images/test" + str(i) + ".jpg")
        i += 1


def get_docx_text(path):
    """
    Take the path of a docx file as argument, return the text in unicode.
    """
    document = zipfile.ZipFile(path)
    xml_content = document.read('word/document.xml')
    document.close()
    tree = XML(xml_content)

    paragraphs = []
    for paragraph in tree.getiterator(PARA):
        texts = [node.text
                 for node in paragraph.getiterator(TEXT)
                 if node.text]
        if texts:
            paragraphs.append(''.join(texts))

    return '\n\n'.join(paragraphs)

# Process the audio
def ask_google(string, i):
    tts = gTTS(text=string, lang='en')
    tts.save("audio/piece" + str(i) + ".mp3")

# Save the image and then turn it to text
def image_pdf(image, i):
    image.save("images/test" + str(i) + ".jpg")
    image = Image.open("images/test" + str(i) + ".jpg", mode='r')
    print(image_to_string(image))
    return image_to_string(image)

# Turn the large body of text into small pieces
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

# Multithread it
def make_threads(phrase_list, threadingCounter):
    threadingCounterDefault = threadingCounter
    length = len(phrase_list)
    i = 0
    cores = multiprocessing.cpu_count()

    while i != length:
        threads = threading.activeCount()

        if threads <= cores:
            print (str(threadingCounter + 1) + "/" + str(length + threadingCounterDefault))
            t1 = threading.Thread(target=ask_google, args=(phrase_list[i], threadingCounter,))
            t1.start()
            print("There are currently " + str(threads) + " threads running")
            threadingCounter += 1
            i += 1
        else:
            t1.join()
    try:
        t1.join()
    except UnboundLocalError:
        print("Tried to allow threads to close when none existed")

    return threadingCounter - threadingCounterDefault


time1 = time.time()
s = ""

try:
    if (sys.argv[1][-4:] == ".pdf"):
        try:
            # If it is a pdf that does not contain pure text add the true flag
            if sys.argv[2] == "--true":
                # Convets the pdf into a string of images
                images = convert_from_path(sys.argv[1])
                threadingCounter = 0
                ''' Turns the images into text and them into small enough sizes
                to send to google and then multi threads the process of sending
                the strings to google than saves those files to mp3s'''
                for i in range(len(images)):
                    ph = make_phrases(image_pdf(images[i], i))
                    threadingCounter += make_threads(ph, threadingCounter)

        except IndexError:
            print("It is a normal pdf file")
            pdfReader = PyPDF2.PdfFileReader(open(sys.argv[1], 'rb'))
            '''Extracts the text from the pdf, splits it into small enough
            pieces for it to go to google and then multithreads the sending of
            the files to google and saves the replys from google to mp3s'''
            threadingCounter = 0
            for i in range(pdfReader.numPages):
                # Better for debuging
                s = str(pdfReader.getPage(i).extractText())
                ph = make_phrases(s)
                threadingCounter += make_threads(ph, threadingCounter)
                # Fewer lines
                # make_threads(make_phrases(str(pdfReader.getPage(i).extractText())), 0)

    elif sys.argv[1][-4:] == ".txt":
        # Better for debuging. Make into one line when done
        '''Converts the text into small enough pieces to send to google, multi
         threads the sending of those files to google and then saves those files
         google exports to mp3s'''
        f = open(sys.argv[1], "r")
        ph = make_phrases(f.read())
        make_threads(ph, 0)

    elif sys.argv[1][-5:] == ".docx":
#       Better for debuging when done put it in one function call
        '''Extracts the text out of the docx file and then splits that into
        phrases small enough to send to google and then multithreads that
        process and then saves the exported files as mp3s'''
        text = get_docx_text(sys.argv[1])
        ph = make_phrases()
        make_threads(ph, 0)


    # It will start reading the files aloud right when it makes the first one
    # and then it will save the full export when its done.
    i = 1
    # Initalizeing the full track
    full_track = AudioSegment.from_mp3("audio/piece0.mp3")
    while os.path.isfile("audio/piece" + str(i) + ".mp3"):
        # reads in a new track
        new_track = AudioSegment.from_mp3("audio/piece" + str(i) + ".mp3")
        print("adding track num " + str(i))
        # adds the new tack to the full exported thing
        full_track += new_track
        i += 1
    folder, filename = os.path.split(sys.argv[1])
    full_track.export("audio/" + filename + ".mp3", format='mp3')
except KeyboardInterrupt:
    print("Goodbye World\n")

# It causes errors when the leftover files are still there when it runs again
delete_old_files()

time2 = time.time()
print ("Time taken is " + str(time2 - time1) + " seconds.")
