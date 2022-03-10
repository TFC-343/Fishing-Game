#! /usr/bin/env python3.9

"""
fishing game in python
"""

__author__ = "TFC343"
__version__ = "0.8.0"
__build__ = "16"

import collections  # namedtuple
import copy  # copy
import math  # ciel
import pickle  # load, dump
import random  # randint
import sys  # exc_info
import time  # perf_counter
import logging  # info
import os.path  # exists
import typing  # Union
from functools import cache

from base_funtions import Pos, Multiplier

import pygame
import pygame.gfxdraw
from pygame.locals import *

logging.basicConfig(level=logging.NOTSET, format="[%(levelname)s] -> %(msg)s")
pygame.init()
pygame.font.init()


class User:
    def __init__(self):
        self.current_room = area_start
        self.current_pos = 750, 1350
        self.inventory = []
        self.save_slot = 0

    def update(self, new_room, new_pos):
        self.current_room = new_room
        self.current_pos = new_pos


class Fish:
    def __init__(self, name, image, size, colour):
        self.name = name
        self.size = size
        self.colour = colour


class Material:
    def __init__(self, name, luck_mod):
        self.name = name
        self.luck_mod = luck_mod


class FishingRod:
    def __init__(self):
        self.pole = POLES["wood"]
        self.string = STRINGS["weak string"]
        self.hook = HOOKS["basic hook"]


class Player:
    def __init__(self, x, y):
        self.pos = Pos(x, y)
        self.surface = pygame.Surface((36, 36))
        self.surface.fill('red')

        self.speed = 7

    @property
    def rect(self):
        return self.get_surface().get_rect(center=self.pos.get_tuple())

    def get_surface(self):
        return self.surface

    def draw(self, surface):
        surface.blit(self.get_surface(), self.rect)


class Block:
    def __init__(self, rect: pygame.Rect, texture, solid=False, texture_scale=1.0, level=0, popup_text=None,
                 destination=None, frames=None, anim_freq=10):
        self.invisible = False
        self.popup = False
        self.door = False
        self.animated = False
        if texture != "popup" and popup_text is not None:
            raise Exception("cannot add popup text to a non popup")
        else:
            self.popup_text = popup_text
        if texture != "door" and destination is not None:
            raise Exception("cannot add destination to non door")
        else:
            self.destination = destination

        if isinstance(texture, pygame.Color):
            self.image = pygame.Surface((rect.width, rect.height))
            self.image.fill(texture)
        if isinstance(texture, pygame.Surface):
            self.image = pygame.Surface(rect.size, SRCALPHA)
            a = self.image.get_size()[0] / (texture.get_size()[0] * Multiplier(texture_scale))
            b = self.image.get_size()[1] / (texture.get_size()[1] * Multiplier(texture_scale))
            texture = pygame.transform.scale(texture, (
            texture.get_size()[0] * Multiplier(texture_scale), texture.get_size()[1] * Multiplier(texture_scale)))
            for y in range(math.ceil(b)):
                for x in range(math.ceil(a)):
                    self.image.blit(texture, (texture.get_size()[0] * x, texture.get_size()[1] * y))
        if isinstance(texture, str):
            if texture == "invisible":
                self.invisible = True
            if texture == "popup":
                self.popup = True
                self.invisible = True
            if texture == "door":
                self.door = True
                self.invisible = True
            if texture == "anim":
                self.frame = 0
                self.frames = []
                for f in frames:
                    s = pygame.Surface(rect.size)
                    s.blit(f, (0, 0))
                    self.frames.append(s)
                self.animated = True
                self.frame_speed = anim_freq
                self.anim_index = 0

        self.rect = rect

        self.solid = solid
        self.level = level

    def draw(self, surface: pygame.Surface):
        if self.animated:
            surface.blit(self.frames[self.anim_index], self.rect)
            if self.frame % self.frame_speed == 0:
                self.anim_index = (self.anim_index + 1) % len(self.frames)
            self.frame += 1
        elif not self.invisible:
            surface.blit(self.image, self.rect)


