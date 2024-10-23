import os
import logging
from openai import OpenAI
# from memory_profiler import profile


   

# Enhanced logging setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# File handler for log file
file_handler = logging.FileHandler('log.txt')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
# Stream handler for console output
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
# Add both handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)
# Remove @profile from the functionse
def query_openai_api(user_input, context):
    try:
        messages = context + [{"role": "user", "content": user_input}]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150
        )

        logger.debug(f"API Response: {response}")

        # Accessing the assistant's response
        if response.choices and len(response.choices) > 0:
            for choice in response.choices:
                if choice.message.role == "assistant":  # Ensure we're getting the assistant's response
                    response_text = choice.message.content.strip()
                    logger.info(f"OpenAI response: {response_text}")
                    return response_text

        logger.error("No response from OpenAI API.")
        return None

    except Exception as e:
        logger.error(f"Error querying OpenAI API: {e}")
        return None
