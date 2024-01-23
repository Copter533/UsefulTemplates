import inspect
import os
import sys
from threading import Thread
from math import sin, cos, ceil, pi, dist, sqrt, radians
from random import randint
from time import time, sleep
from typing import overload, Iterable

import pygame as pg


class Settings:
    FPS = 60
    rate = .3
    coordinates = False
    draw_text = True

    background = '#FDF7F0'
    line = '#c7b095'
    dot = '#345278'

    col1 = '#FFCE5E'  # This is a bright yellow color.
    col2 = '#61E053'  # This is a vibrant green color.
    col3 = '#68B2F7'  # This is a light blue color.
    col4 = '#E053DF'  # This is a bright pink color.
    col5 = '#FF272A'  # This is a vibrant red color.
    outline = "#3A3A0A"

    def setBGR(self, value): self.background = self.line = value

    def darkMode(self):
        self.background = "#444444"
        self.line = "#222222"

    def slightlyDarkMode(self):
        self.background = "#333333"
        self.line = "#1a1a1a"

    def lightMode(self):
        self.background = '#FDF7F0'
        self.line = '#c7b095'


def detect_importer_filename():
    cur_frame = inspect.currentframe()
    if cur_frame is None: return "UNSET"
    prev_frames = inspect.getouterframes(cur_frame)

    for prev_frame in prev_frames:
        path = prev_frame.filename
        if os.path.exists(path) and path != __name__:
            return path
    else:
        return "SELF"


def rotate(point: tuple, anchor: tuple, angle: float) -> tuple:
    x, y = point
    ax, ay = anchor

    angle_rad = radians(angle)

    return\
        (x - ax) * cos(angle_rad) - (y - ay) * sin(angle_rad) + ax, \
        (x - ax) * sin(angle_rad) + (y - ay) * cos(angle_rad) + ay


def sgn(value):
    return 1 if value > 0 else (-1 if value < 0 else 0)


class Point:
    _x: int
    _y: int

    @overload
    def __init__(self, tupleV: tuple): pass
    @overload
    def __init__(self, x: float, y: float): pass

    def __init__(self, value1, value2=None):
        if isinstance(value1, Iterable):
            self._x, self._y = value1
        elif isinstance(value1, (int, float)):
            self._x, self._y = value1, value2
        else:
            raise ValueError()

    def __sub__(self, other): return Point((self.getX() - other.getX(), self.getY() - other.getY()))
    def __add__(self, other): return Point((self.getX() + other.getX(), self.getY() + other.getY()))

    def __mul__(self, other):     return Point((self.getX() * other, self.getY() * other))
    def __truediv__(self, other): return Point((self.getX() / other, self.getY() / other))

    def __neg__(self): return Point(-self._x, -self._y)
    def __iter__(self):
        yield self._x
        yield self._y

    def getX(self): return self._x
    def getY(self): return self._y

    def addX(self, value): self._x += value
    def addY(self, value): self._y += value

    def setX(self, value): self._x = value
    def setY(self, value): self._y = value

    def asTuple(self): return self.getX(), self.getY()
    def length2(self): return self._x ** 2 + self._y ** 2
    def length(self): return sqrt(self.length2())

    def normalized(self): return Point(self._x / self.length(), self._y / self.length())

    def normalize(self):
        length = self.length()
        self._x /= length
        self._y /= length


class InterpolatedValue:
    value: float
    dest: float

    def __init__(self, value, rate):
        self.factor = 1
        self.value = value
        self.rate = rate
        self.dest = value

    def set_dest(self, dest):
        self.dest = dest

    def tick(self):
        self.value += round((self.dest - self.value) * self.rate, 5)
        return self.value


class InterpolatedPoint:
    def __init__(self, point: Point, rate):
        self.point = point
        self.rate = rate
        self.dest = point
        self.factor = InterpolatedValue(1, .6)
        self.tick()

    def set_dest(self, dest: Point):
        self.dest = dest
        return dest

    def tick(self, factor=None):
        if factor is not None: self.factor.set_dest(factor)

        self.point.addX(round((self.dest.getX() - self.point.getX()) * self.rate, 5))
        self.point.addY(round((self.dest.getY() - self.point.getY()) * self.rate, 5))
        self.factor.tick()

        return self.point

    def getX(self): return self.point.getX()  # * self.factor.value

    def getY(self): return self.point.getY()  # * self.factor.value


