from django.shortcuts import render
from .forms import DocumentForm
from django.shortcuts import redirect

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
from multiprocessing import Pool
from multiprocessing import Queue

try:
    from xml.etree.cElementTree import XML
except ImportError:
    from xml.etree.ElementTree import XML
import zipfile

processed_audio = '/home/c/github/Text-to-Speech/Django/lolRipMe/media/processed_audio/'
unprocessed_audio = '/home/c/github/Text-to-Speech/Django/lolRipMe/media/unprocessed_audio/'
old_unprocessed_audio = '/home/c/github/Text-to-Speech/Django/lolRipMe/media/old_unprocessed_audio/'
ocr_images = '/home/c/github/Text-to-Speech/Django/lolRipMe/media/ocr_images/'
ocr_text = "/home/c/github/Text-to-Speech/Django/lolRipMe/media/ocr_text/"
documents = "/home/c/github/Text-to-Speech/Django/lolRipMe/media/documents"
text_files = "/home/c/github/Text-to-Speech/Django/lolRipMe/media/text-files/"
# audo-pieces = "/home/c/github/Text-to-Speech/Django/lolRipMe/media/unprocessed_audio/piece"

WORD_NAMESPACE = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
PARA = WORD_NAMESPACE + 'p'
TEXT = WORD_NAMESPACE + 't'


def delete_old_files(filename_no_ext):
    # Remove any leftover audio
    i = 0
    while os.path.isfile(unprocessed_audio + filename_no_ext + str(i) + ".mp3"):
        os.rename(unprocessed_audio + filename_no_ext + str(i) + ".mp3",
         old_unprocessed_audio + filename_no_ext + str(i) + ".mp3")
        i += 1

    # Remove any leftover images
    i = 0
    while os.path.isfile(ocr_images + str(i) + ".png"):
        os.remove(ocr_images + str(i) + ".png")
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
def ask_google(string, i, filename_no_ext):
    tts = gTTS(text=string, lang='en')
    tts.save(unprocessed_audio + filename_no_ext + str(i) + ".mp3")
    print("Saving")


def image_to_text():
    os.environ['OMP_THREAD_LIMIT'] = '1'
    threads = multiprocessing.cpu_count()
    with concurrent.futures.ProcessPoolExecutor(max_workers=threads) as executor:
        image_list = list_files(ocr_images)
        print(image_list)
        for img_path,out_file in zip(image_list,executor.map(ocr,image_list)):
            print("I did a thing")


def ocr(img_path):
    # print(img_path)
    img = cv2.imread(img_path)
    text = pytesseract.image_to_string(img,lang='eng',config='--psm 6')
    print(text)
    temp, filename = os.path.split(img_path)
    f = open(ocr_text + filename[:-4] + ".txt", 'w+')
    f.write(text)
    f.flush()
    return


# Turn the large body of text into small pieces
def make_phrases(s):
    print(s)
    word_list = s.split(" ")
    phrase = ""
    phrase_list = []
    for i in range(len(word_list)):
        phrase += word_list[i] + " "
        if len(phrase) >= 110:
            phrase_list.append(phrase)
            phrase = ""
    return phrase_list


def make_threads(phrase_list, threadingCounter, filename_no_ext):
    q = Queue()
    time_start = time.time()
    i = 0
    threadingCounterDefault = threadingCounter
    length = len(phrase_list)
    cores = multiprocessing.cpu_count()
    print ("The ammount of threads we will be making is" + str(length))
    pool = multiprocessing.Pool(cores * 40) #use all available cores, otherwise specify the number you want as an argument
    for i in range(length):
        pool.apply_async(ask_google, args=(phrase_list[i], threadingCounter, filename_no_ext,))
        threadingCounter += 1
    pool.close()
    pool.join()
    # while i != length:
    #     threads = threading.activeCount()
    #     if i != length:
    #         print (str(threadingCounter + 1) + "/" + str(length + threadingCounterDefault))
    #         t1 = threading.Thread(target=ask_google, args=(phrase_list[i], threadingCounter, filename_no_ext))
    #         t1.start()
    #         print("There are currently " + str(threads)  + " threads running")
    #         threadingCounter += 1
    #         i += 1
    # try:
    #     t1.join()
    # except UnboundLocalError:
    #     print("Tried to allow threads to close when none existed")
    print(time.time() - time_start)
    return threadingCounter - threadingCounterDefault


