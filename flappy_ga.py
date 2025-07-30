# ------------- flappy_ga.py -------------
import os, pygame, random, numpy as np
os.environ["SDL_VIDEO_WINDOW_POS"] = "100,30"

from flappy_env import FlappyEnv

# ---------- GA sabitleri ----------
POP, HOF         = 500, 4
TOUR_SIZE        = 8
MUT_P            = 0.25
SIGMA_INIT       = 0.6
SIGMA_DECAY      = 0.97
STUCK_BOOST      = 1.5
WEAK_TICKS       = 180
SPEEDS           = [60, 120, 240, 480]

IN_N, H_N, OUT_N = 5, 14, 1
GENOME           = IN_N*H_N + H_N + H_N*OUT_N + OUT_N

# ---------- Genome helpers ----------
def split_genome(g):
    i = 0
    W1 = g[i:i+IN_N*H_N].reshape(IN_N, H_N); i += IN_N*H_N
    b1 = g[i:i+H_N];                          i += H_N
    W2 = g[i:i+H_N*OUT_N].reshape(H_N, OUT_N); i += H_N*OUT_N
    b2 = g[i:i+OUT_N]
    return W1, b1, W2, b2

def ffw(g, x):
    W1, b1, W2, b2 = split_genome(g)
    return 1 / (1 + np.exp(-(np.tanh(x @ W1 + b1) @ W2 + b2)))[0]

# ---------- Individual ----------
class Bird:
    def __init__(self, g=None):
        self.g = g if g is not None else np.random.randn(GENOME)
        self.reset()
    def reset(self):
        self.y, self.vy = FlappyEnv.WIN_H//2, 0
        self.score = self.t = 0
        self.alive = True
    def act(self, s): return ffw(self.g, s) > .5

# ---------- GA utilities ----------
def crossover(g1, g2, sigma):
    child = g1.copy()
    mask  = np.random.rand(GENOME) < .5
    child[mask] = g2[mask]
    mut   = np.random.rand(GENOME) < MUT_P
    child[mut] += np.random.randn(mut.sum()) * sigma
    return child

def tournament(pool):
    k = min(len(pool), TOUR_SIZE)
    cand = random.sample(pool, k)
    cand.sort(key=lambda x: x[0], reverse=True)
    return cand[0][1]

def draw_num(scr, n, y=20):
    s = str(n)
    w = sum(FlappyEnv.digits[d].get_width() for d in s)
    x = (FlappyEnv.WIN_W - w)//2
    for d in s:
        scr.blit(FlappyEnv.digits[d], (x, y)); x += FlappyEnv.digits[d].get_width()

# ---------- Ağ görselleştirici ----------
def draw_network(scr, g):
    W1, _, W2, _ = split_genome(g)
    label_pad = 60
    left_x    = label_pad + 10
    right_x   = FlappyEnv.WIN_W - 14
    mid_x     = (left_x + right_x)//2 - 30
    base_y    = FlappyEnv.GROUND_Y + 20

    inp  = [(left_x,  base_y + i * 18) for i in range(IN_N)]
    hid  = [(mid_x,   base_y + j * 12) for j in range(H_N)]
    outp = [(right_x, base_y + 36)]

    def line(p1, p2, w):
        col = (0, 230, 0) if w > 0 else (230, 0, 0)
        pygame.draw.line(scr, col, p1, p2, max(1, int(abs(w) * 2.5)))

    for i, (x1, y1) in enumerate(inp):
        for j, (x2, y2) in enumerate(hid):
            line((x1 + 6, y1), (x2 - 6, y2), W1[i, j])
    for j, (x1, y1) in enumerate(hid):
        line((x1 + 6, y1), (outp[0][0] - 6, outp[0][1]), W2[j, 0])

    labels = ("y pos", "y vel", "dx", "gap y", "gap size")
    for (x, y), lbl in zip(inp, labels):
        pygame.draw.circle(scr, (50, 50, 255), (x, y), 6, 1)
        scr.blit(small.render(lbl, True, (0, 0, 0)), (x - label_pad + 4, y - 8))
    for x, y in hid:
        pygame.draw.circle(scr, (0, 0, 0), (x, y), 5)

    pygame.draw.rect(scr, (255, 140, 0), (*outp[0], 10, 10))
    scr.blit(small.render("jump", True, (0, 0, 0)),
             (outp[0][0] - 30, outp[0][1] - 6))

