from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_callback_buttons(
    *,
    buttons: dict[str, str],
    sizes: tuple[int] = (1, 1,)
):
    keyboards = InlineKeyboardBuilder()

    for text, data in buttons.items():
        keyboards.add(InlineKeyboardButton(text=text, callback_data=data))

    return keyboards.adjust(*sizes).as_markup()


def get_url_buttons(
    *,
    buttons: dict[str, str],
    sizes: tuple[int] = (2,)
):
    keyboards = InlineKeyboardBuilder()

    for text, url in buttons.items():
        keyboards.add(InlineKeyboardButton(text=text, url=url))

    return keyboards.adjust(*sizes).as_markup()


def get_inline_buttons(
    *,
    buttons: dict[str, str],
    sizes: tuple[int] = (2,)
):
    keyboards = InlineKeyboardBuilder()

    for text, value in buttons.items():
        if '://' in value:
            keyboards.add(InlineKeyboardButton(text=text, url=value))
        else:
            keyboards.add(InlineKeyboardButton(text=text, callback_data=value))

    return keyboards.adjust(*sizes).as_markup()