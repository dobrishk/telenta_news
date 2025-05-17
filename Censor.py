blacklist = {}


def new_check(message, user, last_messages):
    _blacklist = set(blacklist.get(user, []))
    _last_messages = last_messages.get(user, [])

    # Проверка по чёрному списку
    message_words = set(message.lower().split())
    if message_words & _blacklist:
        return False

    # Проверка на дубликаты (40% совпадений)
    for stored_msg, _ in _last_messages:
        stored_words = set(stored_msg.lower().split())
        common = len(stored_words & message_words)
        if (common / len(stored_words)) * 100 >= 40:
            return False
    return True
