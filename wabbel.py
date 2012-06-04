#!/usr/bin/python2 -OOBts
# Copyright (C) 2011, 2012  Roman Zimbelmann <hut@lavabit.com>
# This software is distributed under the terms of the GNU GPL version 3.

import os.path
import pygame
import random
import sys
import time
from collections import deque
from math import sin, cos, atan2, pi, sqrt
from pygame.locals import *

# -- INDEX --
# class Globals
# def run()
# def draw()
# class Actor
# class Monster(Actor)
# class Tower(Actor)
# class Wave
# def keypress(key)
# def keyhold(pressed)
# def click(action, pos, button)


class Globals(object):
  def __init__(g):
    """
    Variables that are initialized here never changed, or only changed once
    inside the run() function.
    """
    g.maxfps = 30
    g.w, g.h = 800, 600
    g.profile = '--profile' in sys.argv
    g.fullscreen = '--fullscreen' in sys.argv
    g.debug = '--debug' in sys.argv
    g.font_name = None
    g.font_size = 16, 24
    g.nextwavestep = 1
    g.waves_per_level = 10
    g.range_color = (32, 32, 32)
    g.level_layouts = [
        [(0, 0.7), (0.4, 0.5), (0.5, 0.9), (0.95, 0.8), (0.7, 0.2), (0, 0.3)],
    ]
    g.hpregeneration = 0
    g.hp_per_monster = 0.3
    g.hp_cost = 1
    g.drag_to = None
    g.hp_damage = 0 if g.debug else 0.6
    g.monster_min_speed = 0.3
    g.monster_min_armor = 0.5
    g.min_hp_for_buying = 2
    g.color_step = 10
    g.clock = None
    g.font = None
    g.smallfont = None
    g.max_drag_dist = 100
    g.max_towers = 20
    g.reset_game()

  def reset_game(g):
    """
    Variables that are initialized here are changed continuously in the course
    of the game and are reset to their defaults when a new game is started.
    """
    g.checkpoints = list(_scaled(random.choice(g.level_layouts), g.w, g.h))
    g.logged = deque(maxlen=30)
    g.nextwave = 200
    g.nextwavemax = g.nextwave
    g.hp = 10
    g.maxhp = g.hp
    g.level = 0
    g.score = 0
    g.pause = False
    g.drag = None
    g.active = None
    g.mobs = []
    g.waves = list()
    g.towers = list()
    g.change_level()

  def change_level(g):
    """
    Variables that are initialized here are updated every time the level is
    changed, which occurs every g.waves_per_level waves.
    """
    g.level_color = _random_color(0xff)
    if g.level == 0:
      g.gravity = (0, 0.01)
    else:
      grav = min(100, g.level * 3)
      g.gravity = (0.001 * random.randint(-grav,grav),
          0.001 * random.randint(-grav,grav))

  def log(g, obj):
    g.logged.append(str(obj))


def run():
  """
  Start the game, initialize pygame and run the input/draw loop
  """
  pygame.init()
  pygame.font.init()
  pygame.key.set_repeat(180, 80)
  flags = pygame.DOUBLEBUF
  if g.fullscreen:
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
          pygame.display.toggle_fullscreen()
        else:
          keypress(event.key)
      elif event.type in (MOUSEBUTTONDOWN, MOUSEBUTTONUP):
        click(event.type, event.pos, event.button)
    keyhold(pygame.key.get_pressed())
    draw()


