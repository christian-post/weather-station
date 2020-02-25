import csv
import logging
import pygame as pg


class UI_Button(pg.sprite.Sprite):
    def __init__(self, state, image=None, rect=None, position=(0, 0),
                 callback=None, anchor='topleft',
                 callback_args=[], callback_kwargs={}):
        # add Button to sprite group
        super().__init__(state.ui_elements)
        if image:
            # image data from file
            self.image = image
            self.rect = image.get_rect()
            self.visible = True
        else:
            # invisible button
            self.image = pg.Surface(rect.size)
            self.image.fill(pg.Color('red'))
            self.rect = rect
            self.visible = False
        setattr(self.rect, anchor, position)
        self.callback = callback
        self.args = callback_args
        self.kwargs = callback_kwargs
    
    def update(self, mouse_pos, mouse_pressed):
        if self.rect.collidepoint(mouse_pos) and mouse_pressed:
            if self.callback:
                self.callback(*self.args, **self.kwargs)

    def draw(self, screen):
        if self.visible:
            screen.blit(self.image, self.rect)


def celsius(kelvin):
    try:
        return kelvin - 273.15
    except TypeError:
        logging.error(f'could not convert {kelvin} to celsius')
        return kelvin


def safe_format_c(temperature):
    try:
        return f'{celsius(temperature):.1f} C'
    except ValueError:
        return f'{temperature} C'


def replace_umlauts(string):
    umlauts = {
        'ä': 'ae',
        'ö': 'oe',
        'ü': 'ue',
        'ß': 'ss'
    }
    for key, value in umlauts.items():
        string = string.replace(key, value)
    return string


def load_weather_codes(filename):
    codes = {}
    with open(filename) as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=',')
        for i, row in enumerate(csv_reader):
            codes[row['ID']] = row
    return codes


def format_temperature(data):
    if type(data) == float:
        temp = celsius(data)
        return (f'{int(temp)}', f'{first_decimal(temp)}')
    elif type(data) == int:
        temp = celsius(data)
        return (f'{int(temp)}', '0')
    else:
        return ('--', '-')


def first_decimal(number):
    return str(round(number - int(number), 1))[2:] or '0'