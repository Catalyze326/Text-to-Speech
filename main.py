# from django.shortcuts import render
# from .forms import DocumentForm
# from django.shortcuts import redirect
# TODO test all other filetypes 
# TODO clean up code
import sys
import pytesseract
import cv2
import concurrent.futures
import glob
from gtts import gTTS
import os
from pydub import AudioSegment
import PyPDF2
import time
from pdf2image import convert_from_path
import multiprocessing

try:
    from xml.etree.cElementTree import XML
except ImportError:
    from xml.etree.ElementTree import XML
import zipfile

processed_audio = 'processed_audio/'
unprocessed_audio = 'unprocessed_audio/'
old_unprocessed_audio = 'old_unprocessed_audio/'
ocr_images = 'ocr_images/'
ocr_text = "ocr_text/"
documents = "documents"
text_files = "text-files/"

if not os.path.isdir(processed_audio): os.mkdir(processed_audio)
if not os.path.isdir(unprocessed_audio): os.mkdir(unprocessed_audio)
if not os.path.isdir(old_unprocessed_audio): os.mkdir(old_unprocessed_audio)
if not os.path.isdir(ocr_images): os.mkdir(ocr_images)
if not os.path.isdir(ocr_text): os.mkdir(ocr_text)
if not os.path.isdir(documents): os.mkdir(documents)
if not os.path.isdir(text_files): os.mkdir(text_files)

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


# Take the path of a docx file as argument, return the text in unicode.
def get_docx_text(path):
    document = zipfile.ZipFile(path)
    xml_content = document.read('word/document.xml')
    document.close()
    tree = XML(xml_content)
    paragraphs = []
    for paragraph in tree.getiterator(PARA):
        texts = [node.text
                 for node in paragraph.getiterator(TEXT)
                 if node.text]
        if texts: paragraphs.append(''.join(texts))

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
    img = cv2.imread(img_path)
    text = pytesseract.image_to_string(img,lang='eng',config='--psm 6')
    print(text)
    temp, filename = os.path.split(img_path)
    f = open(ocr_text + filename[:-4] + ".txt", 'w+')
    f.write(text)
    f.flush()
    return text


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
    time_start = time.time()
    i = 0
    threadingCounterDefault = threadingCounter
    length = len(phrase_list)
    cores = multiprocessing.cpu_count()
    print ("The ammount of threads we will be making is " + str(length))
    pool = multiprocessing.Pool(cores * 40) #use all available cores, otherwise specify the number you want as an argument
    for phrase in phrase_list:
        pool.apply_async(ask_google, args=(phrase, threadingCounter, filename_no_ext,))
        threadingCounter += 1
    pool.close()
    pool.join()
    print(time.time() - time_start)
    return threadingCounter - threadingCounterDefault


def make_full_track(filename_no_ext):
    num_files = len(list_files(unprocessed_audio))
    large_track = AudioSegment.from_mp3(unprocessed_audio + filename_no_ext + str(0) + ".mp3")
    for i in range(num_files - 1):
        large_track += AudioSegment.from_mp3(unprocessed_audio + filename_no_ext + str(i + 1) + ".mp3")
    large_track.export(processed_audio + filename_no_ext + "final.mp3", format='mp3')


def decide_pdfs(path_and_filename, filename_no_ext):
    # Turn the path into its smaller parts to use them individually
    path, filename = os.path.split(path_and_filename)
    filename_no_ext, ext = os.path.splitext(filename)
    # Initalize pdf reader
    pdfReader = PyPDF2.PdfFileReader(open(path_and_filename, 'rb'))
    # Determin whether a pdf is made up of text or it is scanned in
    x = 0
    num_pages = pdfReader.numPages - 1
    page_to_check = int(num_pages / 2)
    num_words_scanned = scanned_pdf_check(path_and_filename, filename_no_ext, page_to_check)
    num_words_text = len(str(pdfReader.getPage(page_to_check))) + 5
    while num_words_scanned < 20:
        if(page_to_check + 1 < num_pages):
            page_to_check += 1
        else:
            print("This is a scanned in pdf")
            scanned_pdf(path_and_filename, filename_no_ext)
        num_words_scanned = scanned_pdf_check(path_and_filename, filename_no_ext, page_to_check)
        num_words_text = len(str(pdfReader.getPage(page_to_check).extractText())) + 5
        
    if num_words_scanned > num_words_text + 10:
        print("This is a scanned in pdf")
        scanned_pdf(path_and_filename, filename_no_ext)
    else:
        print("This is a normal pdf.")
        normal_pdf(path_and_filename, filename_no_ext)


def normal_pdf(path_and_filename, filename_no_ext):
    threadingCounter = 0
    pdfReader = PyPDF2.PdfFileReader(open(path_and_filename, 'rb'))
    s = ''
    f = open(text_files + filename_no_ext + ".txt", 'w')
    for i in range(pdfReader.numPages):
        # Extract text from pdf paeg
        s = str(pdfReader.getPage(i).extractText())
        # Wirte to output.txt
        f.write(s)
        f.flush()
        # Turn into phrases small enough to send to api
        ph = make_phrases(s)
        # multithread and send to api
        threadingCounter += make_threads(ph, threadingCounter, filename_no_ext,)


def scanned_pdf(path_and_filename, filename_no_ext):
    f = open(text_files + filename_no_ext + ".txt", 'w')
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


def scanned_pdf_check(path_and_filename, filename_no_ext, pageNum):
    f = open(text_files + filename_no_ext + ".txt", 'w')
    # Turn pdf into list of images
    images = convert_from_path(path_and_filename)
    images[pageNum].save(ocr_images + "check_page" + ".png")
    # print(images)

    images[pageNum].save(ocr_images + "check_page" + ".png")
    return len(ocr(ocr_images + "check_page" + ".png"))


def image(path_and_filename, filename_no_ext):
    f = open(text_files + filename_no_ext + ".txt", 'w')
    text = pytesseract.image_to_string(path_and_filename)
    # Write to output.txt
    f.write(text)
    f.flush()
    # Make page into small enough phrases to send to api
    make_threads(make_phrases(text), 0, filename_no_ext)


def txt(path_and_filename, filename_no_ext):
    f = open(text_files + filename_no_ext + ".txt", 'w')
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
    f = open(text_files + filename_no_ext + ".txt", 'w')
#   Better for debuging when done put it in one function call
    text = get_docx_text(path_and_filename)
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


def main(path_and_filename):
    # Turn the path into its smaller parts to use them individually
    path, filename = os.path.split(path_and_filename)
    filename_no_ext, ext = os.path.splitext(filename)
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
    else:
        print("That is not a supported file format.")
        exit

    make_full_track(filename_no_ext)
    print("Deleting and moving extra files")
    delete_old_files(filename_no_ext)
    print("The time taken was " + str(time.time() - time1) + "\nDone!")


try:
    if 'help' in sys.argv[1]:
        print('The proper usage for the program is \n python3 main.py /path/to/file')
    main(sys.argv[1])
except IndexError:
    print('The proper usage for the program is \n python3 main.py /path/to/file')