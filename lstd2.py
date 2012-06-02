#!/usr/bin/python -O
# Copyright (C) 2011, 2012  Roman Zimbelmann <hut@lavabit.com>
# This software is distributed under the terms of the GNU GPL version 3.

import pygame
import random
import sys
import time
from collections import deque
from math import *
from pygame.locals import *

class Globals(object):
  def __init__(g):
    # constants:
    g.maxfps = 30
    g.w, g.h = 800, 600
    g.profile = '--profile' in sys.argv
    g.fullscreen = '--fullscreen' in sys.argv
    g.font_name = None
    g.font_size = 24
    g.gravity = 0.01
    g.nextwavestep = 1
    g.level = [(0, 0.7), (0.4, 0.5), (0.5, 0.9), (0.95, 0.8), (0.7, 0.2), (0, 0.3)]
    g.level_scaled = list(_scaled(g.level, g.w, g.h))
    g.clock = None
    g.font = None

    g.reset()

  def reset(g):
    g.logged = deque(maxlen=30)
    g.nextwave = 200
    g.nextwavemax = g.nextwave
    g.hp = 10
    g.maxhp = g.hp
    g.levelnumber = 0
    g.score = 0
    g.pause = False
    g.drag = None
    g.active = None
    g.mobs = []
    g.waves = list()
    g.towers = list()

  def log(g, obj):
    g.logged.append(str(obj))


class Monster(object):
  def __init__(self, level):
    self.level = level
    self.hp = 10 * level
    self.checkpoint = 0
    self.speed = 1 + level * 0.1 + random.randint(-10,10) * 0.04
    self.danger = 0
    self.armor = 0
    self.original_color = (random.randint(1,3) * 63, random.randint(1,3) * 63, random.randint(1,3) * 63)
    self.color = self.original_color
    self.x, self.y = g.level_scaled[self.checkpoint]
    if level % 3 == 0:
      self.square = True
      self.armor = (self.armor + 1) * 2
      self.hp *= 0.5
    else:
      self.square = False
    self.maxhp = float(self.hp)

  def draw(self):
    point1 = g.level_scaled[self.checkpoint]
    point2 = g.level_scaled[self.checkpoint + 1]
    angle = atan2(point2[1] - point1[1], point2[0] - point1[0])
    self.x += cos(angle) * self.speed
    self.y += sin(angle) * self.speed
    self.danger += self.speed
    if abs(point2[0] - self.x) < self.speed and \
        abs(point2[1] - self.y) < self.speed * 2:
      if self.checkpoint >= len(g.level) - 2:
        self.hp = 0
        g.hp -= 1
        if g.hp <= 0:
          g.log("You have lost the game! Press F10 to reset. Final Score: %d" % g.score)
      else:
        self.checkpoint += 1

    if self.square:
      pygame.draw.rect(g.screen, self.color, Rect(int(self.x-4), int(self.y-4), 8, 8), 3)
    else:
      pygame.draw.circle(g.screen, self.color, (int(self.x), int(self.y)), 5, 2)

  def damage(self, damage):
    damage -= self.armor
    self.hp -= damage
    self.color = _scale_color(self.color, self.hp / self.maxhp)
    if self.hp < 0 and -self.hp <= damage:
      return True
    return False


class Wave(object):
  def __init__(self, level):
    self.level = level
    self.delay = 0.3
    self.last_send = 0
    self.monsters_left = 10

  def tick(self):
    if self.last_send + self.delay < time.time():
      mob = Monster(self.level)
      g.mobs.append(mob)
      self.monsters_left -= 1
      self.last_send = time.time()


class Tower(object):
  def __init__(self):
    self.red = 64
    self.blue = 64
    self.green = 64
    color = random.randint(1,3)
    if color == 1:
      self.red = 0
    elif color == 2:
      self.green = 0
    else:
      self.blue = 0
    self.size = 0
    self.x = g.w
    self.y = g.h * 0.5
    self.vx = random.randint(-100, -40)
    self.vy = random.randint(-100, 100)
    self.last_shot = 0
    self.shot_delay = 0.4
    self.range = 100
    self.phase = 0
    self.update_stats()

  def update_stats(self):
    self.damage = self.size / 10 + self.red / 16
    self.color = (self.red, self.green, self.blue)
    self.range = int(50 + self.green)
    self.radius = int(10 + sqrt(self.size * 2))

  def act(self):
    if g.drag == self:
      mousex, mousey = pygame.mouse.get_pos()
      mousex = max(0, min(g.w, mousex))
      mousey = max(0, min(g.h, mousey))
