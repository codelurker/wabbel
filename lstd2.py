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
    g.font_size = 16, 24
    g.gravity = 0.01
    g.nextwavestep = 1
    g.level = [(0, 0.7), (0.4, 0.5), (0.5, 0.9), (0.95, 0.8), (0.7, 0.2), (0, 0.3)]
    g.level_scaled = list(_scaled(g.level, g.w, g.h))
    g.clock = None
    g.font = None
    g.smallfont = None
    g.max_drag_dist = 200

    g.reset()

  def reset(g):
    g.logged = deque(maxlen=30)
    g.nextwave = 200
    g.nextwavemax = g.nextwave
    g.hp = 10
    g.hpregeneration = 0.01
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
    self.original_speed = self.speed
    self.danger = 0
    self.armor = level * 0.1
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
          die()
      else:
        self.checkpoint += 1
        self.x, self.y = g.level_scaled[self.checkpoint]

    if self.square:
      pygame.draw.rect(g.screen, self.color, Rect(int(self.x-4), int(self.y-4), 8, 8), 3)
    else:
      pygame.draw.circle(g.screen, self.color, (int(self.x), int(self.y)), 5, 2)

  def damage(self, damage, tower):
    freeze = (tower.blue / 2048.0)
    damage -= self.armor * (1 - tower.pierce)
    self.hp -= damage
    self.color = _scale_color(self.color, self.hp / self.maxhp)
    self.speed -= freeze * self.original_speed
    self.speed = min(self.original_speed, max(self.original_speed / 2.0, self.speed))
    if self.hp <= 0 and -self.hp <= damage:
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
    self.size = 1
    self.x = g.w
    self.y = g.h * 0.5
    self.vx = random.randint(-100, -40)
    self.vy = random.randint(-100, 100)
    self.last_shot = 0
    self.range = 100
    self.phase = 0
    self.stats = []
    self.update_stats()

  def update_stats(self):
    self.yellow = max(0, (self.red + self.green) / 2 - self.blue - abs(self.red - self.green))
    self.cyan = max(0, (self.blue + self.green) / 2 - self.red - abs(self.blue - self.green))
    self.magenta = max(0, (self.blue + self.red) / 2 - self.green - abs(self.blue - self.red))

    size_damage = 1 + self.size / 10.0
    red_damage = self.red / 16.0
    self.damage = size_damage + red_damage
    self.color = (self.red, self.green, self.blue)
    self.pierce = 0
    self.radius = int(10 + sqrt(self.size * pi))
    self.range = int(self.radius + 30 + sqrt(self.green * 10) * 2)
    if self.yellow == 0 and self.magenta == 0 and self.cyan == 0:
      self.shot_delay = 1 / 6.5
    else:
      self.shot_delay = 0.4 - (0.3 * self.yellow / 255.0)
    self.inertia = 4.0 / (4 + self.size)
    if self.color == (0, 0, 0):
      self.pierce = 1

    self.stats = []
    self.stats.append("damage: %d + %d" % (size_damage, red_damage))
    self.stats.append("range: %d" % self.range)
    self.stats.append("freeze: %.2f" % (self.blue / 2048.0))
    self.stats.append("")
    self.stats.append("attack speed: %.2f" % (1 / self.shot_delay))
    self.stats.append("armor decay: %.2f" % (self.cyan / 2048.0))
    if self.color == (0, 0, 0):
      self.stats.append("black hole bonus: armor piercing")
    if self.yellow == 0 and self.magenta == 0 and self.cyan == 0:
      self.stats.append("purity bonus: +4 aspd")
#    if self.yellow > 0:
#      self.stats.append("yellow: +%.2f aspd" % (1 / self.shot_delay - 2.5))
    self.stats.append("")
    self.stats.append("mass: %d" % self.size)
    self.stats.append("radius: %d" % self.radius)

  def act(self):
    if g.drag == self:
      mousex, mousey = pygame.mouse.get_pos()
      mousex = max(0, min(g.w, mousex))
      mousey = max(0, min(g.h, mousey))
#      g.log("%d, %d" % (mousex, mousey))
      self.vx += (mousex - self.x) / 20 * self.inertia
      self.vy += (mousey - self.y) / 20 * self.inertia
    else:
      if self.y + self.radius < g.h:
        self.vy += g.gravity

    self.y += self.vy
    self.x += self.vx
    if self.x - self.radius < 0 or self.x + self.radius > g.w:
      self.vx *= -1
    if self.y - self.radius < 0 or self.y + self.radius > g.h:
      self.vy *= -1

    if self.size < 50:
      slowdown = 0.95 + self.size / 1000.0
      self.vx *= slowdown
      self.vy *= slowdown

    if self.last_shot + self.shot_delay < time.time():
      self.shoot()

  def draw(self):
    whalf = (1 + 0.2 *-sin(self.phase+0.2)) * self.radius
    hhalf = (1 + 0.2 * sin(self.phase)) * self.radius
    x = int(self.x - whalf)
    y = int(self.y - hhalf)
#    pygame.draw.circle(g.screen, (0, 255, 255), (int(self.x), int(self.y)), self.radius, 0)
    self.phase = (self.phase + pi/12) % (2*pi)
