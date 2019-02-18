from django.shortcuts import render
from django import forms
from .forms import DocumentForm
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse
from django.http import Http404
from django.shortcuts import redirect
from numba import jit

import glob
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
    while os.path.isfile("/home/c/github/Text-to-Speech/Django/lolRipMe/media/unprocessed-audio/" + str(i) + ".mp3"):
        os.remove("/home/c/github/Text-to-Speech/Django/lolRipMe/media/unprocessed-audio/" + str(i) + ".mp3")
        i += 1

    # Remove any leftover images
    i = 0
    while os.path.isfile("/home/c/github/Text-to-Speech/images/test" + str(i) + ".jpg"):
        os.remove("/home/c/github/Text-to-Speech/images/test" + str(i) + ".jpg")
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


# Save the image and then turn it to text
def image_pdf(image, i):
    image.save("/home/c/github/Text-to-Speech/images/test" + str(i) + ".jpg")
    image = Image.open("/home/c/github/Text-to-Speech/images/test" + str(i) + ".jpg", mode='r')
    # print(image_to_string(image))
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
    print (length)
    while i != length:
        threads = threading.activeCount()
        # print ("THe threads are " + threads + "\n" + "The cores are " + cores)
        print (str(threadingCounter + 1) + "/" + str(length + threadingCounterDefault))
        t1 = threading.Thread(target=ask_google, args=(phrase_list[i], threadingCounter,))
        t1.start()
        print("There are currently " + str(threads) + " threads running")
        threadingCounter += 1
        i += 1
    try:
        t1.join()
    except UnboundLocalError:
        print("Tried to allow threads to close when none existed")

    return threadingCounter - threadingCounterDefault

def main(path_and_filename):
    # Turn the path into its smaller parts to use them individually
    path, filename = os.path.split(path_and_filename)
    filename_no_ext, ext = os.path.splitext(filename)
    # Get start time so that you can check how long it took
    time1 = time.time()

    # Open output.txt for writing
    f = open("/home/c/github/Text-to-Speech/output.txt", 'w')
    s = ""

    '''This if and the subsaquint else statments extracts the text from
    the file of the given format, splits it into small enough
    pieces for it to go to to the text to speach api and then
    multithreads the sending of the files to the api and saves the
    replys from the api to mp3s'''
    if (ext == ".pdf"):

        pdfReader = PyPDF2.PdfFileReader(open(path_and_filename, 'rb'))
        threadingCounter = 0

        # Determin whether a pdf is made up of text or it is scanned in
        x = 0
        for i in range(5):
            y = len(str(pdfReader.getPage(5 + i * 2).extractText()))
            if x < y:
                x = y;

        if x > 65:
            print("This is a normal pdf.")
            for i in range(pdfReader.numPages):
                # Extract text from pdf paeg
                s = str(pdfReader.getPage(i).extractText())
#               Wirte to output.txt
                f.write(s)
                f.flush()
                # Turn into phrases small enough to send to api
                ph = make_phrases(s)
                # multithread and send to api
                threadingCounter += make_threads(ph, threadingCounter)

        else:
            # Turn pdf into list of images
            images = convert_from_path(path_and_filename)
            for i in range(len(images)):
                # Turn image that was a pdf page into an image
                text = (image_pdf(images[i], i))
                # Write to output.txt
                f.write(text)
                f.flush()
                # Make page into small enough phrases to send to api
                ph = make_phrases(text)
                # Multithread and send to api
                threadingCounter += make_threads(ph, threadingCounter)

    elif ext == ".txt":
        # Better for debuging. Make into one line when done
        fr = open(path_and_filename, "r")
        # Write to output.txt
        f.write(fr.read())
        f.flush()
        # Make into smaller phrases to send to api for processing
        ph = make_phrases(fr.read())
        # Multi process the sending of the threads
        make_threads(ph, 0)

    elif ext == ".docx":
#       Better for debuging when done put it in one function call
        text = get_docx_text(path_and_filename)
        # Write to output.txt
        f.write(text)
        f.flush()
        ph = make_phrases(text)
        make_threads(ph, 0)
    # Reseting counter to 1
    i = 1
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
    # delete_old_files()
    print("The time taken was " + str(time.time() - time1))


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

# Create your views here.

