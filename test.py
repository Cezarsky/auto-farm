import time
import math
import minescript

# ===== USTAWIENIA =====
PLANT_AIM_Y = 1.12
PLANT_AIM_X_BIAS = 0.10
PLANT_AIM_Z_BIAS = 0.00

RADIUS = 3  # 7x7

LOOK_TICKS = 1
FARMLAND_Y_OFFSET = -1

MOVE_BLOCKS = 8.5
MOVE_TIME_PER_BLOCK = 0.17

SEED_ITEMS = {"minecraft:wheat_seeds"}
ALLOW_SWAP_FROM_INVENTORY = True

MIN_SEEDS_BEFORE_REFILL = 3
REFILL_COOLDOWN_SEC = 0.5
_last_refill_ts = 0.0

HOME_PREFIX = "farma"
home_counter = 1

ATTACK_TICKS = 2
HARVEST_PASSES_MAX = 3
HARVEST_MODE = "ALL_PLANTS"  # "MATURE_ONLY" albo "ALL_PLANTS"

# ===== NOWE: LOBBY LOGIC =====
BLACK_CONCRETE_ID = "minecraft:black_concrete"
LOBBY_WAIT_SECONDS = 45 * 60  # 45 minut

# ===== POMOCNICZE =====
def wait_one_tick():
    with minescript.tick_loop:
        pass

def aim_point_for_plant(x, fy, z):
    px, py, pz = minescript.player().position
    ax = x + (0.2 if px < x + 0.5 else 0.8)
    az = z + (0.2 if pz < z + 0.5 else 0.8)

    ax = max(x + 0.05, min(x + 0.95, ax + PLANT_AIM_X_BIAS))
    az = max(z + 0.05, min(z + 0.95, az + PLANT_AIM_Z_BIAS))

    ay = fy + PLANT_AIM_Y
    return ax, ay, az

def should_break_crop(block_id: str) -> bool:
    if not isinstance(block_id, str):
        return False
    if block_id.startswith("minecraft:air"):
        return False

    if HARVEST_MODE == "MATURE_ONLY":
        return block_id.startswith("minecraft:wheat") and "age=7" in block_id

    crops = (
        "minecraft:wheat",
        "minecraft:carrots",
        "minecraft:potatoes",
        "minecraft:beetroots",
        "minecraft:nether_wart",
    )
    return block_id.startswith(crops)

def get_center_block_floor():
    px, py, pz = minescript.player().position
    return math.floor(px), py, math.floor(pz)

def farmland_y(py):
    return round(py + FARMLAND_Y_OFFSET)

def aim_point_towards_player(x, fy, z):
    px, py, pz = minescript.player().position
    ax = x + (0.2 if px < x + 0.5 else 0.8)
    az = z + (0.2 if pz < z + 0.5 else 0.8)
    ay = fy + 1.0
    return ax, ay, az

def look_at(ax, ay, az, ticks=1):
    for _ in range(ticks):
        with minescript.tick_loop:
            minescript.player_look_at(ax, ay, az)

def use_once():
    with minescript.tick_loop:
        minescript.player_press_use(True)
    with minescript.tick_loop:
        minescript.player_press_use(False)

def attack_for_ticks(ticks=ATTACK_TICKS):
    for _ in range(ticks):
        with minescript.tick_loop:
            minescript.player_press_attack(True)
    with minescript.tick_loop:
        minescript.player_press_attack(False)

# ===== INVENTORY / SEEDS =====
def get_main_hand_count():
    hands = minescript.player_hand_items()
    mh = getattr(hands, "main_hand", None)
    return getattr(mh, "count", 0) if mh else 0

def get_main_hand_item_id():
    hands = minescript.player_hand_items()
    if hands is None:
        return None
    mh = getattr(hands, "main_hand", None)
    if mh is None:
        return None
    return getattr(mh, "item", None)

