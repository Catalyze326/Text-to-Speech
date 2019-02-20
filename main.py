import sys
import pytesseract
import cv2
import concurrent.futures
import glob
from gtts import gTTS
import os
from pydub import AudioSegment
import threading
import PyPDF2
import time
from pdf2image import convert_from_path
import multiprocessing
try:
    from xml.etree.cElementTree import XML
except ImportError:
    from xml.etree.ElementTree import XML
import zipfile

WORD_NAMESPACE = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
PARA = WORD_NAMESPACE + 'p'
TEXT = WORD_NAMESPACE + 't'


def delete_old_files(filename_no_ext):
    # Remove any leftover audio
    i = 0
    while os.path.isfile("/home/c/github/Text-to-Speech/Django/lolRipMe/media/unprocessed-audio/" + str(i) + ".mp3"):
        os.rename("/home/c/github/Text-to-Speech/Django/lolRipMe/media/unprocessed-audio/" + str(i) + ".mp3",
         "/home/c/github/Text-to-Speech/Django/lolRipMe/media/old-unprocessed-audio/" + filename_no_ext + str(i) + ".mp3")
        i += 1

    # Remove any leftover images
    i = 0
    while os.path.isfile("/home/c/github/Text-to-Speech/Django/lolRipMe/media/ocr-images/" + str(i) + ".png"):
        os.remove("/home/c/github/Text-to-Speech/Django/lolRipMe/media/ocr-images/" + str(i) + ".png")
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
    tts.save("/home/c/github/Text-to-Speech/Django/lolRipMe/media/unprocessed-audio/piece" + str(i) + ".mp3")


def image_to_text():
    out_dir = "/home/c/github/Text-to-Speech/Django/lolRipMe/media/ocr-text/"
    os.environ['OMP_THREAD_LIMIT'] = '1'
    threads = multiprocessing.cpu_count()
    with concurrent.futures.ProcessPoolExecutor(max_workers=threads) as executor:
        image_list = list_files("/home/c/github/Text-to-Speech/Django/lolRipMe/media/ocr-images")
        print(image_list)
        for img_path,out_file in zip(image_list,executor.map(ocr,image_list)):
            print("I did a thing")


def ocr(img_path):
    # print(img_path)
    out_dir = "/home/c/github/Text-to-Speech/Django/lolRipMe/media/ocr-text/"
    img = cv2.imread(img_path)
    text = pytesseract.image_to_string(img,lang='eng',config='--psm 6')
    print(text)
    temp, filename = os.path.split(img_path)
    f = open(out_dir + filename[:-4] + ".txt", 'w+')
    f.write(text)
    f.flush()
    return


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
    time_start = time.time()
    i = 0
    threadingCounterDefault = threadingCounter
    length = len(phrase_list)
    cores = multiprocessing.cpu_count()
    print ("The ammount of threads we will be making is" + str(length))
    while i != length:
        threads = threading.activeCount()
        print (str(threadingCounter + 1) + "/" + str(length + threadingCounterDefault))
        t1 = threading.Thread(target=ask_google, args=(phrase_list[i], threadingCounter,))
        t1.start()
        print("There are currently " + str(threads)  + " threads running")
        threadingCounter += 1
        i += 1
    try:
        t1.join()
    except UnboundLocalError:
        print("Tried to allow threads to close when none existed")
    print(time.time() - time_start)
    return threadingCounter - threadingCounterDefault


def make_full_track(filename_no_ext):
    i = 0
    # Initalizeing the full track
    full_track = AudioSegment.from_mp3("/home/c/github/Text-to-Speech/Django/lolRipMe/media/unprocessed-audio/piece0.mp3")
    while os.path.isfile("/home/c/github/Text-to-Speech/Django/lolRipMe/media/unprocessed-audio/piece" + str(i) + ".mp3"):
        # reads in a new track
        new_track = AudioSegment.from_mp3("/home/c/github/Text-to-Speech/Django/lolRipMe/media/unprocessed-audio/piece" + str(i) + ".mp3")
        print("adding track num " + str(i))
        # adds the new tack to the full exported thing
        full_track += new_track
        i += 1
    full_track.export("/home/c/github/Text-to-Speech/Django/lolRipMe/media/processed-audio/" + filename_no_ext + ".mp3", format='mp3')


def decide_pdfs(path_and_filename, filename_no_ext):
    # Turn the path into its smaller parts to use them individually
    path, filename = os.path.split(path_and_filename)
    filename_no_ext, ext = os.path.splitext(filename)
    # Initalize pdf reader
    pdfReader = PyPDF2.PdfFileReader(open(path_and_filename, 'rb'))
    # Determin whether a pdf is made up of text or it is scanned in
    x = 0
    # TODO put try catch in here
    for i in range(5):
        y = len(str(pdfReader.getPage(2 + i * 2).extractText()))
        if x < y:
            x = y
    if x > 120:
        print("This is a normal pdf.")
        normal_pdf(path_and_filename, filename_no_ext)
    else:
        print("This is a scanned in pdf")
        scanned_pdf(path_and_filename, filename_no_ext)


