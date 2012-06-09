#!/usr/bin/python2 -OBts
# Copyright (C) 2012  Roman Zimbelmann <hut@lavabit.com>
# This software is distributed under the terms of the GNU GPL version 3.
"""Usage: wabbel [options]

Options:
  -h, --help
  --version
  --easy
  --fullscreen
  --profile
 
Key bindings:
Space: Pause game
F2: Create a new bubble
r: Add red color from the bubble (shift+r to remove)
g: Add green color from the bubble (shift+g to remove)
b: Add blue color from the bubble (shift+b to remove)
Tab: Select next bubble
0-9: Select certain bubbles, ordered by size
F3: Send the next wave of enemies
F11: Toggle fullscreen (unix only)
F5: Clear the message log
Drag&Drop, Arrow Keys or hjkl: Move the active bubble
Escape: quit"""

import getpass
import os.path
import pygame
import sys
import time
from collections import deque
from math import sin, cos, atan2, pi, sqrt
from pygame.locals import *
from random import random, randint, choice, shuffle
tau = 2 * pi

# -- TODO --
# Add more types of enemies?
# Maps that morph and breathe, with edge points spiraling in and out


class Globals(object):
  def __init__(g):  # "g" instead of "self" used for consistency reasons
    """
    Variables that are initialized here never change, apart of the
    ones which only make sense to be defined in run_game().
    """
    g.color_step = 12
    g.easy = '--easy' in sys.argv
    g.font_name = None
    g.font_size = 16, 24
    g.fullscreen = '--fullscreen' in sys.argv
    g.growth_per_kill = 1
    g.growth_per_shot = 0.05
    g.highscorefile = os.path.expanduser("~/.wabbel_highscore")
    g.hp_cost = 0.5 if g.easy else 1
    g.hp_damage = 0.3 if g.easy else 0.6
    g.hp_per_monster = 0.3
    g.level_layouts = [
        [(0, 7), (4, 5), (5, 9), (9.5, 8), (7, 2), (0, 3)],
        [(4, 0), (4.4, 5), (2, 7), (3, 9), (8, 8), (5.6, 5), (6, 0)],
        [(1, 0), (2, 4), (8, 3), (4, 9), (8, 6), (7, 10)],
        [(0, 4), (3.5, 4), (5, 2), (7, 2), (3, 7), (7, 7), (9, 5), (0, 5)],
    ]
    g.max_drag_dist = 100
    g.maxfps = 30
    g.max_towers = 20
    g.min_hp_for_buying = 2
    g.monster_min_armor = 0.5
    g.monster_min_speed = 0.3
    try:
      g.name = os.environ.get("USER", getpass.getuser())
    except:
      g.name = "unknown"
    g.profile = '--profile' in sys.argv
    g.range_color = (32, 32, 32)
    g.version = "0.1"
    g.waves_per_level = 10
    g.w, g.h = 800, 600

    # initialized in run_game()
    g.clock = None
    g.font = None
    g.font_small = None
    g.screen = None

    g.reset_game()

  def reset_game(g):
    """
    Variables that are initialized here are modified throughout the game and
    are reset to their defaults when a new game is started.
    """
    g.active = None
    g.drag = None
    g.dt = 0
    g.game_time = 0
    g.hp = 10
    g.level = 0
    g.logged = deque(maxlen=30)
    g.maxhp = g.hp
    g.mobs = []
    g.nextwave = 6.6
    g.nextwavemax = g.nextwave
    g.pause = False
    g.score = 0
    g.shake = (0, 0)
    g.shake_until = 0
    g.towers = list()
    g.waves = list()
    g.change_level()

  def change_level(g):
    """
    Variables that are initialized here are updated every time the level is
    changed, which occurs every g.waves_per_level waves.
    """
    g.level_color = _random_color(0xaf)
    g.checkpoints = [(int(d[0] * g.w / 10), int(d[1] * g.h / 10)) for d in
        choice(g.level_layouts)]
    if randint(0,1) == 0:
      g.checkpoints = [(g.w-d[0], d[1]) for d in g.checkpoints]
    if randint(0,1) == 0:
      g.checkpoints = [(d[0], g.h-d[1]) for d in g.checkpoints]
    if randint(0,1) == 0:
      g.checkpoints.reverse()

    # global gravity
    if g.easy or randint(0,3) == 0:
      g.gravity = (0, 0)
    else:
      g.gravity = (0, 0.001 * randint(0, min(100, g.level * 3)))
      if randint(0, 2) == 0:
        # vertical gravity instead
        g.gravity = (choice([1, -1]) * g.gravity[1], 0)

  def log(g, *things):
    g.logged.extend([str(obj) for obj in things])

  def lose(g):
    g.hp = 0
    g.log("You have lost the game! Press F8 to restart.")
    g.log("Final Score: %d" % g.score)
    try:
      highscores = open(g.highscorefile, "r").read().strip().split("\n")
    except:
      highscores = []

    if g.score > 0:
      highscores.append("%d - %s" % (g.score, g.name + (" (easy)" if g.easy else "")))
      highscores.sort(key=_highscore_sorting_key)
      highscores.reverse()
      f = open(g.highscorefile, "w")
      f.write("\n".join(highscores) + "\n")

    g.log(" ", "Top 10:", *highscores[:10])


