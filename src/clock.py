import datetime
import calendar
import traceback
import pygame as pg

# TODO: a.m. and p.m.

def get_weekday():
    year = datetime.datetime.now().year
    month = datetime.datetime.now().month
    day = datetime.datetime.now().day
    weekday = calendar.weekday(year, month, day)
    return (calendar.day_name[weekday],
            day, month, year)


def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Clock:
    def __init__(self, app, fontsize, fgcolor, bgcolor=None):
        self.app = app

        self.seconds = 0
        self.minutes = 0
        self.hours = 0
        self.time_string = ''
        self.synced = False
        self.hour_mode = 24

        self.rect = None
        self.image = None
        self.fontsize = fontsize
        self.fgcolor = fgcolor
        self.bgcolor = bgcolor

        # a dictionary of timers for certain events
        self.timers = {}
        self.timer_events = []

        self.update_time()

    def update_time(self):
        time = datetime.datetime.now().time()
        ms = time.microsecond
        self.seconds = time.second + ms / 1000000
        self.minutes = time.minute + self.seconds / 60
        self.hours = time.hour % self.hour_mode + self.minutes / 60

    def construct_image(self):
        font = self.app.font
        txt = self.time_string
        self.image, self.rect = font.render(txt,
                                            fgcolor=self.fgcolor,
                                            bgcolor=self.bgcolor,
                                            size=self.fontsize)

    def clear_timer_events(self):
        events = {name: event for name, event in self.timer_events}
        self.timer_events = []
        return events

    def add_timer(self, name, seconds, callback):
        self.timers[name] = [seconds, 0, callback]

    def update(self, dt, show_seconds=True):
        self.seconds = (self.seconds + dt) % 60
        self.minutes = (self.minutes + dt / 60) % 60
        self.hours = (self.hours + dt / 3600) % self.hour_mode
        if show_seconds:
            self.time_string = (f'{int(self.hours):02d}:'
                                f'{int(self.minutes):02d}:'
                                f'{int(self.seconds):02d}')
        else:
            self.time_string = (f'{int(self.hours):02d}:'
                                f'{int(self.minutes):02d}')

        self.construct_image()

        # sync time after one minute
        if int(self.seconds) % 60 == 0:
            if not self.synced:
                self.update_time()
                self.synced = True
        else:
            self.synced = False

        # check for elapsed timers
        for name, timer in self.timers.items():
            # advance the timer
            timer[1] += dt
            # check against the first item
            if timer[1] >= timer[0]:
                timer[1] = 0
                self.timer_events.append((name, timer[2]))

    def draw(self, screen, pos, align):
        try:
            setattr(self.rect, align, pos)
            screen.blit(self.image, self.rect)
        except pg.error:
            traceback.print_exc()