#      g.log("%d, %d" % (mousex, mousey))
      self.vx += (mousex - self.x) / 20
      self.vy += (mousey - self.y) / 20
    else:
      if self.y + self.radius < g.h:
        self.vy += g.gravity

    self.y += self.vy
    self.x += self.vx
    if self.x - self.radius < 0 or self.x + self.radius > g.w:
      self.vx *= -1
    if self.y - self.radius < 0 or self.y + self.radius > g.h:
      self.vy *= -1
    self.vx *= 0.95
    self.vy *= 0.95

    if self.last_shot + self.shot_delay < time.time():
      self.shoot()

  def draw(self):
    whalf = (1 + 0.2 *-sin(self.phase+0.2)) * self.radius
    hhalf = (1 + 0.2 * sin(self.phase)) * self.radius
    x = int(self.x - whalf)
    y = int(self.y - hhalf)
#    pygame.draw.circle(g.screen, (0, 255, 255), (int(self.x), int(self.y)), self.radius, 0)
    self.phase = (self.phase + pi/12) % (2*pi)
    rect = Rect(x-1, y-1, whalf*2+2, hhalf*2+2)
    pygame.draw.ellipse(g.screen, (0, 0, 0), rect, 0)
    rect = Rect(x, y, whalf*2, hhalf*2)
    pygame.draw.ellipse(g.screen, self.color, rect, 0)

  def _get_monsters_in_range(self):
    for mob in g.mobs:
      if mob.hp > 0 and \
          abs(mob.x - self.x) < self.range and \
          abs(mob.y - self.y) < self.range and \
          sqrt((mob.x - self.x) ** 2 + (mob.y - self.y) ** 2) < self.range:
        yield mob

  def shoot(self):
    mobs = list(self._get_monsters_in_range())
    if not mobs:
      return
    self.last_shot = time.time()
    target = max(mobs, key=lambda mob: mob.danger)
    pygame.draw.circle(g.screen, self.color, (int(target.x), int(target.y)), self.radius, 0)
    pygame.draw.line(g.screen, self.color, (int(self.x), int(self.y)), (int(target.x), int(target.y)), self.radius * 2)

    for mob in g.mobs:
      if mob.hp > 0 and \
          abs(mob.x - target.x) < self.radius and \
          abs(mob.y - target.y) < self.radius and \
          sqrt((mob.x - target.x) ** 2 + (mob.y - target.y) ** 2) < self.radius:
        if mob.damage(self.damage):
          self.size += 1
          self.update_stats()
          g.score += mob.level


# Lib {{{
def _cached_method(fnc):
  cache = {}
  def result(*args):
    try:
      return cache[args]
    except:
      value = fnc(*args)
      cache[args] = value
      return value
  result._cache = cache
  return result


def _scaled(dots, width, height):
  for dot in dots:
    yield (int(dot[0] * width), int(dot[1] * height))

def _scale_color(color, factor):
  return (max(0, min(255, int(color[0] * factor))),
      max(0, min(255, int(color[1] * factor))),
      max(0, min(255, int(color[2] * factor))))

def _draw_bar(x, y, length, width, color):
  pygame.draw.line(g.screen, color, (x, y), (x + length, y), width)
#}}}


def call_next_wave():
  g.nextwave = g.nextwavemax
  g.levelnumber += 1
  g.log("Level %d" % g.levelnumber)
  g.waves.append(Wave(g.levelnumber))


def keyhandler(key):
  if key == K_F1:
    g.log("Space: Pause game")
    g.log("n: Create a new bubble")
    g.log("1: Paint the bubble in red")
    g.log("2: Paint the bubble in green")
    g.log("3: Paint the bubble in blue")
    g.log("Tab: Select next bubble")
    g.log("f: Send the next wave of enemies")
    g.log("Drag&Drop, Arrow Keys or hjkl: Move the active bubble")
    g.log("q or ESC: quit")
  elif key == K_F10:
    g.reset()
  elif key == ord("c"):
    g.logged.clear()
  elif key == ord("f"):
    call_next_wave()
  elif key == ord("n"):
    g.towers.append(Tower())
  elif key == ord(" "):
    g.pause ^= True
  elif key == K_1:
    if g.active and g.hp > 2:
      g.hp -= 1
      g.active.red = min(255, g.active.red + 16)
      g.active.update_stats()
  elif key == K_2:
    if g.active and g.hp > 2:
      g.hp -= 1
      g.active.green = min(255, g.active.green + 16)
      g.active.update_stats()
  elif key == K_3:
    if g.active and g.hp > 2:
      g.hp -= 1
      g.active.blue = min(255, g.active.blue + 16)
      g.active.update_stats()
  elif key == K_TAB:
    if g.active:
      g.active = g.towers[(g.towers.index(g.active) + 1) % len(g.towers)]
    elif g.towers:
      g.active = g.towers[0]