def find_seed_in_hotbar():
    inv = minescript.player_inventory()
    for it in inv:
        slot = getattr(it, "slot", None)
        item = getattr(it, "item", None)
        count = getattr(it, "count", 0)
        if slot is None or item is None:
            continue
        if 0 <= slot <= 8 and count > 0 and item in SEED_ITEMS:
            return slot
    return None

def find_seed_in_inventory_non_hotbar():
    inv = minescript.player_inventory()
    for it in inv:
        slot = getattr(it, "slot", None)
        item = getattr(it, "item", None)
        count = getattr(it, "count", 0)
        if slot is None or item is None:
            continue
        if slot >= 9 and count > 0 and item in SEED_ITEMS:
            return slot
    return None

def refill_seeds_to_hotbar_if_needed():
    global _last_refill_ts
    now = time.time()

    held_item = get_main_hand_item_id()
    held_count = get_main_hand_count()

    if held_item in SEED_ITEMS and held_count > MIN_SEEDS_BEFORE_REFILL:
        return True

    if held_count > 0 and (now - _last_refill_ts) < REFILL_COOLDOWN_SEC:
        return True

    hotbar_slot = find_seed_in_hotbar()
    if hotbar_slot is not None:
        with minescript.tick_loop:
            minescript.player_inventory_select_slot(hotbar_slot)
        wait_one_tick()
        _last_refill_ts = now
        return (get_main_hand_item_id() in SEED_ITEMS and get_main_hand_count() > 0)

    if ALLOW_SWAP_FROM_INVENTORY:
        inv_slot = find_seed_in_inventory_non_hotbar()
        if inv_slot is not None:
            with minescript.tick_loop:
                swapped_to = minescript.player_inventory_slot_to_hotbar(inv_slot)
                minescript.player_inventory_select_slot(swapped_to)
            wait_one_tick()
            _last_refill_ts = now
            return (get_main_hand_item_id() in SEED_ITEMS and get_main_hand_count() > 0)

    _last_refill_ts = now
    return False

# ===== CHECKERS / BLOCKS =====
def block_under_player():
    px, py, pz = minescript.player().position
    bx = math.floor(px)
    bz = math.floor(pz)
    by = math.floor(py) - 1
    return minescript.getblock(bx, by, bz)

def every_10_cycles_commands(cycle):
    if cycle % 10 != 0:
        return
    with minescript.tick_loop:
        minescript.execute("/bloki")
    time.sleep(0.3)
    with minescript.tick_loop:
        minescript.execute("/sellall")
    time.sleep(0.3)
    with minescript.tick_loop:
        minescript.chat("&c ===  &6 Darmowa Zarabiarka /is warp BestPlayerKrul &c ===")
    time.sleep(0.3)

def check_red_concrete_and_home():
    global home_counter
    block = block_under_player()
    if isinstance(block, str) and block.startswith("minecraft:red_concrete"):
        cmd = f"/home {HOME_PREFIX}{home_counter}"
        with minescript.tick_loop:
            minescript.execute(cmd)
        home_counter += 1
        time.sleep(0.2)

# ===== HARVEST CHECKER =====
def count_breakable_crops(cx, fy, cz):
    cnt = 0
    for dx in range(-RADIUS, RADIUS + 1):
        for dz in range(-RADIUS, RADIUS + 1):
            x = cx + dx
            z = cz + dz
            if not minescript.getblock(x, fy, z).startswith("minecraft:farmland"):
                continue
            above = minescript.getblock(x, fy + 1, z)
            if should_break_crop(above):
                cnt += 1
    return cnt

def harvest_pass(cx, fy, cz):
    harvested = 0
    for dx in range(-RADIUS, RADIUS + 1):
        for dz in range(-RADIUS, RADIUS + 1):
            x = cx + dx
            z = cz + dz

            if not minescript.getblock(x, fy, z).startswith("minecraft:farmland"):
                continue

            above = minescript.getblock(x, fy + 1, z)
            if should_break_crop(above):
                ax, ay, az = aim_point_towards_player(x, fy, z)
                look_at(ax, ay, az, LOOK_TICKS)
                wait_one_tick()
                attack_for_ticks(ATTACK_TICKS)
                harvested += 1
                time.sleep(0.02)
    return harvested