def run_game():
  """
  Start the game, initialize pygame and run the input/draw loop
  """
  pygame.init()
  pygame.font.init()
  pygame.key.set_repeat(180, 80)
  flags = DOUBLEBUF | (g.fullscreen and FULLSCREEN)
  g.screen = pygame.display.set_mode((g.w, g.h), flags, 32)
  g.font_small = pygame.font.Font(g.font_name, g.font_size[0])
  g.font = pygame.font.Font(g.font_name, g.font_size[1])
  g.clock = pygame.time.Clock()
  g.log("Welcome! Press F1 to display help.")

  next_log_refresh = 0

  while True:
    time_before = time.time()
    g.clock.tick(g.maxfps)
    if next_log_refresh <= time.time():
      next_log_refresh = time.time() + 1
      g.log("")

    for event in pygame.event.get():
      if event.type == QUIT:
        return
      elif event.type == KEYDOWN:
        keypress(event.key)
      elif event.type in (MOUSEBUTTONDOWN, MOUSEBUTTONUP):
        click(event.type, event.pos, event.button)
    keyhold(pygame.key.get_pressed())

    # Handle waves, monsters and towers:
    if g.hp > 0 and not g.pause:
      if g.towers or g.level:
        if g.level and g.level % g.waves_per_level == 0:
          if g.mobs:
            g.nextwave = g.nextwavemax
          else:
            g.change_level()
            g.nextwave = 0

        g.nextwave -= g.dt
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

    if g.hp > 0 and not g.pause:
      g.towers.sort(key=lambda tower: -tower.size)
      for i, tower in enumerate(tuple(g.towers)):
        tower.walk()
        # gravitational attraction:
        for other in g.towers[i+1:]:
          angle = atan2(tower.y - other.y, tower.x - other.x)
          distance = tower.distance(other.x, other.y)
          if int(distance) in (range(25, 50) if g.easy else range(10,200)):
            g1 = tower.size + 1
            g2 = other.size + 1
            attraction = (g1 * g2) / distance**2
            tower.vx -= cos(angle) * attraction / g1 / tower.pinhead
            tower.vy -= sin(angle) * attraction / g1 / tower.pinhead
            other.vx += cos(angle) * attraction / g2 / other.pinhead
            other.vy += sin(angle) * attraction / g2 / other.pinhead
    draw_game()
    if not g.pause:
      g.dt = time.time() - time_before
      g.game_time += g.dt


