from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import JoinChannelRequest

from Headline_generetor import generate_headline, ad_check

import pymorphy3

import json

# Инициализация инструментов для бота

api_id = ""
api_hash = ""
phone_number = ""
device_model = "Redmi Note 12 Pro"
app_version = "10.3.2"
system_version = "11 (30)"
lang_code = "ru"

morph = pymorphy3.MorphAnalyzer()

client = TelegramClient(
    "client_new",
    api_id,
    api_hash,
    device_model=device_model,
    app_version=app_version,
    system_version=system_version,
    lang_code=lang_code,
).start()

bot = TelegramClient("bot_new", api_id, api_hash).start()

with open("save.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    last_messages = data.get("last_messages", {})
    for x in last_messages:
        last_messages[x] = []
    channels = data.get("channels", {})
    users = data.get("users", {})
    blacklist = data.get("blacklist", {})
    act = data.get("act", [])
    print(last_messages, channels, users, blacklist, act, sep=",")


data_to_save = {
    "last_messages": users,
    "channels": channels,
    "users": users,
    "blacklist": blacklist,
    "act": act,
}


def save():
    with open("save.json", "w", encoding="utf-8") as file:
        json.dump(data_to_save, file, ensure_ascii=False, indent=4)

# Обработка полученной новости

@client.on(events.NewMessage(func=lambda m: m.is_channel))
async def handler(event):
    global last_messages
    channel = event.message._sender.username
    for user in channels.get(channel, []):
        if orig_check(event.message.text, channel) and generate_headline(event.message.text) and not ad_check(event.message.text):
            if len(last_messages[user]) >= 5:
                await send_news(user)
                last_messages[user] = []
            last_messages[user].append(
                (
                    generate_headline(event.message.text),
                    f"[{channel}](https://t.me/{channel}/{event.message.id})",
                )
            )

    save()

# Проверка на оригинальность

def orig_check(text, channel):
    global last_messages
    message = set()
    for word in text.split():
        message.add(morph.parse(word)[0].normal_form)
    for user in channels[channel]:
        _blacklist = set(blacklist[user])
        _last_messages = last_messages[user]
        if message.intersection(_blacklist):
            return False
        for words in _last_messages:
            words = set(morph.parse(x)[0].normal_form for x in words[0].split())
            length = len(words)
            common_len = len(words.intersection(message))
            percent = (common_len / length) * 100
            if percent >= 40:
                return False
        return True


user_steps = {user: [0] for user in users}

# Рассылка новостей

async def send_news(user):
    global last_messages
    text = ""
    messages = last_messages[user]
    last_messages[user] = []
    for i, message in enumerate(messages):
        if text:
            text += "\n"
        text += str(i + 1) + ") " + message[0] + "\n" + message[1] + "\n\n"
    name = (await bot.get_entity(user)).first_name
    await bot.send_message(user, f"Сводка новостей для вас, {name}.")
    await bot.send_message(user, text, link_preview=False)

# ИНТЕРФЕЙС

# Команда start

@bot.on(events.NewMessage(pattern="/start"))
async def bot_start(event):
    user = event._sender.username
    if user not in users:
        users[user] = []
        last_messages[user] = []
        blacklist[user] = []
    user_steps[user] = [0]
    buttons = [
        [Button.inline("Подписки", "subscriptions")],
        [Button.inline("Чёрный список", "blacklist")],
    ]
    await event.respond(
        "Привет! Это - новостная лента в Телеграм. Я могу запомнить твои любимые каналы и передавать вам только самое интересное.",
        buttons=buttons,
    )
    save()


@bot.on(events.CallbackQuery(pattern="start"))
async def back_to_start(event):
    await event.delete()
    await bot_start(event)


# Команда subscriptions для работы с подписками

@bot.on(
    events.NewMessage(
        func=lambda e: user_steps.get(e._sender.username, [0])[-1] == "subscriptions"
    )
)
async def add_channel_name(event):
    sender_id = event._sender.username
    pr_event = user_steps[sender_id][0]
    user_steps[sender_id] = [0]
    try:
        channel_id = event.message.text.strip("@").lower()
        channel_name = await client.get_entity(channel_id)
        await client(JoinChannelRequest(channel_id))
        users[sender_id].append([channel_name.title, channel_id])
        if channel_id in channels:
            channels[channel_id].append(sender_id)
        else:
            channels[channel_id] = [sender_id]
    except:
        await bot.send_message(
            sender_id,
            "Похоже, такого канала не существует, либо я не могу получить к нему доступ. Проверьте, правильно ли вы отправили тег.",
        )
    await show_subscriptions(pr_event, new=True)
    save()

def create_subscription_buttons(subscriptions, page, total_pages):
    buttons = []
    for i, channel in enumerate(subscriptions):
        buttons.append([Button.inline(f"{channel} ❌", f"remove_{page}_{i}")])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(Button.inline("⬅️ Влево", f"prev_{page}"))
    if page < total_pages - 1:
        nav_buttons.append(Button.inline("Вправо ➡️", f"next_{page}"))

    nav_buttons.append(Button.inline("Добавить подписку", b"add_sub"))
    nav_buttons.append(Button.inline("Назад", b"start"))

    if nav_buttons:
        buttons.append(nav_buttons)

    return buttons

@bot.on(events.CallbackQuery(pattern="subscriptions"))
async def show_subscriptions(event, page=0, new=False):
    user_id = event._sender.username
    data = {"subscriptions": [c[0] for c in users[user_id]], "page": 0}
    subscriptions = data["subscriptions"]

    items_per_page = 10
    total_pages = (len(subscriptions) + items_per_page - 1) // items_per_page

    start = page * items_per_page
    end = start + items_per_page

    current_page_subscriptions = subscriptions[start:end]

    buttons = create_subscription_buttons(current_page_subscriptions, page, total_pages)
    if new:
        await bot.send_message(
            user_id,
            f"Ваши подписки (Страница {page + 1}/{total_pages}):",
            buttons=buttons,
        )
    else:
        await event.edit(
            f"Ваши подписки (Страница {page + 1}/{total_pages}):", buttons=buttons
        )

# Команда blacklist для работы с чёрным списком

@bot.on(
    events.NewMessage(
        func=lambda e: user_steps.get(e._sender.username, [0])[-1] == "blacklist"
    )
)
async def add_channel_name(event):
    global blacklist
    sender_id = event._sender.username
    pr_event = user_steps[sender_id][0]
    user_steps[sender_id] = [0]
    blacklist[sender_id] += [x.lower() for x in event.message.text.split()]
    await show_blacklist(pr_event, new=True)



def create_blacklist(blacklist, page, total_pages):
    buttons = []
    for i, word in enumerate(blacklist):
        buttons.append([Button.inline(f"{word} ❌", f"word_remove_{page}_{i}")])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(Button.inline("⬅️ Влево", f"word_prev_{page}"))
    if page < total_pages - 1:
        nav_buttons.append(Button.inline("Вправо ➡️", f"word_next_{page}"))

    nav_buttons.append(Button.inline("Добавить слова", b"words_add"))
    nav_buttons.append(Button.inline("Назад", b"start"))

    if nav_buttons:
        buttons.append(nav_buttons)

    return buttons


@bot.on(events.CallbackQuery(pattern="blacklist"))
async def show_blacklist(event, page=0, new=False):
    global blacklist
    user_id = event._sender.username
    data = {"blacklist": blacklist[user_id], "page": 0}
    current_blacklist = data["blacklist"]

    items_per_page = 10
    total_pages = (len(current_blacklist) + items_per_page - 1) // items_per_page

    start = page * items_per_page
    end = start + items_per_page

    current_page_blacklist = current_blacklist[start:end]

    buttons = create_blacklist(current_page_blacklist, page, total_pages)
    if new:
        await bot.send_message(
            user_id,
            f"Ваш чёрный список (Страница {page + 1}/{total_pages}):",
            buttons=buttons,
        )
    else:
        await event.edit(
            f"Ваш чёрный список (Страница {page + 1}/{total_pages}):", buttons=buttons
        )

# Перелистывание страниц списков

@bot.on(events.CallbackQuery(pattern=r"^(word_prev|word_next)"))
async def word_paginate(event):
    word, action, page_str = event.data.decode("utf-8").split("_")
    page = int(page_str)
    if action == "next":
        page += 1
    elif action == "prev":
        page -= 1
    await show_blacklist(event, page)


@bot.on(events.CallbackQuery(pattern=r"^(next|prev)"))
async def paginate(event):
    action, page_str = event.data.decode("utf-8").split("_")
    page = int(page_str)
    if action == "next":
        page += 1
    elif action == "prev":
        page -= 1
    await show_subscriptions(event, page)


@bot.on(events.CallbackQuery(pattern="remove"))
async def remove_subscription(event):
    page_str, index_str = event.data.decode("utf-8").split("_")[1:]
    page = int(page_str)
    index = int(index_str)

    user_id = event._sender.username

    users[user_id].pop(page * 10 + index)

    await show_subscriptions(event, page)
    save()


@bot.on(events.CallbackQuery(pattern="word_remove"))
async def remove_subscription(event):
    page_str, index_str = event.data.decode("utf-8").split("_")[2:]
    page = int(page_str)
    index = int(index_str)

    user_id = event._sender.username

    blacklist[user_id].pop(page * 10 + index)

    await show_blacklist(event, page)
    save()


@bot.on(events.CallbackQuery(pattern="add_sub"))
async def add_subscription(event):
    user_id = event._sender.username
    if user_steps[user_id] == [0]:
        user_steps[user_id] = (event, "subscriptions")
        await event.edit("Введите тег канала для подписки.")
    save()


@bot.on(events.CallbackQuery(pattern="words_add"))
async def add_words(event):
    user_id = event._sender.username
    if user_steps[user_id] == [0]:
        user_steps[user_id] = (event, "blacklist")
        await event.edit("Введите слова через пробел.")
    save()

client.run_until_disconnected()
bot.run_until_disconnected()

