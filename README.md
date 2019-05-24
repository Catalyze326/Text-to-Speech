# Text-to-Speech
To get this running simply run these commands:

````
pip3 install pytesseract
````
````
pip3 install gtts
````
````
pip3 install pydub
````
````
pip3 install pypdf2
````
````
pip3 install pdf2image
````
````
pip3 install opencv-python
````
````
sudo apt-get install ffmpeg
````
Multithreaded text to speech program that takes a large input file and exports an mp3.

It can work with both pdfs and txt files. The beauty of this is that it can work with a pdf file that is made up of scanned in images of a book. It will turn them into an image and then turn that into text. There might be a better way to do this, but I cannot find it.

I am working to make it work more quickly by having it read files sooner. Right now it takes the entire file and turns it into an an mp3 and exports it. This takes far too long for most people to go along with it so I have to break it down so that while it is running and processing the rest it is already reading.
