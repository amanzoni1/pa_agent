# app/tools/mail_tools.py
import os
import logging
from langchain_core.tools import tool
from langchain_google_community import GmailToolkit

logger = logging.getLogger(__name__)

# Initialize the Gmail toolkit (reads credentials.json by default)
# Ensure you have run the Gmail API setup and have credentials.json in your project root
try:
    toolkit = GmailToolkit()
    gmail_tools = toolkit.get_tools()
except Exception as e:
    logger.exception("Failed to initialize GmailToolkit: %s", e)
    gmail_tools = []  # fallback to empty list

# Export each Gmail tool as a langgraph-compatible tool
# We'll dynamically expose them in __init__.py
# Example tools in gmail_tools:
#  - GmailCreateDraft
#  - GmailSendMessage
#  - GmailSearch
#  - GmailGetMessage
#  - GmailGetThread


# You can also wrap them if you want to rename or simplify args:
# @tool
def send_email_via_gmail(to: str, subject: str, body: str) -> str:
    """
    Shortcut wrapper around GmailSendMessage tool.
    """
    try:
        draft = toolkit.invoke_tool(
            "GmailCreateDraft",
            {
                "to": [to],
                "subject": subject,
                "message": body,
            },
        )
        send = toolkit.invoke_tool("GmailSendMessage", {"message_id": draft["id"]})
        return f"Email sent (ID: {send.get('id')})"
    except Exception as e:
        logger.exception("send_email_via_gmail failed: %s", e)
        return f"⚠️ Email send error: {e}"
