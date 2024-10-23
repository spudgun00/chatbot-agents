import os
import logging
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import pygame  # Import pygame for playing audio
import time
# from memory_profiler import profile

# Enhanced logging setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('log.txt')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Remove @profile from the functions
def play_audio(file_path):
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():  # Wait for audio to finish playing
        time.sleep(0.1)

# Securely load AWS credentials from environment variables
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'eu-west-2')  # Default to us-west-2 if not specified

if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
    raise ValueError("AWS credentials not found in environment variables")

# Initialize a boto3 session with the AWS credentials
session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

# Create a Polly client using the boto3 session
polly = session.client("polly")

# Remove @profile from the functions
def text_to_speech(text):
    """
    Converts text to speech using AWS Polly with the specified voice model 'Matthew'.
    :param text: The text to be converted to speech.
    :return: The path to the saved audio file.
    """
    try:
        # Requesting speech synthesis from Polly using the 'Matthew' voice
        response = polly.synthesize_speech(Text=text, OutputFormat="mp3", VoiceId="Matthew")
        if "AudioStream" in response:
            output = os.path.join("output", "speech.mp3")  # Saving the file in an 'output' directory
            try:
                # Writing the output to a file
                with open(output, "wb") as file:
                    file.write(response["AudioStream"].read())
                return output
            except IOError as error:
                # Handling file writing errors
                logger.error(error)
                return None
        else:
            # If the response doesn't contain audio data
            logger.error("Could not stream audio from Polly")
            return None

    except (BotoCoreError, ClientError) as error:
        # Handling potential errors from the service
        logger.error(error)
        return None
