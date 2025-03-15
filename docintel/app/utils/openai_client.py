import os
from openai import AzureOpenAI
import httpx

def create_azure_openai_client():
    """
    Create an AzureOpenAI client with proper configuration.
    This centralizes the client creation and avoids issues with proxy settings.
    """
    # Create a custom httpx client without proxy settings
    # This avoids the 'proxies' parameter error in newer OpenAI versions
    http_client = httpx.Client()
    
    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_API_VERSION", "2024-02-15-preview"),
        azure_endpoint=os.getenv("AZURE_ENDPOINT", "https://eyvoicecentralus.openai.azure.com/"),
        http_client=http_client
    ) 