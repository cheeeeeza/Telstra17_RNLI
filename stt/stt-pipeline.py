# imports
import numpy as np
import sounddevice as sd # for python to access ur mic
import requests # allow web requests
from faster_whisper import WhisperModel # sst engine
import paramiko 
import getpass
import base64

"""
stt-pipeline.py

in a nutshell, this document takes audio input from your laptop mic,
transcribes it, and sends it to the llm to process

"""

# connecting to haku
haku_ip = "10.234.6.18"
haku_user = "nao"
password = getpass.getpass("Haku's password: ")

# establishing ssh conneciton with haku
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(haku_ip, username=haku_user, password=password)


def haku_speak(message):
    # Sends text to Haku via SSH to be spoken via NAOqi TTS
    encoded = base64.b64encode(message.encode("utf-8")).decode("utf-8")
    command = (
        "python -c \"import base64; "
        "from naoqi import ALProxy; "
        "tts=ALProxy('ALTextToSpeech','127.0.0.1',9559); "
        "tts.say(base64.b64decode('" + encoded + "'))\""
    )
    stdin, stdout, stderr = ssh.exec_command(command)
    stdout.channel.recv_exit_status()  # wait for it to actually finish speaking

# llm settings
LLM_ENDPOINT = "http://localhost:11434/api/generate"
LLM_MODEL_NAME = "llama3.2:3b"
SAMPLE_RATE = 16000 # audio expected

print("Loading local Whisper model into memory... (This may take a moment)")
model = WhisperModel("base", device="cpu", compute_type="int8")

def record_audio(duration=7):
    #Records audio from the microphone for 5 seconds
    print(f"\nListening for {duration} seconds...")
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    return audio.flatten()

def transcribe_audio(audio_data):
    # transcribes raw audio arrays locally using whisper
    print("Transcribing...")
    segments, info = model.transcribe(audio_data, beam_size=5)
    text = " ".join(segment.text for segment in segments)
    return text.strip()

def send_to_local_llm(prompt_text):
    # sends the text to the local LLM and Haku replies
    if not prompt_text or len(prompt_text) < 2:
        print("No speech detected.")
        return

    print(f"You said: {prompt_text}")
    print("Querying local LLM...")

    payload = {
        "model": LLM_MODEL_NAME,
        "prompt": f"You are a local voice assistant. Keep answers brief.\n\nUser: {prompt_text}",
        "stream": False
    }

    try:
        response = requests.post(LLM_ENDPOINT, json=payload, timeout=30)
        response.raise_for_status()
        reply = response.json()["response"]
        print(f"Haku: {reply}")
        haku_speak(reply)
    except requests.exceptions.RequestException as e:
        print(f"Could not connect to LLM at {LLM_ENDPOINT}. Error: {e}")
    except KeyError:
        print(f"Unexpected response format: {response.json()}")

# main loop
if __name__ == "__main__":
    print("Starting voice assistant. Press Ctrl+C to stop.")
    try:
        while True:
            audio_buffer = record_audio(duration=5)
            transcribed_text = transcribe_audio(audio_buffer)
            send_to_local_llm(transcribed_text)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        ssh.close()