def draw():
  """
  Draw the level, the UI and the actors.
  """
  if g.hp > 0 and not g.pause:
    g.hp = min(g.maxhp, g.hp + g.hpregeneration)
    if g.towers or g.level:
      if g.level and g.level % g.waves_per_level == 0:
        if g.mobs:
          g.nextwave = g.nextwavemax
        else:
          g.change_level()
          g.nextwave = 0

      g.nextwave -= g.nextwavestep
      if g.nextwave <= 0:
        g.nextwave = g.nextwavemax
        g.level += 1
        g.log("Wave %d" % g.level)
        g.waves.append(Wave(g.level))

    for wave in list(g.waves):
      if wave.monsters_left > 0:
        wave.tick()
      else:
        g.waves.remove(wave)

    for mob in list(g.mobs):
      if mob.hp <= 0:
        g.mobs.remove(mob)
      else:
        mob.walk()

  if g.hp > 0 and not g.pause or g.debug:
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
    for i, tower in enumerate(tuple(g.towers)):
      tower.walk()
      for other in g.towers[i+1:]:
        angle = atan2(tower.y - other.y, tower.x - other.x)
        distance = tower.distance(other.x, other.y)
        if distance > 10:
          g1 = tower.size + 1
          g2 = other.size + 1
          attraction = (g1 * g2) / distance**2
          tower.vx -= cos(angle) * attraction / g1
          tower.vy -= sin(angle) * attraction / g1
          other.vx += cos(angle) * attraction / g2
          other.vy += sin(angle) * attraction / g2

  g.screen.fill((0, 0, 0))

  if g.active:
    pygame.draw.circle(g.screen, g.range_color, g.active.pos, g.active.range, 0)

  dark = [int(clr*0.5) for clr in g.level_color]
  pygame.draw.lines(g.screen, dark, False, g.checkpoints, 24)
  for dot in g.checkpoints:
    pygame.draw.circle(g.screen, dark, (dot[0], dot[1]+1), 12, 0)
  pygame.draw.lines(g.screen, g.level_color, False, g.checkpoints, 20)
  for dot in g.checkpoints:
    pygame.draw.circle(g.screen, g.level_color, (dot[0], dot[1]+1), 10, 0)

  for mob in g.mobs:
    mob.draw()

  for tower in tuple(g.towers):
    tower.draw()

  if g.drag and g.drag_to:
    pygame.draw.line(g.screen, g.drag.color, g.drag.pos, g.drag_to, 3)

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


class Actor(object):
  @property
  def pos(self):
    return int(self.x), int(self.y)

  def distance(self, x, y):
    return sqrt((x-self.x) ** 2 + (y-self.y) ** 2)


class Monster(Actor):
  def __init__(self, level):
    self.level = level
    self.hp = 6 * level
    self.checkpoint = 0
    self.speed = 1 + level * 0.1 + random.randint(-10,10) * 0.04
    self.danger = 0
    self.armor = max(0, (level - 5)/2)
    self.color = (random.randint(1,3) * 63, random.randint(1,3) * 63,
        random.randint(1,3) * 63)
    self.x, self.y = g.checkpoints[self.checkpoint]
    if level % 3 == 0:
      self.square = True
      self.armor = (self.armor + 1) * 2
      self.hp *= 0.5
      self.speed *= 0.8
    else:
      self.square = False

    self.maxhp = float(self.hp)
    self.original_speed = self.speed
    self.original_color = self.color
    self.original_armor = self.armor

  def walk(self):
    point1 = g.checkpoints[self.checkpoint]
    point2 = g.checkpoints[self.checkpoint + 1]
    angle = atan2(point2[1] - point1[1], point2[0] - point1[0])
    self.x += cos(angle) * self.speed
    self.y += sin(angle) * self.speed
    self.danger += self.speed
    if abs(point2[0] - self.x) < self.speed and \
        abs(point2[1] - self.y) < self.speed * 2:
      if self.checkpoint >= len(g.checkpoints) - 2:
        self.hp = 0
        g.hp -= g.hp_damage
        if g.hp <= 0:
          g.log("You have lost the game! Press F8 to restart.")
          g.log("Final Score: %d" % g.score)
      else:
        self.checkpoint += 1
        self.x, self.y = g.checkpoints[self.checkpoint]

  def draw(self):
    if self.square:
      pygame.draw.rect(g.screen, self.color, Rect(int(self.x-4), int(self.y-4), 8, 8), 3)
    else:
      pygame.draw.circle(g.screen, self.color, self.pos, 5, 2)

  def damage(self, damage, tower):
    damage -= self.armor * (1 - tower.armor_pierce)
    self.hp -= damage
    self.color = _scale_color(self.color, self.hp / self.maxhp)
    self.speed -= tower.freeze * self.original_speed
    self.speed = min(self.original_speed, max(self.original_speed *
      g.monster_min_speed, self.speed))
    if tower.armor_decay:
      self.armor -= tower.armor_decay
      self.armor = min(self.original_armor, max(self.original_armor *
        g.monster_min_armor, self.armor))
    if self.hp <= 0 and -self.hp <= damage:
      return True
    return False


