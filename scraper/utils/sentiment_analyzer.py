"""
Simple sentiment analysis for posts.
Uses rule-based approach (can be enhanced with ML models later).
"""

import re
import logging
from typing import Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class Sentiment(Enum):
    """Sentiment classification."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# Positive and negative word lists (basic implementation)
# In production, use a proper sentiment lexicon or ML model
POSITIVE_WORDS = {
    "good",
    "great",
    "excellent",
    "amazing",
    "wonderful",
    "fantastic",
    "love",
    "like",
    "best",
    "awesome",
    "brilliant",
    "outstanding",
    "perfect",
    "superb",
    "terrific",
    "fabulous",
    "marvelous",
    "delightful",
    "happy",
    "joy",
    "pleased",
    "glad",
    "thrilled",
    "excited",
    "proud",
    "success",
    "achievement",
    "win",
    "victory",
    "triumph",
    "celebration",
    "thank",
    "grateful",
    "appreciate",
    "support",
    "help",
    "care",
}

NEGATIVE_WORDS = {
    "bad",
    "terrible",
    "awful",
    "horrible",
    "worst",
    "hate",
    "dislike",
    "disappointed",
    "sad",
    "angry",
    "frustrated",
    "upset",
    "worried",
    "concerned",
    "problem",
    "issue",
    "error",
    "fail",
    "failure",
    "mistake",
    "wrong",
    "difficult",
    "hard",
    "challenge",
    "struggle",
    "crisis",
    "emergency",
    "danger",
    "risk",
    "threat",
    "attack",
    "violence",
    "complaint",
    "criticize",
    "blame",
    "fault",
    "damage",
    "harm",
}


def analyze_sentiment(text: str) -> Dict[str, any]:
    """
    Analyze sentiment of text content.

    Args:
        text: Text content to analyze

    Returns:
        Dictionary with sentiment analysis:
        {
            'sentiment': 'positive' | 'negative' | 'neutral',
            'score': float (-1.0 to 1.0),
            'confidence': float (0.0 to 1.0)
        }
    """
    if not text:
        return {
            "sentiment": Sentiment.NEUTRAL.value,
            "score": 0.0,
            "confidence": 0.0,
        }

    # Normalize text
    text_lower = text.lower()

    # Count positive and negative words
    positive_count = sum(1 for word in POSITIVE_WORDS if word in text_lower)
    negative_count = sum(1 for word in NEGATIVE_WORDS if word in text_lower)

    # Check for negation (e.g., "not good")
    negation_pattern = r"\b(not|no|never|nothing|nobody|nowhere|neither|nor)\s+\w+"
    negations = len(re.findall(negation_pattern, text_lower))

    # Adjust counts for negations
    if negations > 0:
        # Simple heuristic: negations flip some sentiment
        positive_count = max(0, positive_count - negations // 2)
        negative_count = max(0, negative_count - negations // 2)

    # Calculate score (-1.0 to 1.0)
    total_words = len(text.split())
    if total_words == 0:
        score = 0.0
    else:
        score = (positive_count - negative_count) / max(total_words, 1)
        # Normalize to -1.0 to 1.0 range
        score = max(-1.0, min(1.0, score * 10))

    # Determine sentiment
    if score > 0.1:
        sentiment = Sentiment.POSITIVE
    elif score < -0.1:
        sentiment = Sentiment.NEGATIVE
    else:
        sentiment = Sentiment.NEUTRAL

    # Calculate confidence (based on how clear the signal is)
    total_sentiment_words = positive_count + negative_count
    if total_words == 0:
        confidence = 0.0
    else:
        confidence = min(1.0, total_sentiment_words / max(total_words, 1) * 5)

    return {
        "sentiment": sentiment.value,
        "score": round(score, 3),
        "confidence": round(confidence, 3),
    }


def get_tone_from_sentiment(sentiment_data: Dict[str, any]) -> Optional[str]:
    """
    Convert sentiment analysis to tone classification.

    Args:
        sentiment_data: Result from analyze_sentiment()

    Returns:
        Tone string (e.g., 'positive', 'negative', 'neutral')
    """
    return sentiment_data.get("sentiment", "neutral")