# ---------- Main GA ----------
def run_ga(screen):
    global SIGMA, small
    clock = pygame.time.Clock()
    font  = pygame.font.SysFont(None, 22)
    small = pygame.font.SysFont(None, 16)

    env = FlappyEnv(shrink_gap=True)
    pop = [Bird() for _ in range(POP)]
    SIGMA = SIGMA_INIT
    gen = 0
    speed_idx = 0
    speed_r = pygame.Rect(FlappyEnv.WIN_W - 46, 6, 40, 24)
    base_x = anim = 0

    while True:
        env.reset(); [b.reset() for b in pop]; alive = POP
        while alive:
            for e in pygame.event.get():
                if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                    return
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and speed_r.collidepoint(e.pos):
                    speed_idx = (speed_idx + 1) % len(SPEEDS)

            dx, gy, g = env._state()[2:]
            stat = (dx/288, gy/512, g/160)

            alive = 0
            for b in pop:
                if not b.alive: continue
                if b.act(np.array([b.y/512, b.vy/10, *stat])):
                    b.vy = FlappyEnv.FLAP_VEL
                b.vy += FlappyEnv.GRAVITY; b.y += b.vy; b.t += 1

                for p in env.pipes:
                    if p["x"] + FlappyEnv.PIPE_W == 50:
                        b.score += 1

                hit = b.y<=0 or b.y>=FlappyEnv.GROUND_Y
                if not hit:
                    for p in env.pipes:
                        if 50 in range(int(p["x"]), int(p["x"]) + FlappyEnv.PIPE_W):
                            if not (p["top"] < b.y < p["top"] + p["gap"]):
                                hit = True; break
                b.alive = not hit
                if b.alive: alive += 1

            env.step(False)
            base_x = (base_x - FlappyEnv.PIPE_SPEED) % -FlappyEnv.base_w

            # --- Çizim ---
            screen.blit(FlappyEnv.bg_img, (0, 0))
            for p in env.pipes:
                screen.blit(FlappyEnv.pipe_up,   (p["x"], p["top"] - FlappyEnv.pipe_up.get_height()))
                screen.blit(FlappyEnv.pipe_down, (p["x"], p["top"] + p["gap"]))

            FlappyEnv.draw_base(screen, base_x)

            frame = FlappyEnv.bird_frames[(anim // 5) % 3]; anim += 1
            for b in pop:
                if b.alive:
                    screen.blit(frame, (46, b.y - 12))

            screen.blit(font.render(f"Gen {gen}", True, (0, 0, 0)), (5, 5))
            draw_num(screen, env.score_total)
            pygame.draw.rect(screen, (0, 0, 0), speed_r, 2)
            screen.blit(font.render(f"{1<<speed_idx}x", True, (0,0,0)),
                        speed_r.move(4,2))

            draw_network(screen, pop[0].g)
            pygame.display.flip()
            clock.tick(SPEEDS[speed_idx])

        # -------- Evolution (kısaltılmış) --------
        fit = [( (b.score**2)*40 + b.t/3 if not (b.score==0 and b.t<WEAK_TICKS) else 0, b)
               for b in pop]
        fit.sort(key=lambda x: x[0], reverse=True)
        elites = [b for _, b in fit[:HOF]]
        pool   = fit[:POP//30]

        new_pop = [Bird(e.g.copy()) for e in elites]
        while len(new_pop) < POP:
            new_pop.append(Bird(crossover(tournament(pool).g,
                                          tournament(pool).g, SIGMA)))
        pop = new_pop; gen += 1