class Tower(Actor):
  starting_towers = [(64, 0, 0), (0, 64, 0), (0, 0, 64)]
  def __init__(self):
    if g.towers:
      self.color = random.choice(self.starting_towers)
    else:
      self.color = self.starting_towers[0]
    self.red, self.green, self.blue = self.color
    self.size = 0
    self.x = g.w
    self.y = g.h * 0.5
    self.vx = random.randint(-100, -40)
    self.vy = random.randint(-100, 100)
    self.last_shot = 0
    self.range = 100
    self.phase = 0
    self.bonus_damage = 0
    self.stats = []
    self.target_point = None
    self.update_stats()

  def update_stats(self):
    r, g, b = self.red, self.green, self.blue
    self.yellow = max(0, (r + g) / 2 - b - abs(r - g))
    self.cyan = max(0, (b + g) / 2 - r - abs(b - g))
    self.magenta = max(0, (b + r) / 2 - g - abs(b - r))

    size_damage = 1 + self.size / 10.0
    red_damage = r / 16.0
    self.damage = size_damage + red_damage

    self.color = (r, g, b)
    self.armor_decay = sqrt(self.cyan / 2048.0)
    self.freeze = b / 2048.0
    self.armor_pierce = 0
    self.support = 0
    self.inflate = 0
#    self.inflate = (self.magenta / 255.0) ** 4 * 3
    self.radius = int(sqrt((50 + self.size * 1.5) * (1+self.inflate) * pi))
    self.range = int(self.radius + 30 + sqrt(g * 10) * 2)

    self.shot_delay = max(0.1, 0.4 - (0.3 * self.yellow / 255.0) + (self.size / 10000.0))
    if self.yellow == 0 and self.magenta == 0 and self.cyan == 0:
      self.shot_delay = 1 / (1 / (self.shot_delay) + 2)
    self.inertia = 4.0 / (4 + self.size / 100.0)
    if self.color == (0, 0, 0):
      self.armor_pierce = 1

    self.dps = 1 / self.shot_delay * (self.damage + self.bonus_damage)

    self.stats = []
    self.stats.append("DPS: %.2f" % self.dps)
    self.stats.append("damage: %d + %d + %d" % (size_damage, red_damage, self.bonus_damage))
    self.stats.append("range: %d" % self.range)
    self.stats.append("attacks per second: %.2f" % (1 / self.shot_delay))
    self.stats.append("")
    if self.freeze > 0:
      self.stats.append("blue: %.3f freeze" % self.freeze)
    if self.armor_decay > 0:
      self.stats.append("cyan: %.2f armor breaking" % self.armor_decay)
    if self.magenta > 0:
      self.support = self.size / 20.0 + self.magenta / 16.0
      self.stats.append("magenta: adds %d damage to bubbles in range" % self.support)
    if self.color == (0, 0, 0):
      self.stats.append("black hole bonus: armor piercing")
    if self.yellow == 0 and self.magenta == 0 and self.cyan == 0:
      self.stats.append("purity bonus: +2 aspd")
    self.stats.append("")
    self.stats.append("kills: %d" % self.size)
    self.stats.append("radius: %d" % self.radius)

  def walk(self):
    if g.drag == self:
      self.vx += (g.drag_to[0] - self.x) / 30 * self.inertia
      self.vy += (g.drag_to[1] - self.y) / 30 * self.inertia
    else:
      if self.y + self.radius < g.h:
        self.vx += g.gravity[0]
        self.vy += g.gravity[1]

    self.phase = (self.phase + pi/12) % (2*pi)
    self.y += self.vy
    self.x += self.vx
    if self.x - self.radius < 0 or self.x + self.radius > g.w:
      self.vx *= -1
    if self.y - self.radius < 0 or self.y + self.radius > g.h:
      self.vy *= -1

    self.vx *= 0.97
    self.vy *= 0.97
