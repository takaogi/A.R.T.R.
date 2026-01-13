import openai
from dotenv import load_dotenv
load_dotenv()

print(f"OpenAI Version: {openai.__version__}")
try:
    client = openai.OpenAI()
    print(f"Has Responses: {hasattr(client, 'responses')}")
except Exception as e:
    print(f"Error init client: {e}")
