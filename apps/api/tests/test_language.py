"""Deterministic answer-language detection (pure, no model calls)."""

from app.agent.language import detect_language, language_directive


def test_english_question_stays_english():
    assert detect_language("What are my rights if I am arrested?") == "english"
    assert detect_language("How does a court decide a child's custody?") == "english"


def test_urdu_script_detected():
    assert detect_language("میرے کیا حقوق ہیں؟") == "urdu"


def test_roman_urdu_detected():
    assert detect_language("Kya mujhe taleem ka haq hasil hai?") == "roman-urdu"
    assert detect_language("Bachay ki custody kaise milti hai?") == "roman-urdu"


def test_explicit_override_wins_over_script():
    # Urdu script, but the user explicitly asks for English.
    assert detect_language("مجھے حقوق بتائیں، answer in english") == "english"
    # English text, but the user asks for the reply in Urdu.
    assert detect_language("What is the punishment for theft? Answer in Urdu.") == "urdu"
    assert detect_language("Mere haq kya hain? English mein jawab do.") == "english"


def test_incidental_language_mention_does_not_override():
    # No request verb near "Urdu" -> not treated as a language request.
    assert detect_language("What rights do Urdu-speaking minorities have?") == "english"


def test_directive_matches_language_and_is_nonempty():
    assert "English" in language_directive("What is dowry?")
    assert "Urdu/Arabic script" in language_directive("جہیز کیا ہے؟")
    assert "Roman Urdu" in language_directive("Jahez kya hota hai aur iska haq kya hai?")
