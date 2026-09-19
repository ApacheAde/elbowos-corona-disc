#!/usr/bin/env python3
"""Corona Disc — original ElbowOS neon disc-canyon arcade (Python 3 + pygame)."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys
from pathlib import Path

W, H = 1080, 1920
FPS = 30
SECONDS = 15
FRAMES = FPS * SECONDS
TITLE = "CORONA DISC"
OUT = Path("/home/workdir/artifacts/CORONA_DISC_ElbowOS.mp4")

if "--play" not in sys.argv:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402


def lerp(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


class Game:
    def __init__(self, seed=7):
        self.rng = random.Random(seed)
        self.score = 0
        self.t = 0
        self.combo = 0
        self.flash = 0
        self.wind = 0.0
        self.disc = {"x": W / 2, "y": 1680.0, "vx": 0.0, "vy": -22.0, "spin": 0.0, "live": True}
        self.rings = []
        self.pillars = []
        self.sparks = []
        self.motes = [[self.rng.uniform(0, W), self.rng.uniform(0, H), self.rng.uniform(0.4, 1.6)] for _ in range(50)]
        for i in range(6):
            self._spawn_ring(280 + i * 240)
        for i in range(4):
            self._spawn_pillar(400 + i * 320)

    def _spawn_ring(self, y=None):
        y = -80 if y is None else y
        self.rings.append({
            "x": self.rng.uniform(220, W - 220),
            "y": float(y),
            "r": self.rng.choice((70, 82, 96)),
            "hue": self.rng.choice(((70, 255, 190), (255, 210, 60), (255, 90, 200))),
            "hit": 0,
        })

    def _spawn_pillar(self, y=None):
        y = -120 if y is None else y
        side = self.rng.choice((-1, 1))
        self.pillars.append({
            "x": 90 if side < 0 else W - 90,
            "y": float(y),
            "w": self.rng.randint(140, 220),
            "h": self.rng.randint(90, 160),
            "side": side,
        })

    def launch(self, aim_x=None):
        d = self.disc
        if d["live"] and d["y"] < 1500:
            return
        tx = W / 2 if aim_x is None else aim_x
        d["x"], d["y"] = W / 2 + self.rng.uniform(-20, 20), 1680.0
        d["vx"] = (tx - d["x"]) * 0.028 + self.rng.uniform(-1.2, 1.2)
        d["vy"] = -self.rng.uniform(20, 26)
        d["spin"] = self.rng.uniform(-0.35, 0.35)
        d["live"] = True

    def tick(self, steer=0.0):
        self.t += 1
        self.wind = 2.4 * math.sin(self.t * 0.035)
        if self.flash:
            self.flash -= 1
        for r in self.rings:
            r["y"] += 5.2
            if r["hit"]:
                r["hit"] -= 1
        self.rings = [r for r in self.rings if r["y"] < H + 80]
        while len(self.rings) < 6:
            self._spawn_ring(min((r["y"] for r in self.rings), default=0) - 260)
        for p in self.pillars:
            p["y"] += 5.2
        self.pillars = [p for p in self.pillars if p["y"] < H + 100]
        while len(self.pillars) < 4:
            self._spawn_pillar(min((p["y"] for p in self.pillars), default=0) - 340)
        for m in self.motes:
            m[1] += m[2] + 2
            if m[1] > H:
                m[0], m[1] = self.rng.uniform(0, W), -10
        d = self.disc
        if not d["live"]:
            self.launch()
        d["vx"] += steer * 0.85 + self.wind * 0.04 + d["spin"] * 0.15
        d["vy"] += 0.42
        d["vx"] *= 0.992
        d["x"] += d["vx"]
        d["y"] += d["vy"]
        d["spin"] *= 0.995
        if d["x"] < 70:
            d["x"], d["vx"] = 70, abs(d["vx"]) * 0.7
        if d["x"] > W - 70:
            d["x"], d["vx"] = W - 70, -abs(d["vx"]) * 0.7
        for r in self.rings:
            if r["hit"]:
                continue
            dist = math.hypot(d["x"] - r["x"], d["y"] - r["y"])
            if dist < r["r"] - 8 and abs(d["y"] - r["y"]) < 28:
                r["hit"] = 14
                self.combo += 1
                self.score += 80 + self.combo * 20
                self.flash = 6
                for _ in range(16):
                    ang = self.rng.random() * 6.28
                    spd = self.rng.uniform(2, 8)
                    self.sparks.append([r["x"], r["y"], math.cos(ang) * spd, math.sin(ang) * spd, 16, r["hue"]])
        for p in self.pillars:
            left = 0 if p["side"] < 0 else W - p["w"]
            rect = pygame.Rect(left, int(p["y"]), p["w"], p["h"])
            if rect.collidepoint(d["x"], d["y"]):
                self.combo = 0
                self.score = max(0, self.score - 15)
                d["vx"] = -d["vx"] * 0.6 + (-2 if p["side"] < 0 else 2)
                d["vy"] *= 0.5
                for _ in range(10):
                    self.sparks.append([d["x"], d["y"], self.rng.uniform(-4, 4), self.rng.uniform(-4, 2), 12, (255, 120, 80)])
        if d["y"] < 180 or d["y"] > 1780 or d["vy"] > 18:
            d["live"] = False
            self.combo = 0
            self.launch()
        alive = []
        for s in self.sparks:
            s[0] += s[2]
            s[1] += s[3]
            s[4] -= 1
            if s[4] > 0:
                alive.append(s)
        self.sparks = alive
        if self.t % 15 == 0:
            self.score += 1

    def auto_steer(self):
        d = self.disc
        target = None
        best = 1e9
        for r in self.rings:
            if r["hit"]:
                continue
            if 200 < r["y"] < d["y"] - 40:
                dist = abs(r["x"] - d["x"]) + (d["y"] - r["y"]) * 0.15
                if dist < best:
                    best, target = dist, r
        if target is None:
            return -0.2 * math.sin(self.t * 0.1)
        err = (target["x"] + self.wind * 8) - d["x"]
        return max(-1.0, min(1.0, err / 90.0))


def draw(surf, g, fonts):
    font_lg, font_md, font_sm = fonts
    t = g.t
    for y in range(0, H, 8):
        c = lerp((18, 6, 42), (255, 90, 40), (y / H) ** 1.35)
        night = lerp((8, 10, 28), c, 0.55)
        pygame.draw.rect(surf, night, (0, y, W, 8))
    for i in range(7):
        yy = int((t * 6 + i * 280) % (H + 40)) - 20
        col = (255, 70 + i * 20, 160, 70)
        ribbon = pygame.Surface((W, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(ribbon, col, (int(80 + 40 * math.sin((t + i) * 0.07)), 0, 420, 18))
        surf.blit(ribbon, (0, yy))
    for m in g.motes:
        pygame.draw.circle(surf, (255, 210, 120), (int(m[0]), int(m[1])), 2)
    for i in range(12):
        y0 = int((i * 180 + t * 5.2) % (H + 180) - 180)
        pygame.draw.polygon(surf, (28, 14, 48), [(0, y0), (70, y0 + 40), (0, y0 + 90)])
        pygame.draw.polygon(surf, (28, 14, 48), [(W, y0 + 20), (W - 70, y0 + 70), (W, y0 + 120)])
    pygame.draw.rect(surf, (255, 140, 40), (0, 200, 12, H - 290))
    pygame.draw.rect(surf, (255, 70, 180), (W - 12, 200, 12, H - 290))
    for p in g.pillars:
        left = 0 if p["side"] < 0 else W - p["w"]
        rec = pygame.Rect(left, int(p["y"]), p["w"], p["h"])
        pygame.draw.rect(surf, (70, 24, 90), rec, border_radius=8)
        pygame.draw.rect(surf, (255, 90, 160), rec, 3, border_radius=8)
    for r in g.rings:
        col = r["hue"]
        thick = 10 if r["hit"] else 6
        pygame.draw.circle(surf, col, (int(r["x"]), int(r["y"])), r["r"], thick)
        pygame.draw.circle(surf, (255, 255, 230), (int(r["x"]), int(r["y"])), r["r"] - 8, 1)
        if r["hit"]:
            pygame.draw.circle(surf, col, (int(r["x"]), int(r["y"])), r["r"] + 12, 2)
    d = g.disc
    ang = t * 0.4 + d["spin"] * 8
    cx, cy = int(d["x"]), int(d["y"])
    glow = pygame.Surface((120, 120), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 170, 40, 70), (60, 60), 50)
    surf.blit(glow, (cx - 60, cy - 60))
    pygame.draw.circle(surf, (255, 200, 60), (cx, cy), 22)
    pygame.draw.circle(surf, (255, 255, 210), (cx, cy), 10)
    pygame.draw.line(surf, (80, 20, 10),
                     (cx + int(18 * math.cos(ang)), cy + int(18 * math.sin(ang))),
                     (cx - int(18 * math.cos(ang)), cy - int(18 * math.sin(ang))), 3)
    for s in g.sparks:
        pygame.draw.circle(surf, s[5], (int(s[0]), int(s[1])), max(1, s[4] // 3))
    if g.flash:
        v = pygame.Surface((W, H), pygame.SRCALPHA)
        v.fill((255, 220, 80, 35))
        surf.blit(v, (0, 0))
    bar = pygame.Surface((W, 150), pygame.SRCALPHA)
    bar.fill((16, 4, 28, 230))
    surf.blit(bar, (0, 0))
    surf.blit(font_lg.render(TITLE, True, (255, 190, 50)), (40, 16))
    surf.blit(font_sm.render("ElbowOS  ·  Python 3 disc canyon  ·  autoplay reel", True, (255, 160, 210)), (44, 92))
    sc = font_md.render(f"AURA  {g.score:05d}", True, (80, 255, 200))
    surf.blit(sc, (W - sc.get_width() - 40, 28))
    foot = pygame.Surface((W, 90), pygame.SRCALPHA)
    foot.fill((16, 4, 28, 230))
    surf.blit(foot, (0, H - 90))
    tag = font_sm.render("x.com/ElbowOS", True, (255, 190, 50))
    surf.blit(tag, (W - tag.get_width() - 40, H - 62))
    surf.blit(font_sm.render("A / D curve   ·   thread the corona rings", True, (200, 150, 190)), (40, H - 62))


def fonts():
    try:
        return (
            pygame.font.SysFont("dejavusans", 72, bold=True),
            pygame.font.SysFont("dejavusans", 42, bold=True),
            pygame.font.SysFont("dejavusans", 28),
        )
    except Exception:
        return pygame.font.Font(None, 80), pygame.font.Font(None, 48), pygame.font.Font(None, 32)


def record(out: Path = OUT) -> Path:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    surf = pygame.Surface((W, H))
    g = Game()
    fnt = fonts()
    tmp = out.with_suffix(".tmp.mp4")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "20", "-preset", "veryfast", "-movflags", "+faststart", str(tmp),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    for _ in range(FRAMES):
        g.tick(g.auto_steer())
        draw(surf, g, fnt)
        proc.stdin.write(pygame.image.tostring(surf, "RGB"))
    proc.stdin.close()
    err = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
    rc = proc.wait()
    pygame.quit()
    if rc != 0 or not tmp.exists():
        raise RuntimeError(f"ffmpeg failed ({rc}): {err[-800:]}")
    tmp.replace(out)
    return out


def play():
    os.environ.pop("SDL_VIDEODRIVER", None)
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((W // 2, H // 2))
    pygame.display.set_caption("Corona Disc — ElbowOS")
    canvas = pygame.Surface((W, H))
    clock = pygame.time.Clock()
    g = Game()
    fnt = fonts()
    running = True
    while running:
        steer = 0.0
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif ev.key == pygame.K_r:
                    g.score = 0
                    g.__init__(seed=random.randint(1, 9999))
                elif ev.key == pygame.K_SPACE:
                    g.launch()
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            steer -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            steer += 1
        g.tick(steer)
        draw(canvas, g, fnt)
        pygame.transform.smoothscale(canvas, screen.get_size(), screen)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


if __name__ == "__main__":
    if "--play" in sys.argv:
        play()
    else:
        path = record()
        print(path)
        print("bytes", path.stat().st_size)
        sys.exit(0)