def draw_game():
  """
  Draw the level, the UI and the actors.
  """
  g.screen.fill((0, 0, 0))
  if g.active:
    pygame.draw.circle(g.screen, g.range_color, g.active.pos, g.active.range, 0)

  if g.shake_until > g.game_time:
    g.shake = (randint(-3,3), randint(-3,3))

  dark = [int(clr*0.5) for clr in g.level_color]
  checkpoints = tuple((dot[0] + g.shake[0], dot[1] + g.shake[1]) for dot in g.checkpoints)
  pygame.draw.lines(g.screen, dark, False, checkpoints, 10)
  pygame.draw.lines(g.screen, g.level_color, False, checkpoints, 2)
  for dot in checkpoints:
    pygame.draw.circle(g.screen, dark, (dot[0], dot[1] + 1), 8, 0)
    pygame.draw.circle(g.screen, g.level_color, (dot[0], dot[1] + 1), 8, 1)

  for mob in g.mobs:
    mob.draw()

  for tower in tuple(g.towers):
    tower.draw()

  if g.drag:
    pygame.draw.line(g.screen, g.drag.color, g.drag.pos, pygame.mouse.get_pos(), 3)

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
      text = g.font_small.render(line, 1, (255, 255, 255))
      g.screen.blit(text, (x - text.get_rect().width, y))
      y += text.get_rect().height + 2

  x, y = 20, 0
  for line in g.logged:
    if not line:
      continue
    text = g.font.render(line, 1, (255, 255, 255))
    g.screen.blit(text, (x, y))
    y += text.get_rect().height + 2

  line = str(g.score)
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
  # Generate the rotating model of monster 1
  cross = [(-5,-1), (-1,-1), (-1,-5), (1,-5), (1,-1), (5,-1), (5,1), (1,1),
      (1,5), (-1,5), (-1,1), (-5,1)]
  steps = [i * tau / 24 for i in range(24)]
  rotated_cross = [[(p[0] * sin(a) + p[1] * cos(a), -p[0] * cos(a) + p[1] * sin(a))
    for p in cross] for a in steps]

  def __init__(self, level):
    self.level = level
    self.hp = 8 * level
    self.checkpoint = 0
    self.speed = 1 + level * 0.1 + randint(-10,10) * 0.04
    self.danger = 0
    self.phase = 0
    self.armor = max(0, (level - 5)/2)
    self.color = (randint(1,3) * 63, randint(1,3) * 63, randint(1,3) * 63)
    self.x, self.y = g.checkpoints[self.checkpoint]
    if level % 3 == 0:
      self.square = True
      self.armor = max(1, self.armor * 2)
      self.hp *= 0.5
      self.speed *= 0.8
    else:
      self.square = False

    self.maxhp = float(self.hp)
    self.original_speed = self.speed
    self.original_color = self.color
    self.original_armor = self.armor

  def walk(self):
    self.phase = (self.phase + 30 * g.dt * tau / len(self.steps)) % tau
    point1 = g.checkpoints[self.checkpoint]
    point2 = g.checkpoints[self.checkpoint + 1]
    angle = atan2(point2[1] - point1[1], point2[0] - point1[0])
    step = self.speed * g.dt * 30
    self.x += cos(angle) * step
    self.y += sin(angle) * step
    self.danger += self.speed * g.dt
    if abs(point2[0] - self.x) < step * 2 and \
        abs(point2[1] - self.y) < step * 2:
      if self.checkpoint >= len(g.checkpoints) - 2:
        self.hp = 0
        if g.hp > 0:
          g.hp -= g.hp_damage
          g.shake_until = max(g.shake_until, g.game_time + 2.0)
          if g.hp <= 0:
            g.lose()
      else:
        self.checkpoint += 1
        self.x, self.y = g.checkpoints[self.checkpoint]

  def draw(self):
    x, y = int(self.x + g.shake[0]), int(self.y + g.shake[1])
    if self.square:
      pygame.draw.rect(g.screen, self.color, Rect(x-4, y-4, 8, 8), 3)
    else:
      pygame.draw.polygon(g.screen, self.color, [(x+p, y+q) for p, q in
        self.rotated_cross[int(self.phase / tau * len(self.steps))]], 1)

  def damage(self, damage, tower):
    damage = max(0, damage - self.armor * (1 - tower.armor_pierce))
    self.hp -= damage
    self.color = _scale_color(self.original_color, self.hp / self.maxhp)
    self.color = [max(0, min(255, int(c * self.hp / self.maxhp))) for c in self.original_color]
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
  starting_towers = [(60, 0, 0), (0, 60, 0), (0, 0, 60)]
  def __init__(self):
    if g.towers:
      self.color = choice(self.starting_towers)
    else:
      self.color = self.starting_towers[0]
    self.red, self.green, self.blue = self.color
    self.size = 0
    self.x = g.w
    self.y = g.h * 0.5
    self.vx = randint(-100, -40)
    self.vy = randint(-100, 100)
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
    if self.magenta > 0:
      self.support = self.size / 20.0 + self.magenta / 16.0
    self.radius = int(sqrt((50 + self.size * 1.5) * pi))
    self.range = int(self.radius + 30 + sqrt(g * 10) * 2)

    self.shot_delay = max(0.1, 0.4 - (0.3 * self.yellow / 255.0) \
        + (self.size / 10000.0))
    if self.yellow == 0 and self.magenta == 0 and self.cyan == 0:
      self.shot_delay = 1 / (1 / (self.shot_delay) + 2)
    self.pinhead = 7 if all(color in range(76, 128) for color in self.color) else 1
    self.inertia = 4.0 / (4 + self.size * self.pinhead / 100.0)
    if self.color == (0, 0, 0):
      self.armor_pierce = 1

    self.dps = 1 / self.shot_delay * (self.damage + self.bonus_damage)

    self.stats = []
    self.stats.append("DPS: %.2f" % self.dps)
    self.stats.append("damage: %d + %d + %d" % (size_damage, red_damage,
      self.bonus_damage))
    self.stats.append("range: %d" % self.range)
    self.stats.append("attacks per second: %.2f" % (1 / self.shot_delay))
    self.stats.append("")
    if self.yellow > 0:
      self.stats.append("yellow: +%.2f attacks/second" % \
          (1 / self.shot_delay - 1 / max(0.1, 0.4 + (self.size / 10000.0))))
    if self.freeze > 0:
      self.stats.append("blue: %.3f freeze" % self.freeze)
    if self.armor_decay > 0:
      self.stats.append("cyan: %.2f armor breaking" % self.armor_decay)
    if self.magenta > 0:
      self.stats.append("magenta: +%d damage to bubbles in range" % self.support)
    if self.color == (0, 0, 0):
      self.stats.append("black hole bonus: armor piercing")
    if self.pinhead > 1:
      self.stats.append("pin head bonus: +600% inertia")
    if self.yellow == 0 and self.magenta == 0 and self.cyan == 0:
      self.stats.append("purity bonus: +2 attacks/second")
    self.stats.append("")
    self.stats.append("power level: %d" % self.size)
    self.stats.append("radius: %d" % self.radius)

  def walk(self):
    if g.drag == self:
      mouse = pygame.mouse.get_pos()
      if self.distance(mouse[0], mouse[1]) < g.max_drag_dist:
        xtarget, ytarget = mouse
      else:
        # limit the ability to pull on a bubble
        angle = atan2(mouse[1] - self.y, mouse[0] - self.x)
        xtarget = self.x + g.max_drag_dist * cos(angle)
        ytarget = self.y + g.max_drag_dist * sin(angle)
      self.vx += (xtarget - self.x) / 30 * self.inertia * g.dt * 30
      self.vy += (ytarget - self.y) / 30 * self.inertia * g.dt * 30
    else:
      if self.y + self.radius < g.h:
        self.vx += g.gravity[0] / self.pinhead * g.dt * 30
        self.vy += g.gravity[1] / self.pinhead * g.dt * 30

    self.phase = (self.phase + tau/24*30*g.dt) % tau
    self.x = min(g.w, max(0, self.x + self.vx * g.dt * 30))
    self.y = min(g.h, max(0, self.y + self.vy * g.dt * 30))
    self.vx *= 0.97
    self.vy *= 0.97
    if self.x - self.radius < 0 and self.vx < 0 or \
        self.x + self.radius > g.w and self.vx > 0:
      self.vx *= -1
    if self.y - self.radius < 0 and self.vy < 0 or \
        self.y + self.radius > g.h and self.vy > 0:
      self.vy *= -1

    if self.last_shot + self.shot_delay < g.game_time:
      self.shoot()

    if self.support > 0:
      for tower in g.towers:
        if tower != self and tower.distance(self.x, self.y) < self.range \
            and tower.bonus_damage < self.support:
          tower.bonus_damage = self.support
          tower.update_stats()

  def draw(self):
    width  = (1 - 0.2 * sin(self.phase+0.2)) * self.radius * 2
    height = (1 + 0.2 * sin(self.phase)) * self.radius * 2
    x = int(self.x - width / 2)
    y = int(self.y - height / 2)
    rect = Rect(x - 1, y - 1, width + 2, height + 2)
    pygame.draw.ellipse(g.screen, (20, 20, 20), rect, 0)
    rect = Rect(x, y, width, height)
    pygame.draw.ellipse(g.screen, self.color, rect, 0)
    if self.target_point:
      pygame.draw.circle(g.screen, self.color, self.target_point, self.radius, 0)
      pygame.draw.line(g.screen, self.color, self.pos, self.target_point, self.radius)
      self.target_point = None

  def _get_monsters_in_range(self, r, x, y):
    for mob in g.mobs:
      if mob.hp > 0 and \
          abs(mob.x - x) < r and \
          abs(mob.y - y) < r and \
          mob.distance(x, y) < r:
        yield mob

  def shoot(self):
    mobs = list(self._get_monsters_in_range(self.range, self.x, self.y))
    if not mobs:
      return
    self.size += g.growth_per_shot
    self.last_shot = g.game_time
    target = max(mobs, key=lambda mob: mob.danger)

    self.target_point = target.pos

    for mob in self._get_monsters_in_range(self.radius, target.x, target.y):
      if mob.damage(self.damage + self.bonus_damage, self):
        self.size += g.growth_per_kill
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
    if self.last_send + self.delay < g.game_time:
      g.mobs.append(Monster(self.level))
      self.monsters_left -= 1
      self.last_send = g.game_time


