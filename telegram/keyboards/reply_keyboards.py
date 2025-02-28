from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


'''Keyboard generator'''
def get_keyboard(
        *buttons: str,
        placeholder: str = None,
        request_contact: int = None,
        request_location: int = None,
        sizes: tuple[int] = (1, 1)
):
    """
    Parameters request_contact and request_location must be as indexes of button arguments for buttons you need
    Example usage:
    get_keyboard(
        "Menyu",
        "Biz haqimizda",
        "To\'lov",
        "Yetkazib berish",
        "Kontaktni jo\'natish",
        placeholder="Amaliyot turini tanlang:",
        request_contact=5,   # request_contact is True for 5th button called "Kontaktni jo\'natish",
        sizes=(2, 2, 1)     # 3 rows of 2, 2, and 1 buttons respectively
    )
    """

    keyboard = ReplyKeyboardBuilder()

    for index, text in enumerate(buttons, start=1):
        if request_contact and request_contact == index:
            keyboard.add(KeyboardButton(text=text, request_contact=True))
        elif request_location and request_location == index:
            keyboard.add(KeyboardButton(text=text, request_location=True))
        else:
            keyboard.add(KeyboardButton(text=text))

    return keyboard.adjust(*sizes).as_markup(resize_keyboard=True, input_field_placeholder=placeholder)