from azure.identity import DefaultAzureCredential
from azure.ai.textanalytics import TextAnalyticsClient

credential = DefaultAzureCredential()
client = TextAnalyticsClient(
    endpoint="https://<seu-endpoint>.cognitiveservices.azure.com/",
    credential=credential
)