def keypress(key):
  if key == K_ESCAPE:
    raise SystemExit()
  elif key == K_F1:
    g.log(*__doc__.split("\n")[8:])
  elif key == K_F8:
    g.reset_game()
  elif key == K_F11:
    pygame.display.toggle_fullscreen()
  elif key == K_F5:
    g.logged.clear()
  elif key in (K_n, K_F3):
    g.nextwave = 0
  elif key == K_d:
    if pygame.key.get_mods() & KMOD_SHIFT and g.active:
      g.towers.remove(g.active)
      g.active = None
      g.drag = None
  elif key in (K_c, K_F2):
    if len(g.towers) < g.max_towers:
      g.towers.append(Tower())
  elif key == K_SPACE:
    g.pause ^= True
  elif key in range(K_1, K_9 + 1):
    if len(g.towers) > key - K_1:
      g.active = g.towers[key - K_1]
  elif key == K_0:
    if len(g.towers):
      g.active = g.towers[-1]
  elif key in (K_r, K_g, K_b):
    if g.active:
      c = {K_r: "red", K_g: "green", K_b: "blue"}[key]
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
      g.active = g.towers[(g.towers.index(g.active) + \
          (-1 if (pygame.key.get_mods() & KMOD_SHIFT) else 1)) % len(g.towers)]
    elif g.towers:
      g.active = g.towers[0]


