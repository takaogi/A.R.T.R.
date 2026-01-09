import json
from src.utils.llm_client import LLMClient
from src.utils.logger import logger
from openai import OpenAIError

class WebSearchClient:
    """
    Client for performing Web Searches.
    Supports Multiple Engines:
    - 'openai': Uses OpenAI Responses API (gpt-5-nano) with web_search tool.
    - 'google': Uses functionality from ARTR Classic (Mock for now).
    """

    def __init__(self):
        self.openai_model = "gpt-5-nano" # As requested
    
    async def perform_search(self, query: str, engine: str = "auto") -> str:
        """
        Execute search based on strategy.
        Args:
            query: Search query string.
            engine: "openai", "google", or "auto" (default).
        """
        logger.info(f"WebSearch Request: '{query}' (Engine: {engine})")
        
        if engine == "auto":
            # Prefer OpenAI, fallback to Google (if implemented)
            engine = "openai"
        
        if engine == "openai":
            return await self._search_openai(query)
        elif engine == "google":
            return self._search_google(query)
        else:
            return f"Error: Unknown search engine '{engine}'."

    async def _search_openai(self, query: str) -> str:
        """
        Uses OpenAI Responses API to search the web.
        """
        client = LLMClient.get_client()
        
        try:
            # Note: Using undocumented/beta 'responses' API endpoint as per user request.
            # If the library version doesn't support 'responses', this will fail.
            # We assume 'openai' library is updated to support this hypothetical/beta feature.
            
            # The user snippet uses: client.responses.create(...)
            # AsyncClient also has 'responses' property usually.
            
            logger.debug(f"Calling OpenAI Search ({self.openai_model})...")
            
            # Construct the call
            # Note: using raw getattr or direct access if typing allows.
            # Assuming standard structure: client.responses.create
            
            # Since 'responses' might not be in the typing stubs yet, we might get warnings.
            # We strictly follow the user provided parameter structure.
            
            response = await client.responses.create(
                model=self.openai_model,
                reasoning={"effort": "low"},
                tools=[
                    {
                        "type": "web_search"
                    }
                ],
                input=query
            )
            
            # User example: response.output_text
            msg = response.output_text
            logger.info(f"OpenAI Search Success. Result Length: {len(msg)}")
            return msg

        except AttributeError:
             # Fallback if 'responses' API is missing from client
             logger.error("OpenAI Client does not support 'responses' API. Fallback to Chat Completions?")
             # For now, return error or try chat completion fallback?
             return "Error: OpenAI 'Responses API' not supported by current client version."
             
        except OpenAIError as e:
            logger.error(f"OpenAI Search Request Failed: {e}")
            return f"Search Failed: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected Error in OpenAI Search: {e}")
            return f"Search Error: {str(e)}"

    def _search_google(self, query: str) -> str:
        """
        Mock Google Search (Placeholder for ARTR Classic Logic).
        """
        logger.info("Executed Google Search (Mock).")
        return f"[Google Search Result] Mock results for: {query}\n1. Example Site A\n2. Example Site B"
