from azure.ai.textanalytics import TextAnalyticsClient
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
client = TextAnalyticsClient(
    endpoint="https://<seu-endpoint>.cognitiveservices.azure.com/",
    credential=credential,
)
