import os
import logging
from openai import OpenAI

logger = logging.getLogger("desktopenv.vllm_client")

class VLLMClient:
    def __init__(self, base_url=None, api_key=None):
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "http://localhost:8000/v1")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "EMPTY")
        
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )
        logger.info(f"Initialized VLLMClient with base_url={self.base_url}")

    def chat(self, model, messages, max_tokens=32768, temperature=0.0, top_p=0.9, **kwargs):
        try:
            # vLLM supports standard OpenAI chat completions
            # Ensure image URLs are passed correctly in messages
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                extra_body=kwargs.get("extra_body", None) # For any vLLM specific params
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling vLLM: {e}")
            raise e