def make_full_track(filename_no_ext):
    cores =  multiprocessing.cpu_count()
    num_files = len(list_files(unprocessed_audio))
    set_size = int(num_files / cores)
    add = num_files % cores
    print("The extra that needs to be put on the end " + str(add))
    sets = [[0 for x in range(set_size)] for y in range(cores)]

    last_one = []
    for i in range(add):
        print(i)
        last_one.append(unprocessed_audio + filename_no_ext + str(i + (set_size * cores)) + ".mp3")

    k = 0
    for i in range(cores):
        for j in range(set_size):
            sets[i][j] = (unprocessed_audio + filename_no_ext + str(k) + ".mp3")
            k += 1

    processes = []
    for i in range(cores):
        # print(sets[i])
        p = multiprocessing.Process(target=multithreaded_splicing_tracks, args=(sets[i],filename_no_ext,))
        processes.append(p)
        p.start()
        print("Starting core " + str(i))
    p = multiprocessing.Process(target=multithreaded_splicing_tracks, args=(last_one,filename_no_ext,))
    p.start()
    processes.append(p)

    for one_process in processes:
        one_process.join()

    for i in range(cores):
        if i == 0:
            final_export = AudioSegment.from_mp3(unprocessed_audio + filename_no_ext + "0.mp3")
        final_export += AudioSegment.from_mp3(unprocessed_audio + filename_no_ext + str(i) + ".mp3")

    final_export.export(processed_audio + filename_no_ext + "final.mp3", format='mp3')
    print("Fully exported.")


def multithreaded_splicing_tracks(list_of_tracks, filename_no_ext):
    print(list_of_tracks)
    for i in range(len(list_of_tracks)):
        if i == 0:
            full_track = AudioSegment.from_mp3(list_of_tracks[0])
        else:
            # reads in a new track
            full_track += AudioSegment.from_mp3(unprocessed_audio + filename_no_ext + str(i) + ".mp3")
        print("adding track num " + str(i))
        # adds the new tack to the full exported thing
    full_track.export(processed_audio + filename_no_ext + str(i) + ".mp3", format='mp3')
    print("Exporting large track")


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
        threadingCounter += make_threads(ph, threadingCounter, )


def scanned_pdf(path_and_filename, filename_no_ext):
    f = open("/home/c/github/Text-to-Speech/Django/lolRipMe/media/text-files/" + filename_no_ext + ".txt", 'w')
    # Turn pdf into list of images
    images = convert_from_path(path_and_filename)
    # print(images)
    for i in range(len(images)):
        images[i].save(ocr_images + str(i) + ".png")
    image_to_text()
    i = 0
    s = ''
    threadingCounter = 0
    while os.path.isfile(ocr_text + str(i) + ".txt"):
        f1 = open(ocr_text + str(i) + ".txt", 'r')
        s += f1.read().replace('\n',' ').replace('\t',' ')
        i += 1

    print(s)
    ph = make_phrases(s)
    threadingCounter += make_threads(ph, threadingCounter, filename_no_ext)


def image(path_and_filename, filename_no_ext):
    f = open("/home/c/github/Text-to-Speech/Django/lolRipMe/media/text-files/" + filename_no_ext + ".txt", 'w')
    text = pytesseract.image_to_string(path_and_filename)
    # Write to output.txt
    f.write(text)
    f.flush()
    # Make page into small enough phrases to send to api
    make_threads(make_phrases(text), 0, filename_no_ext)