class Display:
    def __init__(self):
        self.start_time = -1
        self.base_font = None
        self.clock = None
        self.surface: pg.surface.Surface = None
        self.settings = Settings()

        self.zoom_speed = 10
        self.scale = 100
        self.init_scale = self.scale
        self.Iscale = InterpolatedValue(self.scale, self.settings.rate)

        self.view = Point((0, 0))
        self.Iview = InterpolatedPoint(self.view, self.settings.rate)

        self.zoom_timer = 0
        self.zoom_msg_pos = 0

        self.toast_timer = 0
        self.toast_pos = 0
        self.toast_message = None
        self.toast_next_message = None

        self.click_circle_timer = 0
        self.click_circle_pos = (0, 0)
        self.objects = []

        self.draggables = set()
        self.dragging = None
        self.abstract = AbstractGraph(self)

    # def restoreX(self, x): return (x - self.midX()) / self.scale - self.view.getX() / self.scale
    # def restoreY(self, y): return (y - self.midY()) / self.scale - self.view.getY() / self.scale

    def run_forever(self, title=None):
        pg.init()
        filename = detect_importer_filename()
        cut = filename.rfind("\\", 0, filename.rfind("\\")) + 1
        pg.display.set_caption("↪ " + (title if title else "Whiteboard") + f" ↩ ({filename[cut:]})")
        self.clock = pg.time.Clock()
        self.surface = pg.display.set_mode((1000, 1000), pg.RESIZABLE)
        self.base_font = pg.font.SysFont('serif', 48)

        self.start_time = time()
        running = True

        print("Starting endless loop...")
        while running:
            self.tick()
            for event in pg.event.get():
                if event.type != pg.QUIT: continue
                running = False
                pg.quit()

    def tick(self):
        self.clock.tick(self.settings.FPS)
        self.surface.fill(self.settings.background)
        self.draw_grid()

        for obj in self.objects:
            if not self.settings.draw_text and isinstance(obj, GraphText): continue
            if not obj.hidden: obj.draw_me()
            if isinstance(obj, GraphTickable):
                obj.tick()

        self.zoom_tick()
        self.toast_tick()

        if self.settings.coordinates:
            x, y = pg.mouse.get_pos()

            message = \
                f' ~X: {round(self.abstract.restoreX(x))} ~Y: {round(self.abstract.restoreY(y))}' if\
                pg.key.get_pressed()[pg.K_LSHIFT] else\
                f' X: {self.abstract.restoreX(x):.2f} Y: {self.abstract.restoreY(y):.2f} '

            self.surface.blit(self.base_font.render(message, True, '#ffffff', '#000000'), (x, y))

        self.draw_click_circle()

        for i in pg.event.get():
            if i.type == pg.QUIT:
                pg.quit()
                sys.exit()
            elif i.type == pg.MOUSEMOTION:
                if not pg.mouse.get_pressed()[0]: continue
                vector = (pg.mouse.get_pos(), (Point(pg.mouse.get_pos()) + Point(i.rel)).asTuple())
                if self.dragging:
                    self.dragging.drag()
                    continue
                self.click_circle_pos = pg.mouse.get_pos()
                pg.draw.line(self.surface, self.settings.col2, *vector, width=10)
                self.view = self.Iview.set_dest(self.view + Point(i.rel))

            elif i.type == pg.MOUSEBUTTONDOWN:
                if i.button == pg.BUTTON_LEFT:
                    self.check_draggables()
                    self.click_circle_timer = 20
                    self.click_circle_pos = pg.mouse.get_pos()
                elif i.button == pg.BUTTON_WHEELUP:
                    self.set_zoom(self.scale + self.zoom_speed * self.scale / 20)
                elif i.button == pg.BUTTON_WHEELDOWN:
                    self.set_zoom(self.scale - self.zoom_speed * self.scale / 20)
                elif i.button == pg.BUTTON_RIGHT:
                    if self.scale != self.init_scale:
                        self.set_zoom(self.init_scale)
                    else:
                        self.set_zoom(self.init_scale * 2)
                elif i.button == pg.BUTTON_MIDDLE:
                    if dist(self.view.asTuple(), (0, 0)) > 10:
                        self.toast("Going to center...", 100)
                        self.view = Point((0, 0))
                        self.Iview.set_dest(self.view)

            elif i.type == pg.MOUSEBUTTONUP:
                if i.button == pg.BUTTON_LEFT:
                    self.dragging = None

            elif i.type == pg.KEYDOWN:
                if i.key == pg.K_e:
                    if self.settings.coordinates:
                        self.toast("Координаты OFF")
                    else:
                        self.toast("Координаты ON")
                    self.settings.coordinates = not self.settings.coordinates
                elif i.key == pg.K_r:
                    if self.settings.draw_text:
                        self.toast("Отрисовка текста OFF")
                    else:
                        self.toast("Отрисовка текста ON")
                    self.settings.draw_text = not self.settings.draw_text

        self.Iscale.tick()
        self.Iview.tick()

        pg.display.update()

    def check_draggables(self):
        for draggable in self.draggables:
            draggable: GraphDraggable
            if draggable.check(pg.mouse.get_pos()):
                draggable.on_click()
                self.dragging = draggable
                return True
        return False

    def draw_click_circle(self):
        if self.click_circle_timer <= 0: return

        self.click_circle_timer -= 1
        interpolation = sin(self.click_circle_timer / 40 * pi)
        pg.draw.circle(self.surface, self.settings.col3, self.click_circle_pos, int((1 - interpolation) * 30),
                       width=int(interpolation * 10 + 1))

    def zoom_tick(self):
        if self.zoom_msg_pos > 0:
            message = f' Zoom: {self.Iscale.value / self.init_scale:.2f}x '
            location = self.base_font.render(message, True, '#ffffff', '#000000')
            self.surface.blit(location,
                              (self.midX() - len(message) / 2 * 21, sin(self.zoom_msg_pos / 200 * pi) * 60 - 60))

        if self.zoom_timer > 0:
            self.zoom_msg_pos = min(self.zoom_msg_pos + 15, 100)
            self.zoom_timer -= 1
        else:
            if self.zoom_msg_pos > 0: self.zoom_msg_pos = max(self.zoom_msg_pos - 3, 0)

    def toast_tick(self):
        if self.toast_message is None: return

        lines = self.toast_message.count("\n") + 1
        if self.toast_pos > 0:
            locations = [
                self.base_font.render(f" {msg} ", True, '#ffffff', '#222222') for msg in self.toast_message.split("\n")
            ]
            self.toast_message: str
            for i, location in enumerate(locations):
                self.surface.blit(location, (10,
                                             self.surface.get_height()
                                             - sin(self.toast_pos / 200 * pi) * 60 * lines + 60 * (lines - 1)
                                             - 53 * (len(locations) - i - 1)
                                             )
                                  )

        if self.toast_timer > 0 and self.toast_next_message is None:
            if self.toast_pos < 100:
                self.toast_pos += 5
                if self.toast_pos > 100: self.toast_pos = 100
            else:
                self.toast_timer -= 1 if self.toast_next_message is None else 5
                if self.toast_timer < 0: self.toast_timer = 0
        else:
            if self.toast_pos > 0:
                self.toast_pos -= 5 if self.toast_next_message is None else 15
            else:
                self.toast_message = self.toast_next_message
                self.toast_next_message = None

    def midX(self):
        return self.surface.get_width() // 2

    def midY(self):
        return self.surface.get_height() // 2

    def draw_grid(self):
        scale = self.Iscale.value
        view_x, view_y = self.Iview.getX(), self.Iview.getY()

        count_x = ceil(self.surface.get_width() / scale) + 1
        count_y = ceil(self.surface.get_height() / scale) + 1
        x1 = view_x % scale - scale * ceil((count_x + 1) / 2)
        y1 = view_y % scale - scale * ceil((count_y + 1) / 2)
        lines_scale = int(min(max(scale // 100, 1), 3))
        font = pg.font.SysFont('serif', int(max(1, scale / self.init_scale * 20)))

        for i in range(count_x + 1):
            P = int(x1 + self.midX() + i * scale)
            pg.draw.line(self.surface, self.settings.line, (P, self.surface.get_height()), (P, 0), width=lines_scale)

            if self.settings.coordinates:
                static_x = (i - ceil((count_x + 1) / 2) - view_x // scale)
                stamp = font.render(f"{static_x:.0f}x", True, "#ffff55")
                self.surface.blit(stamp, (P, self.midY()))
                pg.draw.circle(self.surface, "#ffff55", (P, self.midY()), 2)

        for i in range(count_y + 1):
            P = int(y1 + self.midY() + i * scale)
            pg.draw.line(self.surface, self.settings.line, (self.surface.get_width(), P), (0, P), width=lines_scale)

            if self.settings.coordinates:
                static_y = (ceil((count_y + 1) / 2) - i + view_y // scale)
                stamp = font.render(f"{static_y:.0f}y", True, "#ffff11")
                self.surface.blit(stamp, (self.midX(), P))
                pg.draw.circle(self.surface, "#ffff11", (self.midX(), P), 2)

        # Middle marker
        # pg.draw.line(self.surface, self.settings.col4, (self.surface.get_width(), self.midX()), (0, self.midX()))
        # pg.draw.line(self.surface, self.settings.col4, (self.midY(), self.surface.get_height()), (self.midY(), 0))

    def set_zoom(self, zoomV):
        prev = self.scale
        self.scale = min(max(zoomV, 1), 5_000)  # 1, 5_000
        if abs(self.scale - self.init_scale) < 10: self.scale = self.init_scale
        self.Iscale.set_dest(self.scale)
        self.zoom_timer = 100
        self.view = self.view * (self.scale / prev)
        self.Iview.set_dest(self.view)

    def add_object(self, obj):
        assert isinstance(obj, AbstractGraph)
        self.objects.append(obj)
        if isinstance(obj, GraphDraggable): self.draggables.add(obj)

    def add_objects(self, *objs):
        for obj in objs: self.add_object(obj)

    def insert_object(self, obj, index):
        assert isinstance(obj, AbstractGraph)
        self.objects.insert(index, obj)
        if isinstance(obj, GraphDraggable): self.draggables.add(obj)

    def toast(self, message: str, timeMS: int = 1000):
        if self.toast_pos > 0:
            self.toast_next_message = message
            self.toast_timer = timeMS / 10
        else:
            self.toast_message = message
            self.toast_timer = timeMS / 10

    def await_key(self, key: str, delay_after=None):
        true_key = ord(key.lower()) if type(key) == str else key
        while True:
            keys = pg.key.get_pressed()
            if keys[true_key]: break
            sleep(0.05)

        if delay_after: sleep(delay_after)

    def scaling(self):  return self.scale / self.init_scale
    def Iscaling(self): return self.Iscale.value / self.init_scale

    def elapsed(self): return time() - self.start_time

    def set_view(self, x, y):
        self.Iview.set_dest(Point(-x * self.scaling() * 100, y * self.scaling() * 100))


class AbstractGraph:
    def __init__(self, display: Display): self.display, self.hidden = display, False

    def draw(self, *args, **kwargs): pass

    def transformX(self, x): return +x * self.display.Iscale.value + self.display.midX() + self.display.Iview.getX()
    def transformY(self, y): return -y * self.display.Iscale.value + self.display.midY() + self.display.Iview.getY()
    def transformAll(self, coords): return self.transformX(coords[0]), self.transformY(coords[1])

    def restoreX(self, x): return +(x - self.display.midX()) / self.display.scale - self.display.view.getX() / self.display.scale
    def restoreY(self, y): return -(y - self.display.midY()) / self.display.scale + self.display.view.getY() / self.display.scale

    def restoreSmoothX(self, x): return +(x - self.display.midX()) / self.display.Iscale.value - self.display.Iview.getX() / self.display.Iscale.value
    def restoreSmoothY(self, y): return -(y - self.display.midY()) / self.display.Iscale.value + self.display.Iview.getY() / self.display.Iscale.value

    def restoreAll(self, coords): return self.restoreX(coords[0]), self.restoreY(coords[1])

    def position(self): return Point(self.x, self.y)


class GraphTickable(AbstractGraph):
    def tick(self): pass


class GraphTurtle(GraphTickable):
    def __init__(self, display: Display, x, y, angle=180, speed=1, is_ghost=False, is_instant=False):
        super().__init__(display)

        self.is_instant = is_instant
        self.is_ghost   = is_ghost

        self.st = time()
        self.queue = []
        self.lines = [[x, y]]

        self.x, self.y = x, y
        self.angle = angle
        self.speed = speed

        self.Ipos   = InterpolatedPoint(Point(x, y), .5)
        self.Iangle = InterpolatedValue(angle, .5)

    def draw_me(self):
        x, y = self.Ipos.tick()
        iangle = self.Iangle.tick()

        if len(self.lines) > 1:
            lines = self.lines\
                if self.is_instant or dist(self.Ipos.point, self.Ipos.dest) < .1 else\
                    (self.lines[:-1] + [[x, y]])
            pg.draw.lines(self.display.surface, "#ff0000", False, tuple(map(self.transformAll, lines)), width=5)

        if self.is_ghost: return

        points1 = map(
            lambda e: rotate(e, (x, y), iangle),
            (
                (+0.0 + x, +0.0 + y),
                (+0.2 + x, -0.5 + y),
                (+0.0 + x, -0.4 + y),
                (-0.2 + x, -0.5 + y)
            )
        )
        points2 = map(
            lambda e: rotate(e, (x, y), iangle),
            (
                (+0.0 + x, -0.06 + y),
                (+0.155 + x, -0.45 + y),
                (+0.0 + x, -0.37 + y),
                (-0.155 + x, -0.45 + y)
            )
        )

        pg.draw.polygon(self.display.surface, "#000000", tuple(map(self.transformAll, points1)))
        pg.draw.polygon(self.display.surface, "#ffffff", tuple(map(self.transformAll, points2)))

    def tick(self):
        if not self.is_instant and time() - self.st < 0.3 / self.speed: return
        if not self.queue: return

        self.st = time()
        action, data = self.queue.pop(0)
        match action:
            case "forward":
                xo, yo = rotate((0, data), (0, 0), self.angle)
                self.x += xo
                self.y += yo
                self.lines.append([self.x, self.y])
                self.Ipos.set_dest(Point(self.x, self.y))
            case "turn":
                self.angle += data
                self.Iangle.set_dest(self.angle)

    def forward(self, distance): self.queue.append(("forward", distance))
    def right(self, angle): self.queue.append(("turn", angle))
    def left(self, angle): self.queue.append(("turn", -angle))

    def clear(self): self.lines = [[self.x, self.y]]

    def goto(self, xt, yt):
        self.x, self.y = xt, yt
        self.lines.append([self.x, self.y])
        self.Ipos.set_dest(Point(self.x, self.y))


class GraphImage(AbstractGraph):
    def __init__(self, display: Display, x, y, x_size, y_size, image_path):
        super().__init__(display)
        self.image = pg.image.load(image_path)
        self.x, self.y = x, y
        self.resize(x_size, y_size)

    def draw_me(self):
        scaled_image = pg.transform.scale(
            self.image, (self._x_size * self.display.Iscale.value, self._y_size * self.display.Iscale.value)
        )
        image_rect = scaled_image.get_rect()
        image_rect.center = (
            self.transformX(self.x),
            self.transformY(self.y)
        )
        self.display.surface.blit(scaled_image, image_rect)

    def resize(self, new_x_size, new_y_size):
        self._x_size, self._y_size = max(0, new_x_size), max(0, new_y_size)


class GraphDraggable(AbstractGraph):
    def __init__(self, display: Display, x, y, color="#ff0011", size=1, snap=None,
                 before_updater=None, after_updater=None, blocked_axis=""):
        super().__init__(display)
        self.blocked_axis = blocked_axis.lower()
        self.size = size
        self.x, self.y = x, y
        self.color = color
        self.Ipos = InterpolatedPoint(Point((x, y)), 0.4)
        self.snap = snap

        self.before_updater = before_updater
        self.after_updater  = after_updater

        if after_updater:  after_updater (self, x, y)
        if before_updater: before_updater(self, x, y)

    def draw_me(self):
        self.Ipos.tick(1)
        self.radius = self.display.Iscale.value / 4 * self.size
        self.center = (self.transformX(self.Ipos.getX()), self.transformY(self.Ipos.getY()))

        pg.draw.circle(self.display.surface, self.color, self.center, self.radius)
        pg.draw.circle(self.display.surface, "#000000", self.center, self.radius, 5)

    def move_to(self, x, y):
        self.x, self.y = x, y
        self.Ipos.set_dest(Point(x, y))

    def on_click(self):
        pass

    def check(self, pos):
        return (pos[0] - self.transformX(self.x)) ** 2 + (pos[1] - self.transformY(self.y)) ** 2 <= self.radius ** 2

    def drag(self):
        x = self.restoreX(pg.mouse.get_pos()[0]) if "x" not in self.blocked_axis else self.x
        y = self.restoreY(pg.mouse.get_pos()[1]) if "y" not in self.blocked_axis else self.y
        if self.snap:
            new_coords = map(lambda i: round(i / self.snap) * self.snap, (x, y))
            new_x, new_y = new_coords

            was_updated = (new_x != self.x or new_y != self.y)
            if self.before_updater and was_updated: self.before_updater(self, new_x, new_y)
            self.x, self.y = new_x, new_y
            if self.after_updater  and was_updated: self.after_updater(self)
        else:
            if self.before_updater: self.before_updater(self, x, y)
            self.x, self.y = x, y
            if self.after_updater:  self.after_updater(self)

        self.Ipos.set_dest(Point(self.x, self.y))

    def connect_updater(self, updater):
        self.before_updater = updater


class GraphRect(AbstractGraph):
    def __init__(self, display: Display, x, y, x_size, y_size, color=None, shadow=0):
        super().__init__(display)
        self.color = color if color else [randint(0, 255) for _ in range(3)]
        self.shadow = (1 - shadow)

        self.x, self.y = x, y
        self.x_size, self.y_size = x_size, y_size

    def draw_me(self):
        rect = (
            self.transformX(self.x - self.x_size / 2),
            self.transformY(self.y + self.y_size / 2),

            self.x_size * self.display.Iscale.value,
            self.y_size * self.display.Iscale.value
        )

        if self.shadow != 1:
            shadow = max(self.x_size * self.display.Iscale.value * self.shadow,
                         self.y_size * self.display.Iscale.value * self.shadow)
            pg.draw.rect(self.display.surface, "#000000", (
                             rect[0] - shadow,
                             rect[1] - shadow,
                             rect[2] + shadow * 2,
                             rect[3] + shadow * 2
            ))

        pg.draw.rect(self.display.surface, self.color, rect)


class GraphText(AbstractGraph):
    def __init__(self, display: Display, text, x, y, color="#eeeeee", scale=None):
        super().__init__(display)
        self.color = color
        self.x, self.y = x, y

        self._font = pg.font.SysFont('serif', int((100 if scale is None else scale) * 100 / self.display.scale))
        self.scale = scale

        self.change(text=text)

    def draw_me(self):
        if self.scale: self.update()
        self.display.surface.blit(self.stamp, (self.transformX(self.x) - self.stamp.get_width() // 2, self.transformY(self.y) - self.stamp.get_height() // 2))

    def update(self):
        if self.scale:
            self._font = pg.font.SysFont('serif',
                int(max(1, min(3000, self.display.Iscale.value / self.display.init_scale * self.scale))))
        self.stamp = self._font.render(self._text, True, self.color)

    def change(self, text=None):
        if text is not None: self._text = text
        self.update()


class GraphDot(AbstractGraph):
    def __init__(self, display: Display, x, y, color="#44ff44", scale=30, shadow=False, label=None):
        super().__init__(display)
        self.label = label
        self.shadow = shadow
        self.scale = scale
        self.color = color
        self.x, self.y = x, y

    def draw_me(self):
        scale = max(1, int(self.scale * self.display.Iscale.value / self.display.init_scale))
        center = (self.transformX(self.x), self.transformY(self.y))
        if self.shadow: pg.draw.circle(self.display.surface, "#000000", center, scale + 2)
        pg.draw.circle(self.display.surface, self.color, center, scale)
        if self.label:
            self._font = pg.font.SysFont('serif', int(max(1, min(3000, self.display.Iscale.value / self.display.init_scale * 50))))
            stamp = self._font.render(self.label, True, "#ffffff")
            self.display.surface.blit(stamp, (self.transformX(self.x) - stamp.get_width() // 2,
                                              self.transformY(self.y) - self.scale * self.display.Iscaling() - stamp.get_height()))


class GraphLine(AbstractGraph):
    def __init__(self, display: Display, xF, yF, xT, yT, color="#ff4444", width=3):
        super().__init__(display)
        self.color = color
        self.width = width
        self.From, self.To = (xF, -yF), (xT, -yT)

    def draw_me(self):
        pg.draw.line(self.display.surface, self.color,
                     (self.transformX(self.From[0]), self.transformY(self.From[1])),
                     (self.transformX(self.To[0]), self.transformY(self.To[1])),
                     width=self.width)

    def setFrom(self, xF, yF): self.From = (xF, yF)
    def setTo(self, xT, yT): self.To = (xT, yT)


class GraphPlot(AbstractGraph):
    def __init__(self, display: Display, function, step=100, static: bool = False, maxSize: int = 100, color: str = None):
        super().__init__(display)
        self.step = step
        self.function = function
        self.static = static
        if static:
            self.values = {}
            self.mSize = maxSize
        self.name = None
        self.color = (randint(100, 255), randint(100, 255), randint(100, 255)) if color is None else color

    def set_tag(self, name: str, color: str):
        self.name = name
        self.color = color

    def draw_me(self):
        prev = None
        left_edge = self.restoreSmoothX(0)
        right_edge = self.restoreSmoothX(self.display.surface.get_width())

        # self.step = ceil(self.display.scaling() * 100)

        is_first = True
        used_values = set()
        for j in range(int(left_edge * self.step), ceil(right_edge * self.step) + 1):
            used_values.add(j)
            i = j / self.step
            if self.static and j in self.values:
                joint = self.values[j]
            else:
                try:
                    joint = -self.function(i)
                except (ArithmeticError, ValueError, TypeError):
                    joint = None
                if self.static:
                    self.values[j] = joint

            if joint is not None:
                new_point = self.transformX(i), self.transformY(-joint)

                if prev is None and not is_first:
                    pg.draw.circle(self.display.surface, self.color, new_point, 3)

            if joint is not None and prev is not None:
                # noinspection PyUnboundLocalVariable
                pg.draw.line(self.display.surface, self.color, prev, new_point, 2)

            elif joint is None and prev is not None:
                pg.draw.circle(self.display.surface, self.color, prev,  3)

            prev = new_point if joint is not None else None

            is_first = False

        if self.static and len(self.values) > self.mSize:
            keyset = tuple(self.values.keys())
            for key in keyset:
                if key in used_values: continue
                del self.values[key]


if __name__ == "__main__":
    dp = Display()
    Thread(target=dp.run_forever, args=("Графики...",)).start()

    dp.settings.darkMode()
    # dp.add_object(
    #     GraphPlot(dp,
    #               lambda x: None if x != int(x) else max([i for i in range(2, int(x)) if x % i == 0]) / 6,
    #               step=2, static=True, maxSize=5000)
    # )

    l = GraphLine(dp, 0, 0, 20, 0)
    dp.add_object(l)
    dp.add_object(GraphPlot(dp, lambda x: sum(map(int, str(int(x)))) if x >= 0 else None, step=1))
    dp.add_object(GraphPlot(dp,
                            lambda x: sum(map(int, str(int(x))))
                            if sum(map(int, str(int(x))[:2])) == sum(map(int, str(int(x))[2:])) and len(set(str(int(x)))) == 4 else None,
    step=1))
    sleep(1)
    while True:
        x, y = map(lambda x: x / dp.Iscale.value, dp.Iview.point.asTuple())
        l.setFrom(-x - 10, y)
        l.setTo(-x + 10, y)
        sleep(0.03)