def corner_to_rect(top_right, bottom_left):
    return pygame.Rect(top_right[0], top_right[1], bottom_left[0] - top_right[0], bottom_left[1] - top_right[1])


def load_users() -> list[typing.Union[User, None], typing.Union[User, None], typing.Union[User, None], typing.Union[User, None]]:
    users = [None, None, None, None]
    for i, user in enumerate(users):
        if os.path.exists(f"user{i + 1}.pickle"):
            with open(f"user{i + 1}.pickle", 'rb') as f:
                users[i] = pickle.load(f)
                users[i].save_slot = i + 1
    logging.info("loaded users")
    return users


def save_user(user: User):
    with open(f"user{user.save_slot}.pickle", 'wb') as f:
        pickle.dump(user, f, pickle.HIGHEST_PROTOCOL)
    logging.info("user data saved")


def area_start():
    a = copy.copy(AREA)  # collections.namedtuple("Area", ['size', 'surf', 'background_image', 'blocks'])
    a.name = "start"

    a.size = 1500, 1500
    world_width, world_height = a.size

    blocks = [Block(corner_to_rect((640, 0), (860, world_height)), pygame.image.load("gravel_texture.png"),
                    texture_scale=0.75),  # path
              Block(corner_to_rect((0, 1450), (world_width, 1475)), pygame.Color(105, 68, 16), solid=True),
              # fence bottom
              Block(corner_to_rect((25, 0), (50, world_height)), pygame.Color(105, 68, 16), solid=True),  # fence left
              Block(corner_to_rect((1450, 0), (1475, world_height)), pygame.Color(105, 68, 16), solid=True),
              # fence right
              Block(Rect(0, -20, world_width, -15), "door",
                    destination=(area_town, lambda x: (x[0], 1995)))]  # transition to town

    for i in range(7):
        blocks.append(
            Block(pygame.Rect(590 + i * 50, 1440, 20, 45), pygame.Color(89, 58, 14), solid=True))  # fence posts

    img = pygame.image.load("sign_texture.png")
    top = pygame.Surface((18, 10))
    top.blit(img, (0, 0))
    bottom = pygame.Surface((18, 3), SRCALPHA)
    bottom.blit(img, (0, -10))
    blocks.append(Block(pygame.Rect(850, 800, 18 * 6, 10 * 6), top, texture_scale=6, level=2))  # top of sign
    blocks.append(
        Block(pygame.Rect(850, 800 + 10 * 6, 18 * 6, 4 * 6), bottom, texture_scale=6, level=0))  # bottom of sign
    blocks.append(Block(pygame.Rect(850, 800 + 2 * 6, 18 * 6, 8 * 6), "invisible", solid=True))  # sign hitbox
    blocks.append(Block(corner_to_rect((850, 890), (958, 950)), "popup",
                        popup_text="welcome to fishington\ngo forward"))  # pop up
    blocks.append(
        Block(corner_to_rect((500, 1440), (540, 1450)), pygame.Color(255, 255, 255), level=2))  # note on fence
    blocks.append(Block(corner_to_rect((465, 1380), (565, 1425)), "popup", popup_text="Road Closed"))  # pop up for note

    a.blocks = blocks

    a.background_image = pygame.transform.scale(pygame.image.load("sand_texture.png"), a.size)
    a.surf = pygame.Surface(a.size)
    # a.background_surf.blit(pygame.transform.scale(pygame.image.load("sand_texture.png"), a.size), (0, 0))

    return a