def key_pressed_handler(pressed):
  if pressed[ord("j")] and g.active:
    g.active.vy += 2
  if pressed[ord("k")]  and g.active:
    g.active.vy -= 2
  if pressed[ord("h")] and g.active:
    g.active.vx -= 2
  if pressed[ord("l")] and g.active:
    g.active.vx += 2


def click(action, pos, button):
  if button == 1:
    if action == MOUSEBUTTONDOWN:
      for tower in g.towers:
        dist = sqrt((tower.x - pos[0])**2 + (tower.y - pos[1])**2)
        if dist <= tower.radius:
          g.drag = tower
          g.active = tower
          break
      else:
        g.active = None
    elif action == MOUSEBUTTONUP:
      g.drag = None
  elif button == 3:
    g.active = None


def draw():
  if g.hp <= 0:
    return
  if g.pause:
    return

  g.hp = min(g.maxhp, g.hp + 0.01)
  if g.towers or g.levelnumber:
    g.nextwave -= g.nextwavestep
    if g.nextwave <= 0:
      call_next_wave()

  x, y = 0, 0
  g.screen.fill((0, 0, 0))

  if g.active:
    pygame.draw.circle(g.screen, (32, 32, 32), (int(g.active.x),
      int(g.active.y)), g.active.range, 0)

  pygame.draw.lines(g.screen, (100, 0, 0), False, g.level_scaled, 10)
  for dot in g.level_scaled:
    pygame.draw.circle(g.screen, (100, 0, 0), dot, 4, 0)

  for wave in list(g.waves):
    if wave.monsters_left > 0:
      wave.tick()
    else:
      g.waves.remove(wave)

  for mob in list(g.mobs):
    if mob.hp <= 0:
      g.mobs.remove(mob)
    else:
      mob.draw()

  for tower in list(g.towers):
    tower.act()
    tower.draw()

  _draw_bar(g.w-120, 15, int(100*g.nextwave/g.nextwavemax), 2, (150, 150, 0))
  if g.hp > 0:
    _draw_bar(g.w-120, 10, 100, 3, (100, 100, 100))
    _draw_bar(g.w-120, 10, int(100*g.hp/g.maxhp), 5, (255, 0, 0))

  if g.active:
    _draw_bar(g.w-100, 30, 80, 2, (100, 100, 100))
    _draw_bar(g.w-100, 35, 80, 2, (100, 100, 100))
    _draw_bar(g.w-100, 40, 80, 2, (100, 100, 100))
    _draw_bar(g.w-100, 30, int(80*g.active.red/255), 3, (200, 0, 0))
    _draw_bar(g.w-100, 35, int(80*g.active.green/255), 3, (0, 200, 0))
    _draw_bar(g.w-100, 40, int(80*g.active.blue/255), 3, (0, 0, 200))

  for line in g.logged:
    if not line:
      continue
    text = g.font.render(line, 1, (255, 255, 255))
    g.screen.blit(text, (x, y))
    y += text.get_rect().height + 2

  line = "%d %d" % (g.clock.get_fps(), g.score)
  text = g.font.render(line, 1, (150, 150, 150))
  g.screen.blit(text, (10, g.h-10-text.get_rect().height))

  pygame.display.flip()


def run():
  pygame.init()
  pygame.font.init()
  pygame.key.set_repeat(180, 80)
  flags = pygame.SRCALPHA | pygame.DOUBLEBUF # | pygame.RESIZABLE
  if g.fullscreen:
    pygame.mouse.set_visible(False)
    flags |= pygame.FULLSCREEN
  g.screen = pygame.display.set_mode((g.w, g.h), flags, 32)
  g.font = pygame.font.Font(g.font_name, g.font_size)

  g.clock = pygame.time.Clock()
  g.w, g.h = g.screen.get_size()
  g.log("Welcome! Press F1 to display help.")

  next_log_refresh = 0

  while True:
    g.clock.tick(g.maxfps)
    if next_log_refresh <= time.time():
      next_log_refresh = time.time() + 1
      g.log("")

    for event in pygame.event.get():
      if event.type == QUIT:
        return
      elif event.type == KEYDOWN:
        if event.key == K_ESCAPE or event.key == K_q:
          return
        elif event.key == K_F11:
          pygame.mouse.set_visible(not pygame.mouse.set_visible(False))
          pygame.display.toggle_fullscreen()
        else:
          keyhandler(event.key)
      elif event.type in (MOUSEBUTTONDOWN, MOUSEBUTTONUP):
        click(event.type, event.pos, event.button)
    key_pressed_handler(pygame.key.get_pressed())
    draw()


if __name__ == '__main__':
  global g
  g = Globals()
  if g.profile:
    import cProfile
    import pstats
    exit_code = cProfile.run('sys.modules[__name__].run()', '/tmp/profile')
    p = pstats.Stats('/tmp/profile')
    p.strip_dirs().sort_stats('cumulative').print_callees()
  else:
    run()