def txt(path_and_filename, filename_no_ext):
    f = open("/home/c/github/Text-to-Speech/Django/lolRipMe/media/text-files/" + filename_no_ext + ".txt", 'w')
    # Better for debuging. Make into one line when done
    fr = open(path_and_filename, "r")
    # Make into smaller phrases to send to api for processing
    # Multi process the sending of the threads
    ph = make_phrases(fr.read())
    # print(fr.read())
    f.write(fr.read())
    f.flush()
    # print out text
    # print(ph)
    make_threads(ph, 0, filename_no_ext)


def docx(path_and_filename, filename_no_ext):
    f = open("/home/c/github/Text-to-Speech/Django/lolRipMe/media/text-files/" + filename_no_ext + ".txt", 'w')
#   Better for debuging when done put it in one function call
    text = get_docx_text(path_and_filename, filename_no_ext)
    # Write to output.txt
    f.write(text)
    f.flush()
    ph = make_phrases(text)
    make_threads(ph, 0, filename_no_ext)


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
    files = list_files(processed_audio)
    for i in range(len(files)):
        tmp, files[i] = os.path.split(files[i])
    uploaded = get_latest_file(documents)
    context = {'file_content': file_content, 'download_list': files, 'latest_file': uploaded}
    return render(request, "home.html", context)


def about(request):
    files = list_files(processed_audio)
    for i in range(len(files)):
        tmp, files[i] = os.path.split(files[i])
    uploaded = get_latest_file(documents)
    context = {'download_list': files, 'latest_file': uploaded}
    return render(request, "about.html", context)


def login(request):
    files = list_files(processed_audio)
    for i in range(len(files)):
        tmp, files[i] = os.path.split(files[i])
    uploaded = get_latest_file(documents)
    context = {'file_content': file_content, 'download_list': files, 'latest_file': uploaded}
    return render(request, "login.html", context)


def read(request):
    # f = open(('/home/c/github/Text-to-Speech/Django/lolRipMe/media/text-files/" + filename_no_ext + ".txt"'), 'r')
    # file_content = make_phrases(f.read())
    # f.close()
    files = list_files(processed_audio)
    for i in range(len(files)):
        tmp, files[i] = os.path.split(files[i])
    uploaded = get_latest_file(documents)
    file_list_a = list_files(documents)
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            file_list_b = list_files(documents)
            p1 = threading.Thread(target=main, args=(x for x in file_list_b if x not in file_list_a),)
            p1.start()
        return redirect('read')
    else:
        form = DocumentForm()
        context = {'file_content': '', 'download_list': files, 'form': form}
        return render(request, 'read.html', context)


def text(request):
    # make into global var
    f = open((text_files + filename_no_ext + ".txt"), 'r')
    file_content = make_phrases(f.read())
    f.close()
    context = {'file_content': file_content}
    return render(request, "text.html", context)


def sidenav(request):
    files = list_files(processed_audio)
    for i in range(len(files)):
        tmp, files[i] = os.path.split(files[i])
    # print(files)
    context = {'download_list': files}
    return render(request, "sidenav.html", context)


def model_form_upload(request):
    f = open((text_files + filename_no_ext + '.txt'), 'r')
    file_content = make_phrases(f.read())
    f.close()
    files = list_files(processed_audio)
    for i in range(len(files)):
        tmp, files[i] = os.path.split(files[i])
    # print(files)
    uploaded = get_latest_file(documents)
    file_list_a = list_files(documents)

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            file_list_b = list_files(documents)
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
    # f = open("/home/c/githuib/Text-to-Speech/Django/lolRipMe/media/text-files/" + filename_no_ext + ".txt", 'w')
    # f.close()
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

#2785 Millers Way Drive Ellicott City Maryland 21043
#seancoralson@gmail.com
# main(sys.argv[1])