def area_town():
    a = copy.copy(AREA)
    a.name = "town"

    a.size = 1500, 2000
    a.surf = pygame.Surface(a.size)
    s = pygame.Surface(a.size)
    s.blit(pygame.image.load("sand_texture.png"), (0, 0))
    s.blit(pygame.image.load("sand_texture.png"), (0, 1500))
    a.background_image = s
    a.blocks = [
        Block(corner_to_rect((640, 0), (860, a.size[1])), pygame.image.load("gravel_texture.png"), texture_scale=0.75),
        Block(corner_to_rect((25, 0), (50, a.size[1])), WOOD1, solid=True),  # left fence
        Block(corner_to_rect((1450, 0), (1475, a.size[1])), WOOD1, solid=True),  # right fence
        Block(Rect(0, a.size[1] + 15, a.size[0], a.size[1] + 20), "door",
              destination=(area_start, lambda x: (x[0], 5)))]
    a.blocks.append(Block(corner_to_rect((405, 1575), (640, 1695)), pygame.image.load("gravel_texture.png"), texture_scale=0.75))
    a.blocks.append(Block(corner_to_rect((300, 1500), (405, 1770)), pygame.color.Color('white'), level=2))
    for i in range(11):
        a.blocks.append(Block(pygame.Rect(300, 1500 + 25 * i, 55, 10), pygame.color.Color('blue'), level=2))
    a.blocks.append(Block(pygame.Rect(355, 1500, 50, 270), pygame.color.Color(WOOD1), level=2))
    a.blocks.append(Block(pygame.Rect(366, 1532, 30, 30), pygame.color.Color(118, 82, 33), level=2))
    a.blocks.append(Block(pygame.Rect(366 + 3, 1532 + 3, 30 - 6, 30 - 6), pygame.color.Color(191, 26, 26), level=2))
    a.blocks.append(Block(pygame.Rect(300, 1500, 5, 270), "invisible", solid=True))
    a.blocks.append(Block(pygame.Rect(350, 1500, 55, 270), "invisible", solid=True))

    a.blocks.append(Block(pygame.Rect(420, 1545, 60, 180), "popup", popup_text="welcome to fishington\nthis is my shop where you can sell fish and buys tools to help you\nenjoy your time here"))
    a.blocks.append(Block(pygame.Rect(0, 0, a.size[0], 200), pygame.image.load("water_texture_anim_0.png")))
    frames = [pygame.image.load(f"water_texture_anim/water_texture_anim_{i}.png") for i in range(5)]
    frames = frames + frames[::-1]
    a.blocks.append(Block(pygame.Rect(0, 0, a.size[0], 200), "anim", frames=frames))
    a.blocks.append(Block(pygame.Rect(0, 225, 600, 25), WOOD1, solid=True))
    a.blocks.append(Block(pygame.Rect(900, 225, 600, 25), WOOD1, solid=True))
    return a


