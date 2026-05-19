import os
import httpx
import logging

STORAGE_API_URL = os.getenv("STORAGE_API_URL")

async def forward_to_storage(prompt: str, response: str):
    payload = {"prompt": prompt, "response": response}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(STORAGE_API_URL, json=payload)
            r.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to store response: {e}")
