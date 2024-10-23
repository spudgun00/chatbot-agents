import json
import logging
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import argparse
from api import query_openai_api
from stt import text_to_speech, play_audio
import time
from datetime import datetime, timedelta
import webrtcvad
import tracemalloc

# Start tracing memory allocations
tracemalloc.start()

# Global variable to control the main loop
running = True

# from memory_profiler import profile

# Initialize a vad object
vad = webrtcvad.Vad()

# Run the VAD on 10 ms of silence and 16000 sampling rate 
sample_rate = 16000
frame_duration = 10 # in ms

# Creating an audio frame of silence
frame = b'\x00\x00' * int(sample_rate * frame_duration / 1000)

# Detecting speech
print(f'Contains speech: {vad.is_speech(frame, sample_rate)}')

# Global variables for managing conversation state
q = queue.Queue()
active_listening = False
is_speaking = False  # New variable to track if the assistant is speaking
context = []  # This will store the conversation history

# Global variable to store the last processed query and its time
last_query = None
last_query_time = datetime.min

# Global variables for duplicate detection and minimum query length
last_response = None
last_response_time = datetime.min
MIN_QUERY_LENGTH = 3  # Minimum length of query to process

# Enhanced logging setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# File handler for log file
file_handler = logging.FileHandler('log.txt')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
# Stream handler for console output
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
# Add both handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Argument parser for command-line options regarding device and samplerate
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("-d", "--device", type=int, help="Input device (numeric ID or substring)")
parser.add_argument("-r", "--samplerate", type=int, help="Sampling rate")
args = parser.parse_args()

# Determine the samplerate; use the default if not specified
if args.samplerate is None:
    if args.device is None:
        # Default input device if none is specified
        device_info = sd.query_devices(kind="input")
    else:
        # Specific device based on provided ID
        device_info = sd.query_devices(args.device, "input")
    args.samplerate = int(device_info["default_samplerate"])

# Initialize the speech recognition model
model = Model(lang="en-us")
recognizer = KaldiRecognizer(model, args.samplerate)

# Global variable to manage the audio stream
stream = None

# Callback function to handle incoming audio data
# Remove @profile from the functions
# Global variable for the audio buffer
buffer = bytearray()

# Callback function to handle incoming audio data
BUFFER_SIZE = 8000  # Buffer size in bytes

def callback(indata, frames, time, status):
    global buffer  # Use the global buffer
    if status:
        logger.error(status)
    if not is_speaking:  # Ignore data if the system is speaking
        buffer.extend(bytes(indata))
        if len(buffer) >= BUFFER_SIZE:
            # When buffer is full, put it in the queue and reset the buffer
            q.put(buffer[:])
            buffer.clear()



# Function to manage assistant speaking
# Remove @profile from the functions
def assistant_speaks(response_text):
    global is_speaking
    is_speaking = True
    stop_audio_stream()  # Stop the audio stream

    audio_file = text_to_speech(response_text)
    if audio_file:
        play_audio(audio_file)

    is_speaking = False
    start_audio_stream_after_delay()  # Start the audio stream with a delay

# Remove @profile from the functions
def stop_audio_stream():
    global stream
    stream.close()

# Remove @profile from the functions
def start_audio_stream_after_delay(delay=1):
  global stream, args
  time.sleep(delay) # Cool down period to avoid capturing echoes or the tail of played audio
  # Reopen the stream after the delay
  stream = sd.RawInputStream(samplerate=args.samplerate, blocksize=8000, device=args.device, dtype='int16', channels=1, callback=callback)
  stream.start()

# Remove @profile from the functions
def handle_input(result):
    global active_listening, context, last_response, last_response_time, running
    text = json.loads(result).get('text', '').lower()

    # Check for the 'finish chat' command to stop the script
    if "finish chat" in text:
        running = False  # Set a flag to indicate the script should end
        logger.info("Ending call and exiting script...")
        return  # Exit the function to allow the script to proceed to the finally block

    # Ignore input if the system is currently speaking or if the text is too short
    if is_speaking or len(text) < MIN_QUERY_LENGTH:
        return

    # Check for repeated responses within a short time window, e.g., 10 seconds
    if last_response and text == last_response and (datetime.now() - last_response_time) < timedelta(seconds=10):
        logger.info("Detected a repeated response. Ignoring to prevent a loop.")
        return

    # Update the last response and its timestamp
    last_response = text
    last_response_time = datetime.now()

    logger.info(f"Transcribed text: {text}")

    if "oracle" in text and not active_listening:
        active_listening = True
        logger.info("Activated. Awaiting command...")
    elif active_listening:
        if "goodbye" in text:
            active_listening = False
            context.clear()
            logger.info("Goodbye! Awaiting next wake word...")
        else:
            user_message = {"role": "user", "content": text}
            context.append(user_message)
            response_text = query_openai_api(text, context)

            if response_text:
                logger.info(f"Assistant response: {response_text}")
                assistant_message = {"role": "assistant", "content": response_text}
                context.append(assistant_message)
                assistant_speaks(response_text)  # Let the assistant speak
# Main function to listen to audio input and transcribe it
# Remove @profile from the functions
def listen_and_transcribe():
    global stream, running  # Include 'running' in the global statement
    stream = sd.RawInputStream(samplerate=args.samplerate, blocksize=8000, device=args.device, dtype="int16", channels=1, callback=callback)
    with stream:
        logger.info("Listening for wake word...")
        while running:  # Use the running flag to control the loop
            data = q.get()
            if recognizer.AcceptWaveform(data):
                result = recognizer.Result()
                handle_input(result)

# Main entry point of the script
def main():
    try:
        listen_and_transcribe()
    except KeyboardInterrupt:
        logger.info("Chat interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
    finally:
        # Display the top 10 memory blocks at the end of the program
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        print("[ Top 10 ]")
        for stat in top_stats[:10]:
            print(stat)

        # Stop tracing memory allocations
        tracemalloc.stop()

if __name__ == "__main__":
    main()