def game_page(screen: pygame.Surface):
    clock = pygame.time.Clock()

    area = CURRENT_USER.current_room()
    pos = CURRENT_USER.current_pos

    world_width, world_height = area.size
    world_surf = area.surf

    interact_font = pygame.font.SysFont("arial", 80)
    text_font = pygame.font.SysFont("arial", 30)
    info_font = pygame.font.SysFont("arial", 25)

    text_box_text = ""

    player = Player(*pos)

    # s = pygame.image.load("water_texture_main.png")
    # size = 400
    # s2 = pygame.Surface((size, 100))
    # ind = 0
    # for i in range(size):
    #     if (i % 20) < 5:
    #         ind -= 1
    #     s2.blit(s, (i, 0 + ind))
    #     s2.blit(s, (i, 100 + ind))
    #     s2.blit(s, (i, 200 + ind))
    # s3 = pygame.Surface((400, 100))
    # s3.blit(s2, (0, 0))
    # pygame.image.save(pygame.transform.scale(s3, (4000, 1000)), f"water_texture_anim_0.png")
    # s = pygame.image.load("water_texture_anim_0.png")
    # for i in range(400):
    #     s2 = pygame.Surface((4000, 1000))
    #     s2.blit(s, (0 + i * 10, 0))
    #     s2.blit(s, (-4000 + i * 10, 0))
    #     pygame.image.save(s2, f"water_texture_anim/water_texture_anim_{i}.png")

    blocks = area.blocks

    running = True
    while running:
        interact_text = ""
        pressed_keys = pygame.key.get_pressed()
        for event in pygame.event.get():
            if event.type == QUIT:
                return closing_page
            if event.type == MOUSEBUTTONDOWN:
                logging.debug(f"({event.pos[0] - corner[0]}, {event.pos[1] - corner[1]})")
            if event.type == KEYDOWN:
                if event.key == K_F1:
                    DEBUG.noclip = not DEBUG.noclip
                if event.key == K_F2:
                    DEBUG.show_info = not DEBUG.show_info
                if event.key == K_ESCAPE:
                    command = pause_menu(screen)
                    if command is not None:
                        CURRENT_USER.current_pos = player.pos.get_tuple()
                        return command
                if event.key == K_SPACE:
                    for i in player.rect.collidelistall(blocks):
                        if blocks[i].popup:
                            text_box_text = blocks[i].popup_text

        if DEBUG.noclip:
            solids = []
        else:
            solids = list(filter(lambda x: x.solid, blocks))

        move = 0
        if pressed_keys[K_LEFT]:
            move -= player.speed
        if pressed_keys[K_RIGHT]:
            move += player.speed
        player.pos.move(move, 0)
        for i in player.rect.collidelistall(solids):
            if move > 0:
                player.pos.x = solids[i].rect.left - player.surface.get_width() // 2
            elif move < 0:
                player.pos.x = solids[i].rect.right + player.surface.get_width() // 2
        any_popup = False
        for i in player.rect.collidelistall(blocks):
            if blocks[i].popup:
                interact_text = "Press Space To Read"
                any_popup = True
            if blocks[i].door:
                interact_text = "DOOR"
                destination = blocks[i].destination
                CURRENT_USER.update(destination[0], destination[1](player.pos.get_tuple()))
                return game_page

        if not any_popup:
            text_box_text = ""

        move = 0
        if pressed_keys[K_UP]:
            move -= player.speed
        if pressed_keys[K_DOWN]:
            move += player.speed
        player.pos.move(0, move)
        for i in player.rect.collidelistall(solids):
            if move > 0:
                player.pos.y = solids[i].rect.top - player.surface.get_height() // 2
            elif move < 0:
                player.pos.y = solids[i].rect.bottom + player.surface.get_height() // 2

        world_surf.blit(area.background_image, (0, 0))
        lo = sorted(filter(lambda x: x.level < 1, blocks), key=lambda x: x.level)
        hi = sorted(filter(lambda x: x.level > 1, blocks), key=lambda x: x.level)
        for block in lo:
            block.draw(world_surf)
        player.draw(world_surf)
        for block in hi:
            block.draw(world_surf)

        corner = Pos(-(player.pos.x - SCREEN_WIDTH // 2), -(player.pos.y - SCREEN_HEIGHT // 2))
        if not DEBUG.noclip:
            if corner.x > 0:
                corner.x = 0
            elif corner.x < -(world_width - SCREEN_WIDTH):
                corner.x = -(world_width - SCREEN_WIDTH)
            if corner.y > 0:
                corner.y = 0
            elif corner.y < -(world_height - SCREEN_HEIGHT):
                corner.y = -(world_height - SCREEN_HEIGHT)

        screen.blit(world_surf, corner.get_tuple())

        if interact_text != "":
            rend = interact_font.render(interact_text, True, (0, 0, 0))
            screen.blit(rend, rend.get_rect(center=(SCREEN_WIDTH // 2, 620)))
        if text_box_text != "":
            rect = corner_to_rect((100, 70), (SCREEN_WIDTH - 100, 300))
            # pygame.draw.rect(screen, pygame.Color(100, 100, 100, 100), rect)
            s = pygame.Surface(rect.size, SRCALPHA)
            s.fill(pygame.Color(150, 150, 150, 230))
            screen.blit(s, (100, 70))
            pygame.draw.rect(screen, pygame.Color(80, 80, 80), rect, 7)
            for i, line in enumerate(text_box_text.split("\n")):
                rend = text_font.render(line, True, (0, 0, 0))
                screen.blit(rend, (150, 70 + 30 + i * 35))
        if DEBUG.show_info:
            area_name = info_font.render(f"area name: {area.name}", True, (0, 0, 0))
            screen.blit(area_name, (10, 10))
            player_pos = info_font.render(f"player_pos: {player.pos}", True, (0, 0, 0))
            screen.blit(player_pos, (10, 10 + 25))

        pygame.display.update()
        clock.tick(FPS)


def pause_menu(screen: pygame.Surface):
    background = copy.copy(screen)
    font = pygame.font.SysFont("forte", 70)
    options = {'Resume': None, 'Return To Menu': menu_page, 'Quit To Desktop': closing_page}
    selected = 0

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                return closing_page
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    return None
                if event.key == K_RETURN:
                    return list(options.values())[selected]
                if event.key == K_UP:
                    selected = (selected - 1) % len(options)
                if event.key == K_DOWN:
                    selected = (selected + 1) % len(options)

        screen.blit(background, (0, 0))
        s = pygame.Surface(background.get_size(), SRCALPHA)
        s.fill(pygame.Color(150, 150, 150, 230))
        screen.blit(s, (0, 0))

        for i, text in enumerate(options):
            if i == selected:
                colour = (110, 110, 110)
            else:
                colour = (225, 225, 225)
            shadow = font.render(text, True, (30, 30, 30))
            screen.blit(shadow, shadow.get_rect(center=(SCREEN_WIDTH // 2 + 6, 250 + i * 140 + 6)))

            render = font.render(text, True, colour)
            screen.blit(render, render.get_rect(center=(SCREEN_WIDTH // 2, 250 + i * 140)))

        pygame.display.update()


def options_page(screen: pygame.Surface):
    back_ground = copy.copy(screen)
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                return closing_page


def select_user_page(screen: pygame.Surface):
    global CURRENT_USER
    name_font = pygame.font.SysFont("arial", 30)
    new_user_font = pygame.font.SysFont("arial", 40)

    selected = 0
    deleting = False
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                return closing_page
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    return menu_page
                if event.key == K_UP:
                    selected = (selected - 1) % len(USERS)
                    if not isinstance(USERS[selected], User):
                        deleting = False
                if event.key == K_DOWN:
                    selected = (selected + 1) % len(USERS)
                    if not isinstance(USERS[selected], User):
                        deleting = False
                if event.key in (K_LEFT, K_RIGHT):
                    if USERS[selected] is not None:
                        deleting = not deleting
                if event.key == K_RETURN:
                    if deleting:
                        USERS[selected] = None
                        deleting = False
                    else:
                        if USERS[selected] is not None:
                            CURRENT_USER = USERS[selected]
                            return game_page
                        else:
                            new_user = User()
                            new_user.save_slot = selected + 1
                            USERS[selected] = new_user
                            CURRENT_USER = new_user
                            return game_page

        screen.fill(BACKGROUND_BLUE)

        for i, user in enumerate(USERS):
            if i == selected:
                if deleting:
                    c = 150, 150, 150
                    c2 = 100, 100, 100
                else:
                    c = 100, 100, 100
                    c2 = 150, 150, 150
            else:
                c = 150, 150, 150
                c2 = 150, 150, 150
            rect = pygame.Rect(317, 80 + i * 150, 635, 100)
            pygame.draw.rect(screen, c, rect, 4)
            if isinstance(user, User):
                rend = name_font.render(f"user {i + 1}", True, (0, 0, 0))
                screen.blit(rend, rend.get_rect(centery=rect.centery, left=rect.left + 25))
                del_rect = pygame.Rect(1000, 80 + i * 150, 140, 100)
                pygame.draw.rect(screen, c2, del_rect, 4)
                del_rend = name_font.render(f"delete file", True, (0, 0, 0))
                screen.blit(del_rend, del_rend.get_rect(center=del_rect.center))
            else:
                rend = name_font.render(f"create new user", True, (0, 0, 0))
                screen.blit(rend, rend.get_rect(centery=rect.centery, left=rect.left + 25))

        pygame.display.update()


def menu_page(screen: pygame.Surface):
    font = pygame.font.SysFont("forte", 70)
    options = {"play": select_user_page, "options": options_page, "quit": closing_page}
    selected = 0

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                return closing_page
            if event.type == KEYDOWN:
                if event.key == K_UP:
                    selected = (selected - 1) % len(options)
                if event.key == K_DOWN:
                    selected = (selected + 1) % len(options)
                if event.key == K_RETURN:
                    return list(options.values())[selected]
            if event.type == MOUSEMOTION:
                mag = [math.sqrt(pow((250 + i * 140) - event.pos[1], 2) + pow(SCREEN_WIDTH // 2 - event.pos[0], 2)) for
                       i, text in enumerate(options)]
                selected = mag.index(min(mag))
            if event.type == MOUSEBUTTONDOWN:
                return list(options.values())[selected]

        screen.fill(BACKGROUND_BLUE)

        for i, text in enumerate(options):
            if i == selected:
                colour = (120, 120, 120)
            else:
                colour = (225, 225, 225)
            shadow = font.render(text, True, (30, 30, 30))
            screen.blit(shadow, shadow.get_rect(center=(SCREEN_WIDTH // 2 + 6, 250 + i * 140 + 6)))

            render = font.render(text, True, colour)
            screen.blit(render, render.get_rect(center=(SCREEN_WIDTH // 2, 250 + i * 140)))

        pygame.display.update()


def closing_page(screen: pygame.Surface):
    screen.fill(BACKGROUND_GREY)

    start_time = time.perf_counter()
    font = pygame.font.SysFont("forte", 60)

    text = font.render("Closing...", True, (0, 0, 0))
    screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
    pygame.display.update()

    running = True
    while running:
        pygame.event.get()

        if time.perf_counter() - start_time > 0.8:
            running = False

    # with open("user1.pickle", 'wb') as f:
    #     pickle.dump(CURRENT_USER, f, pickle.HIGHEST_PROTOCOL)
    # logging.info("data saved")
    for user in filter(lambda x: x is not None, USERS):
        save_user(user)

    pygame.quit()
    logging.info("window closed")


USERS = load_users()
CURRENT_USER: typing.Union[User, None] = None

POLES = {"wood": Material("wood", 0), "steal": Material("steal", 0.4)}
STRINGS = {"weak string": Material("Weak String", -0.5)}
HOOKS = {"basic hook": Material("Basic Hook", 0)}

FISH = {}

# constants
BACKGROUND_GREY = pygame.Color(100, 100, 100)
BACKGROUND_BLUE = pygame.Color(148, 247, 255)
WOOD1 = pygame.Color(105, 68, 16)

SCREEN_WIDTH = 1270
SCREEN_HEIGHT = 720

FPS = 60

AREA = collections.namedtuple("Area", ['name', 'size', 'surf', 'background_image', 'blocks'])
DEBUG = collections.namedtuple("DebugRules", ['noclip', 'show_info'])
DEBUG.noclip = False
DEBUG.show_info = True


def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), SRCALPHA)
    pygame.display.set_caption("Fish")

    page = menu_page

    try:
        running = True
        while running:
            p = page(screen)
            if p is not None:
                page = p
            else:
                break
    except Exception:
        print("an exception has occurred")
        closing_page(screen)
        raise sys.exc_info()[1]


if __name__ == '__main__':
    main()