def keyhold(pressed):
  if (pressed[K_j] or pressed[K_s] or pressed[K_DOWN]) and g.active:
    g.active.vy += 30.0 * g.active.inertia * g.dt
  if (pressed[K_k] or pressed[K_w] or pressed[K_UP]) and g.active:
    g.active.vy -= 30.0 * g.active.inertia * g.dt
  if (pressed[K_h] or pressed[K_a] or pressed[K_LEFT]) and g.active:
    g.active.vx -= 30.0 * g.active.inertia * g.dt
  if (pressed[K_l] or pressed[K_d] or pressed[K_RIGHT]) and g.active:
    g.active.vx += 30.0 * g.active.inertia * g.dt


def click(action, pos, button):
  if button == 1:
    if action == MOUSEBUTTONDOWN:
      for tower in reversed(g.towers):
        if tower.distance(pos[0], pos[1]) <= tower.radius:
          g.drag = tower
          g.active = tower
          break
      else:
        g.active = None
    elif action == MOUSEBUTTONUP:
      g.drag = None
  elif button == 3:
    g.active = None


def _draw_bar(x, y, length, width, color):
  if length > 0:
    pygame.draw.line(g.screen, color, (x, y), (x + length, y), width)


def _random_color(maximum):
  color = [random(), random(), random()]
  return [min(255, int(maximum / sum(color) * n)) for n in color]


def _highscore_sorting_key(line):
  try:
    return int(line.split()[0])
  except:
    return 0


if __name__ == '__main__':
  global g
  g = Globals()

  if '--help' in sys.argv or '-h' in sys.argv:
    print(__doc__)
  elif '--version' in sys.argv:
    print(g.version)

  else:
    if g.profile:
      import cProfile
      import pstats
      exit_code = cProfile.run('sys.modules[__name__].run_game()', '/tmp/profile')
      p = pstats.Stats('/tmp/profile')
      p.strip_dirs().sort_stats('cumulative').print_callees()
    else:
      run_game()
