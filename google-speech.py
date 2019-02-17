import speech_recognition as sr

r = sr.Recognizer()
audio_file = sr.AudioFile("audio/time.txt.wav")

with audio_file as source:
    audio_file_record = r.record(source, offset=10)

print(r.recognize_google(audio_file_record, language='en-US'))
