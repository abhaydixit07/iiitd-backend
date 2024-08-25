from flask import Flask, jsonify, request, g
from flask_cors import CORS
from dotenv import load_dotenv
import os
import pyaudio
import wave
from groq import Groq

app = Flask(__name__)
CORS(app, supports_credentials=True)
load_dotenv()

# Load API key
OPEN_API_KEY = os.getenv('OPEN_API_KEY')

# Define constants
SOUND_REFERENCE = {
    'S': 'SH', 'F': 'TH', 'L': 'R', 'B': 'V', 'P': 'F',
    'T': 'D', 'A': 'E', 'Z': 'S'
}

IMAGE = {
    'A': 'https://png.pngtree.com/png-vector/20231017/ourmid/pngtree-fresh-apple-fruit-red-png-image_10203073.png',
    'Z': 'https://pngimg.com/uploads/zebra/zebra_PNG95977.png'
}

PRONUNCIATION = {
    "sunday": "sʌn.deɪ", "free": "friː", "love": "lʌv", "boat": "boʊt",
    "pen": "pen", "tree": "triː", "apple": "ˈæp.əl", "ball": "bɔːl", "zebra": "ˈziː.brə"
}

EXAMPLE = {
    'S': 'sunday', 'F': 'free', 'L': 'love', 'B': 'boat', 'B2': 'ball',
    'P': 'pen', 'T': 'tree', 'A': 'apple', 'Z': 'zebra'
}

REMEDY = {
    'P': ['Put your lips together to make the sound. Vocal cords don’t vibrate for voiceless sounds.'],
    'B': ['Put your lips together to make the sound.'],
    'B2': ['Put your lips together to make the sound.'],
    'M': ['Put your lips together to make the sound. Air flows through your nose.'],
    'W': ['Put your lips together and shape your mouth like you are saying "oo".'],
    'F': ['Place your bottom lip against your upper front teeth. Top teeth may be on your bottom lip.'],
    'V': ['Place your bottom lip against your upper front teeth. Top teeth may be on your bottom lip.'],
    'S': ["Keep your teeth close together to make the sound. The ridge right behind your two front teeth is involved. The front of your tongue is used. Vocal cords don’t vibrate for voiceless sounds."],
    'Z': ['Keep your teeth close together to make the sound. The ridge right behind your two front teeth is involved. The front of your tongue is used.'],
    'th': ['Place your top teeth on your bottom lip and let your tongue go between your teeth for the sound. The front of your tongue is involved.'],
    'TH': ['Place your top teeth on your bottom lip and let your tongue go between your teeth for the sound (as in thin). The front of your tongue is involved. The front of your tongue is used.'],
    'NG': ['Air flows through your nose.'],
    'SING': ['Air flows through your nose.'],
    'L': ['The ridge right behind your two front teeth is involved. The front of your tongue is used.'],
    'T': ["The ridge right behind your two front teeth is involved. The front of your tongue is used. Vocal cords don’t vibrate for voiceless sounds."],
    'D': ['The ridge right behind your two front teeth is involved. The front of your tongue is used.'],
    'CH': ['The front-roof of your mouth is the right spot for the sound. The front of your tongue is used.'],
    'J': ['The front-roof of your mouth is the right spot for the sound. The front of your tongue is used.'],
    'SH': ['The front-roof of your mouth is the right spot for the sound. The front of your tongue is used.'],
    'ZH': ['The front-roof of your mouth is the right spot for the sound. The front of your tongue is used.'],
    'K': ["The back-roof of your mouth is the right spot for the sound. The back of your tongue is used. Vocal cords don’t vibrate for voiceless sounds."],
    'G': ['The back-roof of your mouth is the right spot for the sound. The back of your tongue is used.'],
    'R': ['The back-roof of your mouth is the right spot for the sound. The back of your tongue is used.'],
    'Y': ['The front of your tongue is used.'],
    'H': ['Your lungs provide the airflow for every sound, especially this one.'],
    'A': [
        'Open your mouth wide with your tongue flat at the bottom, as in "apple".',
        'Open your mouth wide and pull your tongue back slightly, as in "father".'
    ]
}

# Helper function to check pronunciation
def check(word_given, word_received, check_for):
    word_received = word_received.strip().split()[0]  # Simplified strip and first word
    print(word_given, word_received, check_for)
    if word_received.startswith(SOUND_REFERENCE.get(check_for, '')):
        if word_received[len(SOUND_REFERENCE[check_for]):] == word_given[len(check_for):]:
            return 20
    elif word_received.startswith(check_for):
        if word_received[len(check_for):] == word_given[len(check_for):]:
            return 100
        else:
            return 75
    return 0

# Record audio route
@app.route('/record', methods=["GET"])
def record():
    chunk = 1024
    sample_format = pyaudio.paInt16
    channels = 2
    fs = 44100
    seconds = 5
    filename = "output.wav"

    p = pyaudio.PyAudio()
    stream = p.open(format=sample_format, channels=channels, rate=fs, frames_per_buffer=chunk, input=True)
    frames = []

    print('Recording')
    for _ in range(0, int(fs / chunk * seconds)):
        data = stream.read(chunk)
        frames.append(data)
    print('Finished recording')

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(sample_format))
    wf.setframerate(fs)
    wf.writeframes(b''.join(frames))
    wf.close()

    try:
        client = Groq(api_key=OPEN_API_KEY)
        with open(filename, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(filename, file.read()),
                model="whisper-large-v3",
                response_format="verbose_json"
            )
        transcript_text = transcription.get('text', '')
        percentage = check(EXAMPLE[g.coupled].upper(), transcript_text.upper(), g.coupled.upper())
        return jsonify({"transcript": transcript_text, "percentage": percentage})
    except Exception as e:
        print(f"Error in transcription: {e}")
        return jsonify({"error": str(e)}), 500

# Remedy route
@app.route("/remedy/<int:averagePercentage>", methods=["GET", "POST"])
def remedy(averagePercentage):
    if averagePercentage <= 50:
        result = {"remedy": REMEDY.get(g.coupled, [])}
    else:
        result = {"remedy": ""}
    return jsonify(result)

# Test route
@app.route("/test/<lettergiven>")
def test(lettergiven):
    g.coupled = lettergiven.upper()
    word_data = {
        "word1": EXAMPLE[g.coupled],
        "letter": g.coupled,
        "pronunciation": PRONUNCIATION.get(EXAMPLE[g.coupled].lower(), ""),
        "image_link": IMAGE.get(g.coupled, "")
    }
    return jsonify(word_data)

# Generate word route
@app.route("/generate_word/<lettergiven>")
def generate_word(lettergiven):
    g.coupled = lettergiven.upper()
    word_data = {
        "word1": EXAMPLE[g.coupled],
        "letter": g.coupled,
        "pronunciation": PRONUNCIATION.get(EXAMPLE[g.coupled].lower(), "")
    }
    return jsonify(word_data)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
