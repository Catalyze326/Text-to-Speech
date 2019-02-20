from django.shortcuts import render
from django import forms
from .forms import DocumentForm
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse
from django.http import Http404
from django.shortcuts import redirect
from numba import jit

import pytesseract
import cv2
import re
import concurrent.futures
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
from multiprocessing import Process
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


def image_to_text(images, img_path):
    out_dir = "/home/c/github/Text-to-Speech/Django/lolRipMe/media/ocr-images/"
    threads = multiprocessing.cpu_count()
    with concurrent.futures.ProcessPoolExecutor(max_workers=threads) as executor:
        for img_path,out_file in zip(images,executor.map(ocr,images)):
            print(img_path.split("\\")[-1],',',out_file,', processed')


def ocr(img_path):
    out_dir = "ocr_results//"
    img = cv2.imread(img_path)
    text = pytesseract.image_to_string(img,lang='eng',config='--psm 6')
    out_file = re.sub(".png",".txt",img_path.split("\\")[-1])
    out_path = out_dir + out_file
    fd = open(out_path,"w")
    fd.write("%s" %text)
    return out_file

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
    threadingCounterDefault = threadingCounter
    length = len(phrase_list)
    i = 0
    cores = multiprocessing.cpu_count()
    print ("The ammount of threads we will be making is" + str(length))
    # procs = []
    while i != length:
        threads = threading.activeCount()
        print (str(threadingCounter + 1) + "/" + str(length + threadingCounterDefault))
        # proc = Process(target=ask_google, args=(phrase_list[i], threadingCounter,))
        # procs.append(proc)
        # proc.start()
        t1 = threading.Thread(target=ask_google, args=(phrase_list[i], threadingCounter,))
        t1.start()
        # print("There are currently " + str(len(procs))  + " threads running")
        print("There are currently " + str(threads)  + " threads running")
        threadingCounter += 1
        i += 1
    try:
        # for proc in procs:
        #     proc.join()
        t1.join()
    except UnboundLocalError:
        print("Tried to allow threads to close when none existed")
    # print(time.time() - time_start)
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
    for i in range(5):
        y = len(str(pdfReader.getPage(5 + i * 2).extractText()))
        if x < y:
            x = y;
    if x > 65:
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
    threadingCounter = 0
    # Turn pdf into list of images
    images = convert_from_path(path_and_filename)
    print(images)
    image_to_text(images, path_and_filename)
    # for i in range(len(images)):
    #     # images[i] = images[i].convert('1')
    #     # Turn image that was a pdf page into an image
    #     time1 = time.time()
    #     # text = (image_pdf(images[i], i))
    #     print("it took " + str(time.time() - time1) + " seconds.")
    #     # Write to output.txt
    #     f.write(text)
    #     f.flush()
    #     # Make page into small enough phrases to send to api
    #     ph = make_phrases(text)
    #     # Multithread and send to api
    #     threadingCounter += make_threads(ph, threadingCounter)


def image(path_and_filename, filename_no_ext):
    f = open("/home/c/github/Text-to-Speech/Django/lolRipMe/media/text-files//" + filename_no_ext + ".txt", 'w')
    text = (image_pdf(images[i], i))
    # Write to output.txt
    f.write(text)
    f.flush()
    # Make page into small enough phrases to send to api
    make_threads(make_phrases(text), 0)


def txt(path_and_filename, filename_no_ext):
    f = open("/home/c/github/Text-to-Speech/Django/lolRipMe/media/text-files//" + filename_no_ext + ".txt", 'w')
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


# Create your views here.
def home(request):
    files = list_files('/home/c/github/Text-to-Speech/Django/lolRipMe/media/processed-audio')
    for i in range(len(files)):
        tmp, files[i] = os.path.split(files[i])
    uploaded = get_latest_file("/home/c/github/Text-to-Speech/Django/lolRipMe/media/documents")
    context = {'file_content': file_content, 'download_list': files, 'latest_file': uploaded}
    return render(request, "home.html", context)


def about(request):
    files = list_files('/home/c/github/Text-to-Speech/Django/lolRipMe/media/processed-audio')
    for i in range(len(files)):
        tmp, files[i] = os.path.split(files[i])
    uploaded = get_latest_file("/home/c/github/Text-to-Speech/Django/lolRipMe/media/documents")
    context = {'download_list': files, 'latest_file': uploaded}
    return render(request, "about.html", context)


def login(request):
    files = list_files('/home/c/github/Text-to-Speech/Django/lolRipMe/media/processed-audio')
    for i in range(len(files)):
        tmp, files[i] = os.path.split(files[i])
    uploaded = get_latest_file("/home/c/github/Text-to-Speech/Django/lolRipMe/media/documents")
    context = {'file_content': file_content, 'download_list': files, 'latest_file': uploaded}
    return render(request, "login.html", context)


def read(request):
    # f = open(('/home/c/github/Text-to-Speech/Django/lolRipMe/media/text-files/" + filename_no_ext + ".txt"'), 'r')
    # file_content = make_phrases(f.read())
    # f.close()
    files = list_files('/home/c/github/Text-to-Speech/Django/lolRipMe/media/processed-audio')
    for i in range(len(files)):
        tmp, files[i] = os.path.split(files[i])
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
        context = {'file_content': '', 'download_list': files, 'form': form}
        return render(request, 'read.html', context)


def text(request):
    f = open(('/home/c/github/Text-to-Speech/Django/lolRipMe/media/text-files/" + filename_no_ext + ".txt"'), 'r')
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
    f = open(('/home/c/github/Text-to-Speech/Django/lolRipMe/media/text-files/" + filename_no_ext + ".txt"'), 'r')
    file_content = make_phrases(f.read())
    f.close()
    files = list_files('/home/c/github/Text-to-Speech/Django/lolRipMe/media/processed-audio')
    for i in range(len(files)):
        tmp, files[i] = os.path.split(files[i])
    # print(files)
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


def main(path_and_filename):
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

    # make_full_track(filename_no_ext)
    # delete_old_files()

    print("The time taken was " + str(time.time() - time1))
