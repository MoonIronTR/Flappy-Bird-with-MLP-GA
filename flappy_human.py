import os
import sys
import pygame

# Pencere konumu (Windows)
os.environ["SDL_VIDEO_WINDOW_POS"] = "800,300"

# Modül içe aktarma
from flappy_env import FlappyEnv
import flappy_ga

# Pygame başlatma
pygame.init()
WIN_W, WIN_H = FlappyEnv.WIN_W, FlappyEnv.WIN_H
screen = pygame.display.set_mode((WIN_W, WIN_H))
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 24, bold=True)


HS_FILE = "highscores.txt"

def hs_read():
    if os.path.isfile(HS_FILE):
        return [int(x) for x in open(HS_FILE).read().split()]
    return []

def hs_write(lst):
    with open(HS_FILE, "w") as f:
        f.write(" ".join(map(str, lst)))

def save_hs(sc):
    hs_write(sorted(hs_read() + [sc], reverse=True)[:10])



def draw_digits(num, y=20):
    s = str(num)
    w = sum(FlappyEnv.digits[ch].get_width() for ch in s)
    x = (WIN_W - w) // 2
    for ch in s:
        screen.blit(FlappyEnv.digits[ch], (x, y))
        x += FlappyEnv.digits[ch].get_width()



play_r = pygame.Rect(0, 0, 140, 40)
play_r.center = (WIN_W // 2, WIN_H // 2 - 40)

ga_r = pygame.Rect(0, 0, 140, 40)
ga_r.center = (WIN_W // 2, WIN_H // 2 + 10)

hs_r = pygame.Rect(0, 0, 140, 40)
hs_r.center = (WIN_W // 2, WIN_H // 2 + 60)

mute_r = FlappyEnv.sound_on.get_rect(topright=(WIN_W - 6, 6))



all_sounds = [
    s for s in (
        FlappyEnv.SND_WING,
        FlappyEnv.SND_POINT,
        FlappyEnv.SND_HIT,
        FlappyEnv.SND_DIE,
        FlappyEnv.SND_SWOOSH
    ) if s
]

is_muted = False

def set_volume(v):
    for s in all_sounds:
        s.set_volume(v)




STATE = "menu"
env = FlappyEnv()
anim = 0
base_x = 0

while True:
    clock.tick(60)

    # ----- Girdi -----
    for e in pygame.event.get():

        if e.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and mute_r.collidepoint(e.pos):
            is_muted = not is_muted
            set_volume(0 if is_muted else 1)
            continue

        # Menü etkileşimleri
        if STATE == "menu" and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if play_r.collidepoint(e.pos):
                env.reset()
                STATE = "play"
                anim = 0
            elif ga_r.collidepoint(e.pos):
                flappy_ga.run_ga(screen)
                pygame.event.clear()
            elif hs_r.collidepoint(e.pos):
                STATE = "highscores"

        # Skordan veya game over ekranından menüye dön
        elif STATE in ("highscores", "game_over") and e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            STATE = "menu"

        # Kuş uçur
        elif STATE == "play" and env.alive:
            if (
                (e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_UP)) or
                (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not mute_r.collidepoint(e.pos))
            ):
                env.step(True)
                if FlappyEnv.SND_WING and not is_muted:
                    FlappyEnv.SND_WING.play()


    # ----- Mantık -----
    if STATE == "play":
        old = env.score_total

        if env.alive:
            env.step(False)

        if env.score_total > old and FlappyEnv.SND_POINT and not is_muted:
            FlappyEnv.SND_POINT.play()

        anim = (anim + 1) % 15
        base_x = (base_x - FlappyEnv.PIPE_SPEED) % -FlappyEnv.base_w

        if not env.alive:
            save_hs(env.score_total)
            if FlappyEnv.SND_DIE and not is_muted:
                FlappyEnv.SND_DIE.play()
            STATE = "game_over"


    # ----- Çizim -----
    screen.blit(FlappyEnv.bg_img, (0, 0))

    if STATE in ("play", "game_over"):
        for p in env.pipes:
            screen.blit(FlappyEnv.pipe_up,   (p["x"], p["top"] - FlappyEnv.pipe_up.get_height()))
            screen.blit(FlappyEnv.pipe_down, (p["x"], p["top"] + p["gap"]))

    FlappyEnv.draw_base(screen, base_x)

    if STATE in ("play", "game_over"):
        frame = FlappyEnv.bird_frames[(anim // 5) % 3 if env.alive else 1]
        screen.blit(frame, (46, env.y - 12))


    # Menü arayüzü
    if STATE == "menu":
        for r, t in ((play_r, "Play"), (ga_r, "Run Algorithm"), (hs_r, "High Scores")):
            pygame.draw.rect(screen, (0, 0, 0), r, 2)
            text = font.render(t, True, (255, 255, 255))
            screen.blit(text, text.get_rect(center=r.center))

    elif STATE == "highscores":
        screen.blit(font.render("TOP 10 SCORES", True, (255, 255, 255)), (WIN_W // 2 - 80, 60))
        for i, sc in enumerate(hs_read(), 1):
            screen.blit(font.render(f"{i:>2}. {sc}", True, (255, 255, 255)), (WIN_W // 2 - 60, 100 + i * 28))

    elif STATE == "game_over":
        go = pygame.image.load("assets/sprites/gameover.png").convert_alpha()
        screen.blit(go, go.get_rect(center=(WIN_W // 2, WIN_H // 2 - 40)))
        screen.blit(font.render("Click / key → Menu", True, (255, 255, 255)),
                    (WIN_W // 2 - 100, WIN_H // 2 + 10))


    # Skor
    if STATE == "play":
        draw_digits(env.score_total)

    # Ses butonu
    screen.blit(FlappyEnv.sound_off if is_muted else FlappyEnv.sound_on, mute_r)

    pygame.display.flip()