def home(request):
    f = open(('/home/c/github/Text-to-Speech/output.txt'), 'r')
    file_content = make_phrases(f.read())
    f.close()
    files = list_files('/home/c/github/Text-to-Speech/Django/lolRipMe/media/processed-audio')
    for i in range(len(files)):
        tmp, files[i] = os.path.split(files[i])
    print(files)
    uploaded = get_latest_file("/home/c/github/Text-to-Speech/Django/lolRipMe/media/documents")
    context = {'file_content': file_content, 'download_list': files, 'latest_file': uploaded}
    return render(request, "home.html", context)


def about(request):
    f = open(('/home/c/github/Text-to-Speech/output.txt'), 'r')
    file_content = make_phrases(f.read())
    f.close()
    files = list_files('/home/c/github/Text-to-Speech/Django/lolRipMe/media/processed-audio')
    for i in range(len(files)):
        tmp, files[i] = os.path.split(files[i])
    print(files)
    uploaded = get_latest_file("/home/c/github/Text-to-Speech/Django/lolRipMe/media/documents")
    context = {'file_content': file_content, 'download_list': files, 'latest_file': uploaded}
    return render(request, "about.html", context)


def login(request):
    f = open(('/home/c/github/Text-to-Speech/output.txt'), 'r')
    file_content = make_phrases(f.read())
    f.close()
    files = list_files('/home/c/github/Text-to-Speech/Django/lolRipMe/media/processed-audio')
    for i in range(len(files)):
        tmp, files[i] = os.path.split(files[i])
    print(files)
    uploaded = get_latest_file("/home/c/github/Text-to-Speech/Django/lolRipMe/media/documents")
    context = {'file_content': file_content, 'download_list': files, 'latest_file': uploaded}
    return render(request, "login.html", context)


def read(request):
    f = open(('/home/c/github/Text-to-Speech/output.txt'), 'r')
    file_content = make_phrases(f.read())
    f.close()
    files = list_files('/home/c/github/Text-to-Speech/Django/lolRipMe/media/processed-audio')
    for i in range(len(files)):
        tmp, files[i] = os.path.split(files[i])
    # print(files)
    uploaded = get_latest_file("/home/c/github/Text-to-Speech/Django/lolRipMe/media/documents")
    context = {'file_content': file_content, 'download_list': files, 'latest_file': uploaded}
    return render(request, "read.html", context)

    # file_list_a = list_files("/home/c/github/Text-to-Speech/Django/lolRipMe/media/documents")
    # if request.method == 'POST':
    #     form = DocumentForm(request.POST, request.FILES)
    #     if form.is_valid():
    #         form.save()
    #     file_list_b = list_files("/home/c/github/Text-to-Speech/Django/lolRipMe/media/documents")
    #     p1 = threading.Thread(target=main, args=(x for x in file_list_b if x not in file_list_a),)
    #     p1.start()
    #     return redirect('read')
    # else:
    #     form = DocumentForm()
    #     context = {'file_content': file_content, 'download_list': files, 'form': form}
    #     return render(request, "read.html", context)


def text(request):
    f = open(('/home/c/github/Text-to-Speech/output.txt'), 'r')
    file_content = make_phrases(f.read())
    f.close()
    context = {'file_content': file_content}
    return render(request, "text.html", context)

def sidenav(request):
    files = list_files('/home/c/github/Text-to-Speech/Django/lolRipMe/media/processed-audio')
    for i in range(len(files)):
        tmp, files[i] = os.path.split(files[i])
    # print(files)
    context = {'download_list':files }
    return render(request, "sidenav.html", context)

def model_form_upload(request):
    f = open(('/home/c/github/Text-to-Speech/output.txt'), 'r')
    file_content = make_phrases(f.read())
    f.close()
    files = list_files('/home/c/github/Text-to-Speech/Django/lolRipMe/media/processed-audio')
    for i in range(len(files)):
        tmp, files[i] = os.path.split(files[i])
    print(files)
    uploaded = get_latest_file("/home/c/github/Text-to-Speech/Django/lolRipMe/media/documents")
    file_list_a = list_files("/home/c/github/Text-to-Speech/Django/lolRipMe/media/documents")
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            file_list_b = list_files("/home/c/github/Text-to-Speech/Django/lolRipMe/media/documents")
            p1 = threading.Thread(target=main, args=(x for x in file_list_b if x not in file_list_a),)
            p1.start()
        return redirect('read')
    else:
        form = DocumentForm()
        context = {'file_content': file_content, 'download_list': files, 'form': form}
        return render(request, 'model_form_upload.html', context)


def get_latest_file(path):
    list_of_files = glob.glob(path + '/*')
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file