#    if self.size < 50:
#      slowdown = 0.95 + self.size / 1000.0
#      self.vx *= slowdown
#      self.vy *= slowdown

    if self.last_shot + self.shot_delay < time.time():
      self.shoot()

    if self.support > 0:
      for tower in g.towers:
        if tower != self and tower.distance(self.x, self.y) < self.range \
            and tower.bonus_damage < self.support:
          tower.bonus_damage = self.support
          tower.update_stats()

  def draw(self):
    whalf = (1 + 0.2 *-sin(self.phase+0.2)) * self.radius
    hhalf = (1 + 0.2 * sin(self.phase)) * self.radius
    x = int(self.x - whalf)
    y = int(self.y - hhalf)
    rect = Rect(x-1, y-1, whalf*2+2, hhalf*2+2)
    pygame.draw.ellipse(g.screen, (20, 20, 20), rect, 0)
    rect = Rect(x, y, whalf*2, hhalf*2)
    pygame.draw.ellipse(g.screen, self.color, rect, 0)
    if self.target_point:
      pygame.draw.circle(g.screen, self.color, self.target_point, self.radius, 0)
      pygame.draw.line(g.screen, self.color, self.pos, self.target_point, self.radius)
      self.target_point = None

  def _get_monsters_in_range(self):
    for mob in g.mobs:
      if mob.hp > 0 and \
          abs(mob.x - self.x) < self.range and \
          abs(mob.y - self.y) < self.range and \
          self.distance(mob.x, mob.y) < self.range:
        yield mob

  def shoot(self):
    mobs = list(self._get_monsters_in_range())
    if not mobs:
      return
    self.last_shot = time.time()
    target = max(mobs, key=lambda mob: mob.danger)

    self.target_point = target.pos

    for mob in g.mobs:
      if mob.hp > 0 and \
          abs(mob.x - target.x) < self.radius and \
          abs(mob.y - target.y) < self.radius and \
          target.distance(mob.x, mob.y) < self.radius:
        if mob.damage(self.damage + self.bonus_damage, self):
          self.size += 1
          self.update_stats()
          g.hp = min(g.maxhp, g.hp + g.hp_per_monster)
          g.score += mob.level
    if self.bonus_damage:
      self.bonus_damage = 0
      self.update_stats()


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


def keypress(key):
  if key == K_F1:
    g.log("""Space: Pause game
b: Create a new bubble
1: Paint the bubble in red
2: Paint the bubble in green
3: Paint the bubble in blue
Tab: Select next bubble
n: Send the next wave of enemies
Drag&Drop, Arrow Keys or hjkl: Move the active bubble
q or ESC: quit""".split("\n"))
  elif key == K_F8:
    g.reset_game()
  elif key == ord("c"):
    g.logged.clear()
  elif key == ord("n"):
    g.nextwave = 0
  elif key == ord("d"):
    if pygame.key.get_mods() & KMOD_SHIFT and g.active:
      g.towers.remove(g.active)
      g.active = None
      g.drag = None
      g.drag_to = None
  elif key == ord("b"):
    if len(g.towers) < g.max_towers:
      g.towers.append(Tower())
  elif key == ord(" "):
    g.pause ^= True
  elif key in (K_1, K_2, K_3):
    if g.active:
      c = {K_1: "red", K_2: "green", K_3: "blue"}[key]
      if pygame.key.get_mods() & KMOD_SHIFT:
        if g.active.__dict__[c] > 0:
          g.active.__dict__[c] = max(0, g.active.__dict__[c] - g.color_step)
      else:
        if g.hp >= g.min_hp_for_buying and g.active.__dict__[c] < 255:
          g.hp -= g.hp_cost
          g.active.__dict__[c] = min(255, g.active.__dict__[c] + g.color_step)
      g.active.update_stats()
  elif key == K_TAB:
    if g.active:
      g.active = g.towers[(g.towers.index(g.active) + 1) % len(g.towers)]
    elif g.towers:
      g.active = g.towers[0]


def keyhold(pressed):
  if (pressed[K_j] or pressed[K_s] or pressed[K_DOWN]) and g.active:
    g.active.vy += 1.0 * g.active.inertia
  if (pressed[K_k] or pressed[K_w] or pressed[K_UP]) and g.active:
    g.active.vy -= 1.0 * g.active.inertia
  if (pressed[K_h] or pressed[K_a] or pressed[K_LEFT]) and g.active:
    g.active.vx -= 1.0 * g.active.inertia
  if (pressed[K_l] or pressed[K_d] or pressed[K_RIGHT]) and g.active:
    g.active.vx += 1.0 * g.active.inertia


def click(action, pos, button):
  if button == 1:
    if action == MOUSEBUTTONDOWN:
      for tower in reversed(g.towers):
        if tower.distance(pos[0], pos[1]) <= tower.radius:
          g.drag = tower
          g.active = tower
          g.drag_to = None
          break
      else:
        g.active = None
    elif action == MOUSEBUTTONUP:
      g.drag = None
      g.drag_to = None
  elif button == 3:
    g.active = None

# Lib {{{
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

def _random_color(maximum):
  color = [0, 0, 0]
  for i in range(min(3*255, maximum)):
    random.shuffle(color)
    for n in range(3):
      if color[n] < 255:
        color[n] += 1
        break
  return color
#}}}

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