#    rect = Rect(x-1, y-1, whalf*2+2, hhalf*2+2)
#    pygame.draw.ellipse(g.screen, (0, 0, 0), rect, 0)
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
        if mob.damage(self.damage, self):
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
  if length > 0:
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
    g.log("b: Create a new bubble")
    g.log("1: Paint the bubble in red")
    g.log("2: Paint the bubble in green")
    g.log("3: Paint the bubble in blue")
    g.log("Tab: Select next bubble")
    g.log("n: Send the next wave of enemies")
    g.log("Drag&Drop, Arrow Keys or hjkl: Move the active bubble")
    g.log("q or ESC: quit")
  elif key == K_F10:
    g.reset()
  elif key == ord("c"):
    g.logged.clear()
  elif key == ord("n"):
    call_next_wave()
  elif key == ord("b"):
    g.towers.append(Tower())
  elif key == ord(" "):
    g.pause ^= True
  elif key in (K_1, K_2, K_3):
    if g.active:
      c = {K_1: "red", K_2: "green", K_3: "blue"}[key]
      if pygame.key.get_mods() & KMOD_SHIFT:
        if g.active.__dict__[c] > 0:
          g.active.__dict__[c] = max(0, g.active.__dict__[c] - 16)
          g.hp = min(g.maxhp, g.hp + 0.5)
      else:
        if g.hp > 2 and g.active.__dict__[c] < 255:
          g.hp -= 1
          g.active.__dict__[c] = min(255, g.active.__dict__[c] + 16)
      g.active.update_stats()
  elif key == K_TAB:
    if g.active:
      g.active = g.towers[(g.towers.index(g.active) + 1) % len(g.towers)]
    elif g.towers:
      g.active = g.towers[0]


def key_pressed_handler(pressed):
  if (pressed[ord("j")] or pressed[K_DOWN]) and g.active:
    g.active.vy += 4.0 * g.active.inertia
  if (pressed[ord("k")] or pressed[K_UP]) and g.active:
    g.active.vy -= 4.0 * g.active.inertia
  if (pressed[ord("h")] or pressed[K_LEFT]) and g.active:
    g.active.vx -= 4.0 * g.active.inertia
  if (pressed[ord("l")] or pressed[K_RIGHT]) and g.active:
    g.active.vx += 4.0 * g.active.inertia


def click(action, pos, button):
  if button == 1:
    if action == MOUSEBUTTONDOWN:
      for tower in reversed(g.towers):
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


def die():
  towers = [t for t in g.towers if t.size >= 20]
  if towers:
    g.towers.remove(towers[0])
    life = min(10, int(towers[0].size / 20))
    g.log("Your strongest bubble sacrificed itself to give you %d life!" % life)
    g.hp += life
  else:
    g.log("You have lost the game! Press F10 to reset.")
    g.log("Final Score: %d" % g.score)


def draw():
  if g.hp <= 0:
    return
  if g.pause:
    return

  g.hp = min(g.maxhp, g.hp + g.hpregeneration)
  if g.towers or g.levelnumber:
    g.nextwave -= g.nextwavestep
    if g.nextwave <= 0:
      call_next_wave()

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

  if g.drag:
    mouse = pygame.mouse.get_pos()
    dx, dy = mouse[0] - g.drag.x, mouse[1] - g.drag.y
    dist = sqrt(dx*dx + dy*dy)
    if dist < g.max_drag_dist:
      g.drag_to = mouse
    else:
      angle = atan2(dy, dx)
      g.drag_to = g.drag.x + g.max_drag_dist * cos(angle), \
                  g.drag.y + g.max_drag_dist * sin(angle)

  g.towers.sort(key=lambda tower: -tower.size)
  for i, tower in enumerate(list(g.towers)):
    tower.act()
    tower.draw()
    for other in g.towers[i+1:]:
      angle = atan2(tower.y - other.y, tower.x - other.x)
      distance = sqrt((tower.y - other.y)**2 + (tower.x - other.x)**2)
      if distance > 5:
        attraction = (tower.size + other.size) / 10 / distance
        tower.vx -= cos(angle) * attraction * tower.inertia
        tower.vy -= sin(angle) * attraction * tower.inertia
        other.vx += cos(angle) * attraction * other.inertia
        other.vy += sin(angle) * attraction * other.inertia

  if g.drag:
    pygame.draw.line(g.screen, g.drag.color, (int(g.drag.x), int(g.drag.y)),
        g.drag_to, 3)

  _draw_bar(g.w-120, 15, int(100*g.nextwave/g.nextwavemax), 2, (150, 150, 0))
  if g.hp > 0:
    _draw_bar(g.w-120, 10, 100, 3, (100, 100, 100))
    _draw_bar(g.w-120, 10, int(100*g.hp/g.maxhp), 5, (255, 0, 0))

  if g.active:
    for y in [30, 35, 40, 50, 55, 60]:
      _draw_bar(g.w-100, y, 80, 2, (100, 100, 100))

    _draw_bar(g.w-100, 30, int(80*g.active.red/255), 3, (200, 0, 0))
    _draw_bar(g.w-100, 35, int(80*g.active.green/255), 3, (0, 200, 0))
    _draw_bar(g.w-100, 40, int(80*g.active.blue/255), 3, (0, 0, 200))

    _draw_bar(g.w-100, 50, int(80*g.active.yellow/255), 3, (200, 200, 0))
    _draw_bar(g.w-100, 55, int(80*g.active.magenta/255), 3, (200, 0, 200))
    _draw_bar(g.w-100, 60, int(80*g.active.cyan/255), 3, (0, 200, 200))

    x, y = g.w - 20, 80
    for line in g.active.stats:
      text = g.smallfont.render(line, 1, (255, 255, 255))
      g.screen.blit(text, (x - text.get_rect().width, y))
      y += text.get_rect().height + 2

  x, y = 0, 0
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
  g.smallfont = pygame.font.Font(g.font_name, g.font_size[0])
  g.font = pygame.font.Font(g.font_name, g.font_size[1])

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
