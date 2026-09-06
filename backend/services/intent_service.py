import re
from typing import Optional

# Predefined canned responses for pure greetings and chitchat
CHITCHAT_RESPONSES = {
    "hi": "Hello! How can I help you with your document today?",
    "hello": "Hello! How can I help you with your document today?",
    "hey": "Hello! How can I help you with your document today?",
    "hi there": "Hello! How can I help you with your document today?",
    "hello there": "Hello! How can I help you with your document today?",
    "hey there": "Hello! How can I help you with your document today?",
    "greetings": "Greetings! How can I assist you with your document today?",
    "good morning": "Good morning! How can I help you with your document today?",
    "good afternoon": "Good afternoon! How can I help you with your document today?",
    "good evening": "Good evening! How can I help you with your document today?",
    "good night": "Good night! Feel free to return if you have more questions about the document.",
    "thanks": "You're welcome! Let me know if you have any other questions about the document.",
    "thank you": "You're welcome! Let me know if you have any other questions about the document.",
    "thank you so much": "You're welcome! Let me know if you have any other questions about the document.",
    "thank you very much": "You're welcome! Let me know if you have any other questions about the document.",
    "thanks a lot": "You're welcome! Let me know if you have any other questions about the document.",
    "bye": "Goodbye! Have a great day, and feel free to return if you have more questions.",
    "goodbye": "Goodbye! Have a great day, and feel free to return if you have more questions.",
    "bye bye": "Goodbye! Have a great day, and feel free to return if you have more questions.",
    "see you": "Goodbye! Have a great day, and feel free to return if you have more questions.",
    "see you later": "Goodbye! Have a great day, and feel free to return if you have more questions.",
}


def get_chitchat_response(text: str) -> Optional[str]:
    """Check if input is purely an obvious greeting/chitchat.

    Returns a short natural response locally if the message is purely greeting
    or chitchat, or None if the query contains any substantive question
    or document-related instructions.
    
    Examples that return None (must go to RAG):
        - "hi, explain chapter 2"
        - "hello, what is this PDF about?"
        - "thanks, now explain the previous answer"
    """
    if not text:
        return None

    # Strip punctuation and collapse whitespace to lowercase
    cleaned = re.sub(r"[^\w\s]", "", text).strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)

    return CHITCHAT_RESPONSES.get(cleaned)
