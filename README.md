# Text To Speech

This is a multithreaded text to speech program that takes a large input file and exports an mp3.

It can work with both pdfs and txt files. The beauty of this is that it can work with a pdf file that is made up of scanned in images of a book. It will turn them into an image and then turn that into text. There might be a better way to do this, but I cannot find it.

I am working to make it work more quickly by having it read files sooner. Right now it takes the entire file and turns it into an an mp3 and exports it. This takes far too long for most people to go along with it so I have to break it down so that while it is running and processing the rest it is already reading.
# Installing the dependencies for the code
````
pip3 install pytesseract opencv-python gtts pydub pypdf2 pdf2image
````
If you are using linux than use your package manager to install ffmpeg. For Ubuntu and all other Debian based distros the command is
````
sudo apt-get install ffmpeg
````
If you are running windows download ffmpeg from this link and install it manually. https://ffmpeg.org/

# Running the code
To run the program navigate to the directory you just downloaded and run
````
python3 main.py /path/to/file
````
