import os
import json
import logging

import aiohttp
from dotenv import load_dotenv
from fastapi import HTTPException


# Logger instance
logFormatter = logging.Formatter("[%(asctime)s] [%(process)d] [%(levelname)s]  %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

# loading environment variables from .env file
load_dotenv()

API_KEY = os.getenv('API_KEY')
MODEL_ENDPOINT = os.getenv('MODEL_ENDPOINT')
CURIE_URL      = os.getenv('CURIE_URL')


headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}


async def hit_gpt_api(payload):
    """
    Function that sends an asynchronous post request to GPT-3 API
    """
    try:
        # response = requests.post(MODEL_ENDPOINT, headers=headers, data=json.dumps(payload))
        async with aiohttp.ClientSession() as session:
            async with session.post(MODEL_ENDPOINT, headers=headers, data=json.dumps(payload)) as resp:
                print(resp.status)
                response = await resp.json()
        data = response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Request to remote server failed: {str(e)}")

    return data

async def hit_gpt_api1(payload):
    """
    Function that sends an asynchronous post request to GPT-3 API Fine-tuning
    """
    try:
        # response = requests.post(MODEL_ENDPOINT, headers=headers, data=json.dumps(payload))
        async with aiohttp.ClientSession() as session:
            async with session.post(CURIE_URL, headers=headers, data=json.dumps(payload)) as resp:
                print(resp.status)
                response = await resp.json()
        data = response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Request to remote server failed: {str(e)}")

    return data