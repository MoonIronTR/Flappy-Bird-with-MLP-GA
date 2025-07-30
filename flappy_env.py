# -------- FLAPPY ENVIRONMENT + ORTAK KAYNAKLAR ----------
import random, os, pygame

ASSET_SPR = "assets/sprites/"
ASSET_SND = "assets/audio/"

# Pygame gizli surface – convert() sorunlarını önler
if not pygame.get_init():
    pygame.init()
if pygame.display.get_surface() is None:
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
pygame.mixer.init()


class FlappyEnv:
    """
    Gameplay alanı   : 0–400 px
    Pencere yüksekliği: 600 px  (alt +88 px boşluk)
    draw_base()      : Base sprite'ını tek sefer çizer, alt boşluğu bej renkle doldurur
    """

    # ---------------- Pencere & Fizik ----------------
    WIN_W, WIN_H = 288, 600
    GROUND_Y     = 400
    GRAVITY      = 0.45
    FLAP_VEL     = -8
    PIPE_W       = 52
    PIPE_SPEED   = 3
    PIPE_FREQ    = 90
    GAP_MIN, GAP_MAX = 100, 160

    # ---------------- Sprites ----------------
    bg_img   = pygame.image.load(ASSET_SPR + "background-day.png").convert()
    base_img = pygame.image.load(ASSET_SPR + "base.png").convert_alpha()
    base_w   = base_img.get_width()

    bird_frames = [
        pygame.image.load(ASSET_SPR + f"bluebird-{p}flap.png").convert_alpha()
        for p in ("up", "mid", "down")
    ]
    pipe_down = pygame.image.load(ASSET_SPR + "pipe-red.png").convert_alpha()
    pipe_up   = pygame.transform.flip(pipe_down, False, True)
    digits    = {str(i): pygame.image.load(ASSET_SPR + f"{i}.png").convert_alpha()
                 for i in range(10)}
    sound_on  = pygame.transform.smoothscale(
        pygame.image.load(ASSET_SPR + "soundopen.png").convert_alpha(), (24, 24))
    sound_off = pygame.transform.smoothscale(
        pygame.image.load(ASSET_SPR + "soundclosed.png").convert_alpha(), (24, 24))

    # ---------------- Sesler ----------------
    @staticmethod
    def _snd(name):
        for ext in (".wav", ".ogg"):
            path = os.path.join(ASSET_SND, name + ext)
            if os.path.isfile(path):
                return pygame.mixer.Sound(path)
        return None

    SND_WING, SND_POINT, SND_HIT, SND_DIE, SND_SWOOSH = map(
        _snd, ("wing", "point", "hit", "die", "swoosh")
    )

    # ---------------- Base çizici ----------------
    @classmethod
    def draw_base(cls, surf: pygame.Surface, start_x: int) -> None:
        """Kaydırmalı base + bej dolgu"""
        surf.blit(cls.base_img, (start_x,              cls.GROUND_Y))
        surf.blit(cls.base_img, (start_x + cls.base_w, cls.GROUND_Y))

        base_h   = cls.base_img.get_height()
        fill_top = cls.GROUND_Y + base_h
        if fill_top < cls.WIN_H:
            beige = cls.base_img.get_at((0, base_h - 1))
            surf.fill(beige, pygame.Rect(0, fill_top,
                                         cls.WIN_W, cls.WIN_H - fill_top))

    # ---------------- Ortam ----------------
    def __init__(self, shrink_gap: bool = True):
        self.shrink_gap = shrink_gap
        self.reset()

    def reset(self, score_for_gap: int = 0):
        self.y = self.WIN_H // 2
        self.vy = 0
        self.pipes = []
        self.ticks = 0
        self.score_total = 0
        self.score_for_gap = score_for_gap
        self.alive = True
        return self._state()

    def step(self, flap: bool):
        if flap:
            self.vy = self.FLAP_VEL
        self.vy += self.GRAVITY
        self.y  += self.vy

        # Boru üret
        self.ticks += 1
        if self.ticks % self.PIPE_FREQ == 0:
            gap = self._new_gap()
            top = random.randint(50, self.GROUND_Y - gap - 50)
            self.pipes.append({"x": self.WIN_W,
                               "top": top, "gap": gap,
                               "counted": False})

        # Boruları kaydır
        for p in self.pipes:
            p["x"] -= self.PIPE_SPEED
        if self.pipes and self.pipes[0]["x"] < -self.PIPE_W:
            self.pipes.pop(0)

        # Skor
        for p in self.pipes:
            if p["x"] + self.PIPE_W < 50 and not p["counted"]:
                self.score_total += 1
                self.score_for_gap += 1
                p["counted"] = True

        self._collide()
        return self._state(), not self.alive

    # ---------------- Yardımcı ----------------
    def _state(self):
        dx, gy, g = self.WIN_W, self.WIN_H / 2, self.GAP_MAX
        for p in self.pipes:
            if p["x"] + self.PIPE_W >= 50:
                dx, gy, g = p["x"] - 50, p["top"] + p["gap"] / 2, p["gap"]
                break
        return (self.y, self.vy, dx, gy, g)

    def _new_gap(self):
        if not self.shrink_gap:
            return self.GAP_MAX
        max_gap = max(self.GAP_MIN,
                      self.GAP_MAX - (self.score_for_gap // 10) * 10)
        return random.choice(range(self.GAP_MIN, max_gap + 1, 10))

    def _collide(self):
        if self.y <= 0 or self.y >= self.GROUND_Y:
            self.alive = False
            return
        for p in self.pipes:
            if 50 in range(int(p["x"]), int(p["x"]) + self.PIPE_W):
                if not (p["top"] < self.y < p["top"] + p["gap"]):
                    self.alive = False
                    break
