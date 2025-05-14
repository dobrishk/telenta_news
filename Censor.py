blacklist = {'popka' : 'mamonta'}
def ret():
    return blacklist['popka']

def new_check(message, user, last_messages):
    _blacklist = blacklist[user]
    _last_messages = last_messages[user]
    if message.intersection(_blacklist):
        return False
    for words in _last_messages:
        length = len(words)
        common_len = len(words.intersection(message))
        percent = (common_len / length) * 100
        if percent >= 40:
            return False
    return True