def normal_pdf(path_and_filename, filename_no_ext):
    threadingCounter = 0
    pdfReader = PyPDF2.PdfFileReader(open(path_and_filename, 'rb'))
    s = ''
    f = open("/home/c/github/Text-to-Speech/Django/lolRipMe/media/text-files/" + filename_no_ext + ".txt", 'w')
    for i in range(pdfReader.numPages):
        # Extract text from pdf paeg
        s = str(pdfReader.getPage(i).extractText())
        # Wirte to output.txt
        f.write(s)
        f.flush()
        # Turn into phrases small enough to send to api
        ph = make_phrases(s)
        # multithread and send to api
        threadingCounter += make_threads(ph, threadingCounter)


def scanned_pdf(path_and_filename, filename_no_ext):
    f = open("/home/c/github/Text-to-Speech/Django/lolRipMe/media/text-files/" + filename_no_ext + ".txt", 'w')
    # Turn pdf into list of images
    images = convert_from_path(path_and_filename)
    # print(images)
    for i in range(len(images)):
        images[i].save("/home/c/github/Text-to-Speech/Django/lolRipMe/media/ocr-images/" + str(i) + ".png")
    image_to_text()
    i = 0
    s = ''
    threadingCounter = 0
    while os.path.isfile("/home/c/github/Text-to-Speech/Django/lolRipMe/media/ocr-text/" + str(i) + ".txt"):
        f1 = open("/home/c/github/Text-to-Speech/Django/lolRipMe/media/ocr-text/" + str(i) + ".txt", 'r')
        s += f1.read().replace('\n',' ').replace('\t',' ')
        i += 1

    print(s)
    ph = make_phrases(s)
    threadingCounter += make_threads(ph, threadingCounter)



def image(path_and_filename, filename_no_ext):
    f = open("/home/c/github/Text-to-Speech/Django/lolRipMe/media/text-files/" + filename_no_ext + ".txt", 'w')
    text = pytesseract.image_to_string(path_and_filename)
    # Write to output.txt
    f.write(text)
    f.flush()
    # Make page into small enough phrases to send to api
    make_threads(make_phrases(text), 0)


def txt(path_and_filename, filename_no_ext):
    f = open("/home/c/github/Text-to-Speech/Django/lolRipMe/media/text-files/" + filename_no_ext + ".txt", 'w')
    # Better for debuging. Make into one line when done
    fr = open(path_and_filename, "r")
    # Write to output.txt
    f.write(fr.read())
    f.flush()
    # Make into smaller phrases to send to api for processing
    ph = make_phrases(fr.read())
    # Multi process the sending of the threads
    make_threads(ph, 0)


def docx(path_and_filename, filename_no_ext):
    f = open("/home/c/github/Text-to-Speech/Django/lolRipMe/media/text-files/" + filename_no_ext + ".txt", 'w')
#   Better for debuging when done put it in one function call
    text = get_docx_text(path_and_filename, filename_no_ext)
    # Write to output.txt
    f.write(text)
    f.flush()
    ph = make_phrases(text)
    make_threads(ph, 0)


# List files in a directory going recursively.
def list_files(loc):
    filelist = []
    dirlist = list_dirs(loc)
    for path, dirs, files in os.walk(loc):
        for f in files:
            filelist.append(path + "/" + f)
    for dir in dirlist:
        for path, dirs, files in os.walk(dir):
            for f in files:
                filelist.append(path + "/" + f)
    # for file in filelist:
    #     print("We found " + file)
    return filelist


# returns a list of the directories in a folder
def list_dirs(loc):
    dirlist = []
    for path, dirs, files in os.walk(loc):
        for d in dirs:
            lol = (path + "/" + d)
            dirlist.append(lol)
    return dirlist


def get_latest_file(path):
    list_of_files = glob.glob(path + '/*')
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file


def main(path_and_filename=sys.argv[1]):
    # Turn the path into its smaller parts to use them individually
    path, filename = os.path.split(path_and_filename)
    filename_no_ext, ext = os.path.splitext(filename)
    # Erase Output.txt
    f = open("/home/c/github/Text-to-Speech/Django/lolRipMe/media/text-files/" + filename_no_ext + ".txt", 'w')
    f.close()
    # Image types
    image_types = {'.jpg', '.png', '.gif', '.jpeg', '.tif', '.raw'}

    # Get start time so that you can check how long it took
    time1 = time.time()
    if (ext.lower() == ".pdf"):
        decide_pdfs(path_and_filename, filename_no_ext)
    elif ext.lower() == ".txt":
        txt(path_and_filename, filename_no_ext)
    elif ext.lower() == ".docx":
        docx(path_and_filename, filename_no_ext)
    elif ext.lower() in image_types:
        image(path_and_filename, filename_no_ext)

    make_full_track(filename_no_ext)
    print("Deleting and moving extra files")
    delete_old_files(filename_no_ext)
    print("The time taken was " + str(time.time() - time1) + "\nDone!")

main()