# ===== LOGIKA FARMY =====
def harvest_then_plant_area(cx, cy, cz):
    fy = farmland_y(cy)
    harvested = 0
    planted = 0

    # --- ZBIÓR Z CHECKEREM ---
    for _ in range(HARVEST_PASSES_MAX):
        remaining = count_breakable_crops(cx, fy, cz)
        if remaining == 0:
            break
        got = harvest_pass(cx, fy, cz)
        harvested += got
        if got == 0:
            break

    # --- ZASIEW ---
    for dx in range(-RADIUS, RADIUS + 1):
        for dz in range(-RADIUS, RADIUS + 1):
            x = cx + dx
            z = cz + dz

            if not minescript.getblock(x, fy, z).startswith("minecraft:farmland"):
                continue

            above = minescript.getblock(x, fy + 1, z)
            if above.startswith("minecraft:air"):
                ok = refill_seeds_to_hotbar_if_needed()
                if not ok:
                    return harvested, planted, True  # out_of_seeds=True

                ax, ay, az = aim_point_for_plant(x, fy, z)
                look_at(ax, ay, az, LOOK_TICKS)
                use_once()
                planted += 1

    return harvested, planted, False

def finish_cycle():
    with minescript.tick_loop:
        minescript.player_set_orientation(-90, 0)

    with minescript.tick_loop:
        minescript.player_press_forward(True)
    time.sleep(MOVE_BLOCKS * MOVE_TIME_PER_BLOCK)
    with minescript.tick_loop:
        minescript.player_press_forward(False)

# ===== NOWE: BLACK CONCRETE => LOBBY WAIT => FARMA =====
def on_black_concrete_go_lobby_wait_then_farma():
    """
    Jeśli stoisz na black_concrete:
    - /home lobby
    - czekaj 45 min
    - /home farma
    """
    block = block_under_player()
    if isinstance(block, str) and block.startswith(BLACK_CONCRETE_ID):
        with minescript.tick_loop:
            minescript.execute("/home lobby")
        # krótkie "złapanie" teleportu
        time.sleep(2.0)

        # czekaj 45 minut (w małych krokach, żeby nie zamrozić gry kompletnie)
        end_ts = time.time() + LOBBY_WAIT_SECONDS
        while time.time() < end_ts:
            time.sleep(5.0)

        with minescript.tick_loop:
            minescript.execute("/home farma")
        time.sleep(2.0)
        return True

    return False

# ===== MAIN LOOP (LINUX SAFE) =====
def main():
    print("Bot started (Linux safe). Stop: Ctrl+C")

    enabled = True  # startuje od razu; po black_concrete wróci sam na /home farma i będzie działał
    cycle = 0

    while True:
        # 1) Priorytet: jeśli jesteś na black_concrete -> lobby wait -> farma
        # Po powrocie kontynuujemy farmienie.
        if on_black_concrete_go_lobby_wait_then_farma():
            enabled = True
            continue

        if enabled:
            cycle += 1
            cx, cy, cz = get_center_block_floor()
            harvested, planted, out_of_seeds = harvest_then_plant_area(cx, cy, cz)

            print(f"[Cycle {cycle}] harvested={harvested} | planted={planted} | out_of_seeds={out_of_seeds}")

            if not out_of_seeds:
                finish_cycle()
                check_red_concrete_and_home()
                every_10_cycles_commands(cycle)
            else:
                # brak seeds -> czekaj i próbuj w tym samym miejscu
                time.sleep(0.5)
                continue

        time.sleep(0.1)

if __name__ == "__main__":
    main()
