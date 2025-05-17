from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
import re
from pymorphy3 import MorphAnalyzer

morph = MorphAnalyzer()
SUMMARIZE_MIN_WORDS = 50  # Минимальная длина для суммаризации


def clean_channel_references(text):
    text = re.sub(r'\(https://t\.me/[^\s)]+\)', '', text)
    text = re.sub(r'[\u2700-\u27BF\uE000-\uF8FF\u2000-\u2BFF][^\n]+$', '', text)
    return text.strip()


def generate_headline(text, num_sentences=3):
    try:
        text = clean_channel_references(text)
        if not text:
            return ""

        # Всегда извлекаем первое предложение
        sentences = [s.strip() for s in text.split('. ') if s.strip()]
        first_sentence = sentences[0] + '. ' if sentences else ""

        # Если текст слишком короткий - возвращаем только заголовок
        if len(sentences) < 2 or len(text.split()) < SUMMARIZE_MIN_WORDS:
            return first_sentence

        # Суммаризация оставшегося текста
        remaining_text = '. '.join(sentences[1:])
        parser = PlaintextParser.from_string(remaining_text, Tokenizer("russian"))
        summarizer = LsaSummarizer()
        summary = summarizer(parser.document, num_sentences)

        # Формируем результат даже при пустой суммаризации
        summarized_text = ' '.join(str(s) for s in summary).strip()

        return f"{first_sentence}\n{summarized_text}" if summarized_text else first_sentence

    except Exception as e:
        # Возвращаем хотя бы заголовок при любых ошибках
        return first_sentence if sentences else "Новость недоступна"


def ad_check(post_text):
    AD_KEYWORDS = {
        "купить", "продажа", "акция", "скидка", "промокод",
        "реклама", "заказ", "доставка", "розыгрыш", "партнерка"
    }

    normalized = {
        morph.parse(word)[0].normal_form
        for word in post_text.lower().split()
        if len(word) > 3
    }
    return len(normalized & AD_KEYWORDS) >= 2
