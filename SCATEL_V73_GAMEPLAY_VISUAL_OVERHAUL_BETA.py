import pygame, sys, random, math, socket, threading, json, time, base64, zlib, os
from datetime import date

pygame.init()

AUDIO_OK = True
try:
    pygame.mixer.init()
except pygame.error as e:
    AUDIO_OK = False
    print("Audio desactivado:", e)

BASE_ANCHO, BASE_ALTO = 800, 600
ANCHO, ALTO = 1280, 720
HD_VISUAL_SCALE = min(ANCHO / BASE_ANCHO, ALTO / BASE_ALTO)
HD_WIDE_OFFSET = (ANCHO - int(BASE_ANCHO * HD_VISUAL_SCALE)) // 2
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ASSET_SEARCH_DIRS = [
    "",
    os.path.join("assets", "images", "backgrounds"),
    os.path.join("assets", "images", "ships"),
    os.path.join("assets", "images", "bosses"),
    os.path.join("assets", "images", "enemies"),
    os.path.join("assets", "images", "projectiles"),
    os.path.join("assets", "images", "planets"),
    os.path.join("assets", "images", "pickups_and_ui"),
    os.path.join("assets", "images", "hazards"),
    os.path.join("assets", "images", "loot"),
    os.path.join("assets", "images", "cockpit"),
    os.path.join("assets", "images", "cards"),
    os.path.join("assets", "music", "new_soundtrack"),
    os.path.join("assets", "music", "legacy"),
    os.path.join("assets", "sfx", "weapons"),
    os.path.join("assets", "sfx", "bosses"),
    os.path.join("assets", "sfx", "cockpit"),
    os.path.join("assets", "sfx", "movement"),
    os.path.join("assets", "sfx", "impacts"),
    os.path.join("assets", "sfx", "pickups"),
    os.path.join("assets", "sfx", "anomalies"),
    os.path.join("asset_concepts_v69", "assets_individuales_xfondos"),
    os.path.join("SCATEL_V59_ASSET_WORKSPACE", "assets", "sprites", "planets"),
]

def ruta_recurso(nombre):
    nombre = str(nombre)
    if os.path.isabs(nombre):
        return nombre
    directa = os.path.join(BASE_DIR, nombre)
    if os.path.exists(directa):
        return directa
    normalizado = nombre.replace("\\", os.sep).replace("/", os.sep)
    for carpeta in ASSET_SEARCH_DIRS:
        candidato = os.path.join(BASE_DIR, carpeta, normalizado)
        if os.path.exists(candidato):
            return candidato
    return directa

# =====================
# RESOLUCION INTERNA Y PANTALLA COMPLETA
# =====================
# V72: el juego se dibuja en una base HD 16:9.
# La ventana sigue siendo redimensionable y conserva proporcion sin deformar.
fullscreen = False
ventana = pygame.display.set_mode((ANCHO, ALTO), pygame.RESIZABLE)
pygame.display.set_caption("ScaleTale - V73 Gameplay Visual Overhaul Beta")

pantalla = pygame.Surface((ANCHO, ALTO))

escala_pantalla = 1
offset_pantalla_x = 0
offset_pantalla_y = 0
ancho_escalado = ANCHO
alto_escalado = ALTO

# Ajustes rapidos de gameplay: cambia estos valores si quieres retocar velocidad o escudo.
PLAYER_SPEED_NORMAL = 9.1
PLAYER_SPEED_SLOWED = 6.8
PLAYER_BULLET_SPEED = 15
SHIELD_RADIUS_MAIN = 42
SHIELD_RADIUS_COOP = 36

def hd_size(tamano):
    if not isinstance(tamano, (tuple, list)) or len(tamano) != 2:
        return tamano
    w, h = tamano
    if w >= ANCHO * 0.75 or h >= ALTO * 0.75:
        return (int(w), int(h))
    return (max(1, int(w * HD_VISUAL_SCALE)), max(1, int(h * HD_VISUAL_SCALE)))

def hd_rect(x, y, w, h):
    return pygame.Rect(
        int(x * HD_VISUAL_SCALE + HD_WIDE_OFFSET),
        int(y * HD_VISUAL_SCALE),
        int(w * HD_VISUAL_SCALE),
        int(h * HD_VISUAL_SCALE)
    )

def actualizar_escalado():
    global escala_pantalla, offset_pantalla_x, offset_pantalla_y, ancho_escalado, alto_escalado

    ventana_ancho, ventana_alto = ventana.get_size()

    escala_pantalla = min(
        ventana_ancho / ANCHO,
        ventana_alto / ALTO
    )

    ancho_escalado = int(ANCHO * escala_pantalla)
    alto_escalado = int(ALTO * escala_pantalla)

    offset_pantalla_x = (ventana_ancho - ancho_escalado) // 2
    offset_pantalla_y = (ventana_alto - alto_escalado) // 2

def presentar_frame():
    actualizar_escalado()

    ventana.fill((0,0,0))

    frame_escalado = pygame.transform.smoothscale(
        pantalla,
        (
            ancho_escalado,
            alto_escalado
        )
    )

    ventana.blit(
        frame_escalado,
        (
            offset_pantalla_x,
            offset_pantalla_y
        )
    )

    pygame.display.flip()

def convertir_pos_mouse(pos):
    actualizar_escalado()

    x = int((pos[0] - offset_pantalla_x) / escala_pantalla)
    y = int((pos[1] - offset_pantalla_y) / escala_pantalla)

    return (
        max(0, min(ANCHO, x)),
        max(0, min(ALTO, y))
    )

def alternar_pantalla_completa():
    global ventana, fullscreen

    fullscreen = not fullscreen

    if fullscreen:
        ventana = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
    else:
        ventana = pygame.display.set_mode((ANCHO, ALTO), pygame.RESIZABLE)

    actualizar_escalado()

actualizar_escalado()

clock = pygame.time.Clock()

BLANCO = (255,255,255)
ROJO = (255,60,60)
NEGRO = (0,0,0)

fuente = pygame.font.SysFont(None,30)
fuente_peq = pygame.font.SysFont(None,22)

# =====================
# IDIOMA
# =====================
idioma_actual = "ES"
dificultad_actual = "facil"
multijugador_actual = "solo"
musica_volumen = 0.5

# =====================
# ONLINE LAN EXPERIMENTAL
# =====================
NET_PORT = 50555
net_role = "none"          # none / host / client
net_server = None
net_conn = None
net_client = None
net_connected = False
net_thread_running = False
net_status = ""
net_join_ip = ""
net_remote_inputs = {}
net_client_snapshot = None
net_client_frame_raw = None
net_client_frame_id = 0
net_last_frame_sent = 0
net_frame_interval = 1/24
net_lock = threading.Lock()


TEXTOS = {
    "ES": {
        "start":"JUGAR",
        "ships":"NAVES",
        "controls":"TECLAS",
        "language":"IDIOMA",
        "quit":"SALIR",
        "back":"VOLVER",
        "selected":"SELECCIONADA",
        "select_ship":"SELECCIONA TU NAVE",
        "choose_fighter":"Elige tu nave ScaleTale",
        "controls_title":"CONTROLES",
        "language_title":"IDIOMA",
        "spanish":"ESPANOL",
        "english":"INGLES",
        "move":"Mover nave",
        "shoot":"Disparar",
        "dash":"Dash energetico",
        "laser":"Superlaser",
        "pulse":"Bomba de pulso",
        "overdrive":"Ultimate Overdrive",
        "blackhole":"Ultimate Agujero Negro",
        "orbital":"Ultimate Ataque Orbital",
        "boss_only":"Solo durante boss fights",
        "debug":"Debug / pruebas",
        "click_to_change":"Haz clic en una accion para cambiar su tecla",
        "press_new_key":"Pulsa una nueva tecla para",
        "reset_keys":"RESTABLECER",
        "keys_reset":"Teclas restablecidas",
        "shop":"TIENDA",
        "coins":"MONEDAS",
        "buy":"COMPRAR",
        "equip":"EQUIPAR",
        "equipped":"EQUIPADA",
        "owned":"COMPRADA",
        "not_enough":"NO HAY MONEDAS SUFICIENTES",
        "purchased":"COMPRA REALIZADA",
        "skins":"NAVES",
        "abilities":"HABILIDADES",
        "triple_shot":"Triple Shot",
        "auto_shield":"Auto Shield",
        "energy_core":"Energy Core",
        "crimson":"Crimson Wing",
        "nova":"Nova Star",
        "phantom":"Phantom X",
        "eclipse":"Eclipse Viper",
        "aurora":"Aurora Blade",
        "quantum":"Quantum Wraith",
        "coin_booster":"Coin Booster",
        "revive_core":"Revive Core",
        "ultimate_core":"Ultimate Core",
        "info":"INFO",
        "difficulty":"DIFICULTAD",
        "profile":"PERFIL",
        "missions":"MISIONES",
        "achievements":"LOGROS",
        "upgrades":"MEJORAS",
        "daily":"DIARIAS",
        "codex":"CODEX",
        "profile_title":"PERFIL DEL PILOTO",
        "missions_title":"MISIONES",
        "codex_title":"CODEX / GALERIA",
        "best_score":"Mejor puntuacion",
        "games_played":"Partidas jugadas",
        "enemies_destroyed":"Enemigos destruidos",
        "bosses_defeated":"Bosses derrotados",
        "coins_earned":"Monedas ganadas",
        "ships_owned":"Naves compradas",
        "abilities_owned":"Habilidades compradas",
        "mission_1":"Destruye 50 enemigos",
        "mission_2":"Consigue 100.000 puntos",
        "mission_3":"Derrota un boss",
        "mission_4":"Gana 25.000 monedas",
        "reward":"Recompensa",
        "claim":"RECLAMAR",
        "completed":"COMPLETADA",
        "claimed":"RECLAMADA",
        "progress":"Progreso",
        "enemy_codex":"ENEMIGOS",
        "boss_codex":"BOSSES",
        "ship_codex":"NAVES",
        "ability_codex":"HABILIDADES",
        "codex_hint":"Consulta los elementos principales descubiertos en ScaleTale.",
        "difficulty_title":"SELECCIONA DIFICULTAD",
        "game_mode":"MODO DE JUEGO",
        "solo":"SOLITARIO",
        "local_coop":"COOP LOCAL",
        "online_host":"HOST LAN",
        "online_join":"UNIRSE LAN",
        "online_title":"MULTIJUGADOR LAN",
        "host_desc":"Crea una partida en tu red local. Comparte tu IP con tu amigo.",
        "join_desc":"Unete a una partida LAN escribiendo la IP del host.",
        "online_code":"CODIGO / IP",
        "online_waiting":"Esperando jugador 2...",
        "online_connected":"Jugador conectado",
        "online_join_prompt":"Escribe la IP del host y pulsa ENTER",
        "online_joining":"Conectando...",
        "online_failed":"No se pudo conectar",
        "online_client":"Conectado como Jugador 2",
        "online_start_hint":"Host: pulsa JUGAR para crear sala. Cliente: escribe IP y ENTER.",
        "host_lobby":"SALA LAN DEL HOST",
        "host_lobby_wait":"Comparte esta IP con tu amigo. La partida no empezara hasta que se conecte.",
        "host_lobby_ready":"Jugador 2 conectado. Pulsa ENTER para empezar.",
        "cancel":"CANCELAR",
        "solo_desc":"Una sola nave. Experiencia clasica.",
        "coop_desc":"Dos jugadores en la misma pantalla. Naves mas compactas y vidas compartidas.",
        "p2_controls":"Jugador 2: IJKL mover / CTRL derecho disparar",
        "player1":"JUGADOR 1",
        "player2":"JUGADOR 2",
        "p2_dash":"Dash J2",
        "p2_laser":"Laser J2",
        "p2_pulse":"Pulso J2",
        "p2_overdrive":"Overdrive J2",
        "p2_blackhole":"Agujero Negro J2",
        "p2_orbital":"Orbital J2",
        "easy":"FACIL",
        "normal_mode":"NORMAL",
        "hard":"DIFICIL",
        "very_hard":"MUY DIFICIL",
        "easy_desc":"Experiencia original de ScaleTale. Todas las habilidades estan disponibles.",
        "normal_desc":"Ultimate Overdrive queda desactivado para una experiencia mas equilibrada.",
        "hard_desc":"Todas las habilidades Ultimate de boss fight quedan desactivadas.",
        "very_hard_desc":"Modo dificil + los enemigos y bosses infligen un 10% mas de dano.",
        "current_difficulty":"DIFICULTAD ACTUAL",
        "privacy_updates":"PRIVACIDAD / ACTUALIZACIONES",
        "privacy":"PRIVACIDAD",
        "updates":"ACTUALIZACIONES",
        "privacy_text":"ScaleTale no recopila datos personales, no requiere inicio de sesion, no envia informacion a servidores externos y no utiliza anuncios ni seguimiento. El progreso del jugador, monedas, naves compradas y habilidades desbloqueadas se guardan localmente en el archivo scaletale_save.json dentro de la carpeta del juego. El usuario puede eliminar ese archivo para borrar su progreso.",
        "updates_text":"Version 59 Graphics Engine Rework: anade motor visual con postprocesado, color grading por nivel, bloom falso, vinetas, luces dinamicas, particulas de energia y presentacion grafica mas cinematica.",
        "achievements_title":"LOGROS",
        "upgrades_title":"MEJORAS PERMANENTES",
        "daily_title":"MISIONES DIARIAS",
        "upgrade_hp":"Blindaje",
        "upgrade_cooldown":"Reactor",
        "upgrade_coin":"Contrato",
        "level_label":"Nivel",
        "maxed":"MAX",
        "daily_reset":"Se renuevan cada 24 horas",
        "hp":"VIDA",
        "score":"PUNTOS",
        "level":"NIVEL",
        "ready":"LISTO",
        "ultimate_boss_only":"ULTIMATE SOLO EN BOSS FIGHT",
        "overdrive_activated":"OVERDRIVE ACTIVADO",
        "black_hole":"AGUJERO NEGRO",
        "orbital_strike":"ATAQUE ORBITAL",
        "subtitle":"Cinematic Arcade Shooter",
        "help":"WASD MOVER  |  FLECHA ARRIBA DISPARAR  |  SHIFT / ESPACIO / E HABILIDADES"
    },
    "EN": {
        "start":"START",
        "ships":"SHIPS",
        "controls":"KEYS",
        "language":"LANGUAGE",
        "quit":"QUIT",
        "back":"BACK",
        "selected":"SELECTED",
        "select_ship":"SELECT YOUR SHIP",
        "choose_fighter":"Choose your ScaleTale fighter",
        "controls_title":"CONTROLS",
        "language_title":"LANGUAGE",
        "spanish":"SPANISH",
        "english":"ENGLISH",
        "move":"Move ship",
        "shoot":"Shoot",
        "dash":"Energy dash",
        "laser":"Super laser",
        "pulse":"Pulse bomb",
        "overdrive":"Ultimate Overdrive",
        "blackhole":"Ultimate Black Hole",
        "orbital":"Ultimate Orbital Strike",
        "boss_only":"Only during boss fights",
        "debug":"Debug / testing",
        "click_to_change":"Click an action to change its key",
        "press_new_key":"Press a new key for",
        "reset_keys":"RESET",
        "keys_reset":"Keys restored",
        "shop":"SHOP",
        "coins":"COINS",
        "buy":"BUY",
        "equip":"EQUIP",
        "equipped":"EQUIPPED",
        "owned":"OWNED",
        "not_enough":"NOT ENOUGH COINS",
        "purchased":"PURCHASED",
        "skins":"SHIPS",
        "abilities":"ABILITIES",
        "triple_shot":"Triple Shot",
        "auto_shield":"Auto Shield",
        "energy_core":"Energy Core",
        "crimson":"Crimson Wing",
        "nova":"Nova Star",
        "phantom":"Phantom X",
        "eclipse":"Eclipse Viper",
        "aurora":"Aurora Blade",
        "quantum":"Quantum Wraith",
        "coin_booster":"Coin Booster",
        "revive_core":"Revive Core",
        "ultimate_core":"Ultimate Core",
        "info":"INFO",
        "difficulty":"DIFFICULTY",
        "profile":"PROFILE",
        "missions":"MISSIONS",
        "achievements":"ACHIEVEMENTS",
        "upgrades":"UPGRADES",
        "daily":"DAILY",
        "codex":"CODEX",
        "profile_title":"PILOT PROFILE",
        "missions_title":"MISSIONS",
        "codex_title":"CODEX / GALLERY",
        "best_score":"Best score",
        "games_played":"Games played",
        "enemies_destroyed":"Enemies destroyed",
        "bosses_defeated":"Bosses defeated",
        "coins_earned":"Coins earned",
        "ships_owned":"Ships owned",
        "abilities_owned":"Abilities owned",
        "mission_1":"Destroy 50 enemies",
        "mission_2":"Reach 100,000 score",
        "mission_3":"Defeat one boss",
        "mission_4":"Earn 25,000 coins",
        "reward":"Reward",
        "claim":"CLAIM",
        "completed":"COMPLETED",
        "claimed":"CLAIMED",
        "progress":"Progress",
        "enemy_codex":"ENEMIES",
        "boss_codex":"BOSSES",
        "ship_codex":"SHIPS",
        "ability_codex":"ABILITIES",
        "codex_hint":"Review the main elements discovered in ScaleTale.",
        "difficulty_title":"SELECT DIFFICULTY",
        "game_mode":"GAME MODE",
        "solo":"SOLO",
        "local_coop":"LOCAL COOP","online_host":"HOST LAN","online_join":"JOIN LAN","online_title":"LAN MULTIPLAYER","host_desc":"Create a match on your local network. Share your IP with your friend.","join_desc":"Join a LAN match by typing the host IP.","online_code":"CODE / IP","online_waiting":"Waiting for Player 2...","online_connected":"Player connected","online_join_prompt":"Type host IP and press ENTER","online_joining":"Connecting...","online_failed":"Could not connect","online_client":"Connected as Player 2","online_start_hint":"Host: press PLAY to create room. Client: type IP and ENTER.","host_lobby":"HOST LAN LOBBY","host_lobby_wait":"Share this IP with your friend. The game will not start until they connect.","host_lobby_ready":"Player 2 connected. Press ENTER to start.","cancel":"CANCEL",
        "solo_desc":"One ship. Classic experience.",
        "coop_desc":"Two players on the same screen. Smaller ships and shared lives.",
        "p2_controls":"Player 2: IJKL move / Right CTRL shoot","player1":"PLAYER 1","player2":"PLAYER 2","p2_dash":"Dash P2","p2_laser":"Laser P2","p2_pulse":"Pulse P2","p2_overdrive":"Overdrive P2","p2_blackhole":"Black Hole P2","p2_orbital":"Orbital P2",
        "easy":"EASY",
        "normal_mode":"NORMAL",
        "hard":"HARD",
        "very_hard":"VERY HARD",
        "easy_desc":"Original ScaleTale experience. All abilities are available.",
        "normal_desc":"Ultimate Overdrive is disabled for a more balanced experience.",
        "hard_desc":"All boss fight Ultimate abilities are disabled.",
        "very_hard_desc":"Hard mode + enemies and bosses deal 10% more damage.",
        "current_difficulty":"CURRENT DIFFICULTY",
        "privacy_updates":"PRIVACY / UPDATES",
        "privacy":"PRIVACY",
        "updates":"UPDATES",
        "privacy_text":"ScaleTale does not collect personal data, does not require login, does not send information to external servers, and does not use ads or tracking. Player progress, coins, purchased ships, and unlocked abilities are stored locally in the scaletale_save.json file inside the game folder. The user may delete that file to erase their progress.",
        "updates_text":"Version 59 Graphics Engine Rework: adds a visual engine with post-processing, level color grading, fake bloom, vignettes, dynamic lights, energy particles, and a more cinematic presentation.",
        "achievements_title":"ACHIEVEMENTS",
        "upgrades_title":"PERMANENT UPGRADES",
        "daily_title":"DAILY MISSIONS",
        "upgrade_hp":"Armor",
        "upgrade_cooldown":"Reactor",
        "upgrade_coin":"Contract",
        "level_label":"Level",
        "maxed":"MAX",
        "daily_reset":"Refreshes every 24 hours",
        "hp":"HP","score":"SCORE",
        "level":"LEVEL",
        "ready":"READY",
        "ultimate_boss_only":"ULTIMATE ONLY IN BOSS FIGHT",
        "overdrive_activated":"OVERDRIVE ACTIVATED",
        "black_hole":"BLACK HOLE",
        "orbital_strike":"ORBITAL STRIKE",
        "subtitle":"Cinematic Arcade Shooter",
        "help":"WASD MOVE  |  UP ARROW SHOOT  |  SHIFT / SPACE / E ABILITIES"
    }
}

def txt(clave):
    return TEXTOS.get(idioma_actual, TEXTOS["ES"]).get(clave, clave)

# =====================
# CONTROLES CONFIGURABLES
# =====================
def controles_por_defecto():
    return {
        "move_up":pygame.K_w,
        "move_left":pygame.K_a,
        "move_down":pygame.K_s,
        "move_right":pygame.K_d,
        "shoot":pygame.K_UP,
        "dash":pygame.K_LSHIFT,
        "special_laser":pygame.K_SPACE,
        "pulse":pygame.K_e,
        "ultimate_overdrive":pygame.K_q,
        "ultimate_blackhole":pygame.K_r,
        "ultimate_orbital":pygame.K_t,

        # Jugador 2 - coop local
        "p2_move_up":pygame.K_i,
        "p2_move_left":pygame.K_j,
        "p2_move_down":pygame.K_k,
        "p2_move_right":pygame.K_l,
        "p2_shoot":pygame.K_RCTRL,
        "p2_dash":pygame.K_RSHIFT,
        "p2_special_laser":pygame.K_RETURN,
        "p2_pulse":pygame.K_RALT,
        "p2_ultimate_overdrive":pygame.K_u,
        "p2_ultimate_blackhole":pygame.K_o,
        "p2_ultimate_orbital":pygame.K_p
    }

controles = controles_por_defecto()
accion_reasignando = None
mensaje_controles = 0
mensaje_controles_texto = ""

def nombre_tecla(tecla):
    try:
        return pygame.key.name(tecla).upper()
    except:
        return str(tecla)

def tecla_pulsada(teclas, accion):
    codigo = controles.get(accion)
    if codigo is None:
        return False

    # Soporte para shift izquierdo/derecho si se asigna shift.
    if accion in ["dash","p2_dash"]:
        if codigo in [pygame.K_LSHIFT, pygame.K_RSHIFT]:
            return teclas[pygame.K_LSHIFT] or teclas[pygame.K_RSHIFT]

    return teclas[codigo]

# =====================
# SISTEMA DE TIENDA Y MONEDAS
# =====================
SAVE_FILE = ruta_recurso("scaletale_save.json")

monedas = 0
shop_message = 0
shop_message_text = ""

owned_ships = {1,2}
owned_abilities = set()

# =====================
# PERFIL, ESTADISTICAS Y MISIONES
# =====================
stats = {
    "best_score":0,
    "games_played":0,
    "enemies_destroyed":0,
    "bosses_defeated":0,
    "coins_earned":0,
    "scale0_unlocked":0,
    "scale0_fragments":0,
    "scale0_runs":0,
    "planet_missions_done":0
}

build_seleccionada = "balanced"
relics_scale0 = set()

BUILD_DEFS = {
    "balanced":{"name":"BALANCED","name_es":"EQUILIBRIO","desc":"Todo terreno.","desc_es":"Todo terreno."},
    "assault":{"name":"ASSAULT","name_es":"ASALTO","desc":"+damage tempo, less safety.","desc_es":"Mas ritmo ofensivo, menos seguridad."},
    "guardian":{"name":"GUARDIAN","name_es":"GUARDIAN","desc":"Starts protected.","desc_es":"Empieza protegido."},
    "anomaly":{"name":"ANOMALY","name_es":"ANOMALIA","desc":"Better Scale-0 rewards.","desc_es":"Mejores recompensas de Scale-0."}
}

PLANET_MISSION_PROGRESS = {
    "score":0,
    "kills":0,
    "claimed_planet":""
}

mission_claimed = {
    "destroy_50":False,
    "score_100k":False,
    "boss_1":False,
    "coins_25k":False
}

achievement_claimed = set()

permanent_upgrades = {
    "hp":0,
    "cooldown":0,
    "coin":0
}

daily_state = {
    "date":"",
    "reset_at":0,
    "base":{},
    "claimed":{}
}

ACHIEVEMENTS = {
    "first_boss":{"name":"Primer comandante","desc":"Derrota 1 boss","stat":"bosses_defeated","goal":1,"reward":25000},
    "hunter_250":{"name":"Cazador espacial","desc":"Destruye 250 enemigos","stat":"enemies_destroyed","goal":250,"reward":35000},
    "score_500k":{"name":"Piloto elite","desc":"Alcanza 500.000 puntos","stat":"best_score","goal":500000,"reward":50000},
    "rift_5":{"name":"Rompe grietas","desc":"Derrota 5 bosses","stat":"bosses_defeated","goal":5,"reward":85000},
    "millionaire":{"name":"Magnate cosmico","desc":"Gana 1.000.000 monedas","stat":"coins_earned","goal":1000000,"reward":120000}
}

UPGRADE_DEFS = {
    "hp":{"name_key":"upgrade_hp","desc":"+20 HP maximo por nivel","base_cost":65000,"max":5},
    "cooldown":{"name_key":"upgrade_cooldown","desc":"Cooldowns y disparo mas rapidos","base_cost":90000,"max":5},
    "coin":{"name_key":"upgrade_coin","desc":"+10% monedas por nivel","base_cost":80000,"max":5}
}

DAILY_MISSION_POOL = {
    "daily_kills":{"name":"Destruye enemigos","stat":"enemies_destroyed","goal":80,"reward":18000},
    "daily_score":{"name":"Suma puntos","stat":"best_score","goal":150000,"reward":22000},
    "daily_boss":{"name":"Caza un boss","stat":"bosses_defeated","goal":1,"reward":30000},
    "daily_coins":{"name":"Gana monedas","stat":"coins_earned","goal":40000,"reward":20000}
}

run_counted = False
progreso_pendiente = False
ultimo_autoguardado = 0

SHIP_PRICES = {
    3:30000,
    4:60000,
    5:90000,
    6:150000,
    7:230000,
    8:320000
}

SHIP_NAMES = {
    1:"Blue Fighter",
    2:"White Falcon",
    3:"Crimson Wing",
    4:"Nova Star",
    5:"Phantom X",
    6:"Eclipse Viper",
    7:"Aurora Blade",
    8:"Quantum Wraith"
}

ABILITY_PRICES = {
    "triple_shot":200000,
    "auto_shield":300000,
    "energy_core":400000,
    "coin_booster":500000,
    "revive_core":650000,
    "ultimate_core":800000
}

ABILITY_NAMES = {
    "triple_shot":"Triple Shot",
    "auto_shield":"Auto Shield",
    "energy_core":"Energy Core",
    "coin_booster":"Coin Booster",
    "revive_core":"Revive Core",
    "ultimate_core":"Ultimate Core"
}

def cargar_progreso():
    global monedas, owned_ships, owned_abilities, nave_seleccionada, planeta_seleccionado, planet_selector_index, dificultad_actual, multijugador_actual, idioma_actual, musica_volumen, controles, stats, mission_claimed, achievement_claimed, permanent_upgrades, daily_state, build_seleccionada, relics_scale0
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE,"r",encoding="utf-8") as f:
                data=json.load(f)
            monedas=int(data.get("monedas",0))
            owned_ships=set(data.get("owned_ships",[1,2]))
            owned_abilities=set(data.get("owned_abilities",[]))
            nave_seleccionada=int(data.get("nave_seleccionada",1))
            if nave_seleccionada not in owned_ships:
                nave_seleccionada=1

            dificultad_actual = data.get("dificultad_actual","facil")
            if dificultad_actual not in ["facil","normal","dificil","muy_dificil"]:
                dificultad_actual = "facil"

            multijugador_actual = data.get("multijugador_actual","solo")
            if multijugador_actual not in ["solo","coop","online_host","online_join"]:
                multijugador_actual = "solo"

            idioma_actual = data.get("idioma_actual", idioma_actual)
            if idioma_actual not in TEXTOS:
                idioma_actual = "ES"

            try:
                musica_volumen = max(0.0, min(1.0, float(data.get("musica_volumen", musica_volumen))))
            except (TypeError, ValueError):
                musica_volumen = 0.5

            controles_guardados = data.get("controles",{})
            if isinstance(controles_guardados, dict):
                controles_base = controles_por_defecto()
                for accion, tecla in controles_guardados.items():
                    if accion in controles_base:
                        try:
                            controles_base[accion] = int(tecla)
                        except (TypeError, ValueError):
                            pass
                controles = controles_base

            stats_guardadas = data.get("stats",{})
            for clave in stats:
                stats[clave] = int(stats_guardadas.get(clave, stats[clave]))

            build_seleccionada = data.get("build_seleccionada", build_seleccionada)
            if build_seleccionada not in BUILD_DEFS:
                build_seleccionada = "balanced"
            relics_scale0 = set(data.get("relics_scale0",[]))

            planeta_guardado = data.get("planeta_seleccionado","ares_prime")
            if any(p["id"] == planeta_guardado for p in PLANET_DEFS) and planeta_desbloqueado(planeta_guardado):
                planeta_seleccionado = planeta_guardado
            else:
                planeta_seleccionado = "ares_prime"
            planet_selector_index = indice_planeta(planeta_seleccionado)

            misiones_guardadas = data.get("mission_claimed",{})
            for clave in mission_claimed:
                mission_claimed[clave] = bool(misiones_guardadas.get(clave, mission_claimed[clave]))

            achievement_claimed = set(data.get("achievement_claimed",[]))

            mejoras_guardadas = data.get("permanent_upgrades",{})
            if isinstance(mejoras_guardadas, dict):
                for clave in permanent_upgrades:
                    permanent_upgrades[clave] = max(0, min(UPGRADE_DEFS[clave]["max"], int(mejoras_guardadas.get(clave, permanent_upgrades[clave]))))

            daily_guardado = data.get("daily_state",{})
            if isinstance(daily_guardado, dict):
                daily_state["date"] = str(daily_guardado.get("date",""))
                daily_state["reset_at"] = float(daily_guardado.get("reset_at",0))
                daily_state["base"] = daily_guardado.get("base",{}) if isinstance(daily_guardado.get("base",{}), dict) else {}
                daily_state["claimed"] = daily_guardado.get("claimed",{}) if isinstance(daily_guardado.get("claimed",{}), dict) else {}
    except Exception as e:
        print("No se pudo cargar progreso:", e)

def guardar_progreso():
    global progreso_pendiente, ultimo_autoguardado
    try:
        data={
            "monedas":monedas,
            "owned_ships":list(owned_ships),
            "owned_abilities":list(owned_abilities),
            "nave_seleccionada":nave_seleccionada,
            "planeta_seleccionado":planeta_seleccionado,
            "dificultad_actual":dificultad_actual,
            "multijugador_actual":multijugador_actual,
            "idioma_actual":idioma_actual,
            "musica_volumen":musica_volumen,
            "controles":controles,
            "stats":stats,
            "build_seleccionada":build_seleccionada,
            "relics_scale0":list(relics_scale0),
            "mission_claimed":mission_claimed,
            "achievement_claimed":list(achievement_claimed),
            "permanent_upgrades":permanent_upgrades,
            "daily_state":daily_state
        }
        with open(SAVE_FILE,"w",encoding="utf-8") as f:
            json.dump(data,f,indent=4)
        progreso_pendiente = False
        ultimo_autoguardado = pygame.time.get_ticks()
    except Exception as e:
        print("No se pudo guardar progreso:", e)

def ganar_monedas(cantidad):
    global monedas, progreso_pendiente

    cantidad = max(0,int(cantidad))

    bonus_perm = 1 + permanent_upgrades.get("coin",0) * 0.10
    cantidad = int(cantidad * bonus_perm)

    if habilidad_comprada("coin_booster"):
        cantidad = int(cantidad * 1.25)

    monedas += cantidad
    stats["coins_earned"] += cantidad
    if cantidad > 0:
        reproducir_sfx("coin", volumen_extra=0.75)
    progreso_pendiente = True

def comprar_nave(id_nave):
    global monedas, nave_seleccionada, shop_message, shop_message_text
    precio=SHIP_PRICES.get(id_nave,0)
    if id_nave in owned_ships:
        nave_seleccionada=id_nave
        shop_message=90
        shop_message_text=txt("equipped")
        guardar_progreso()
        return
    if monedas >= precio:
        monedas -= precio
        owned_ships.add(id_nave)
        nave_seleccionada=id_nave
        shop_message=90
        shop_message_text=txt("purchased")
        guardar_progreso()
    else:
        shop_message=90
        shop_message_text=txt("not_enough")

def comprar_habilidad(nombre):
    global monedas, shop_message, shop_message_text
    precio=ABILITY_PRICES.get(nombre,0)
    if nombre in owned_abilities:
        shop_message=90
        shop_message_text=txt("owned")
        return
    if monedas >= precio:
        monedas -= precio
        owned_abilities.add(nombre)
        shop_message=90
        shop_message_text=txt("purchased")
        guardar_progreso()
    else:
        shop_message=90
        shop_message_text=txt("not_enough")

def habilidad_comprada(nombre):
    return nombre in owned_abilities

def hp_maximo_jugador():
    base = 100 + permanent_upgrades.get("hp",0) * 20
    if build_seleccionada == "guardian":
        base += 30
    if "vital_orb" in relics_scale0:
        base += 25
    return base

def factor_cooldown():
    factor = 1 - permanent_upgrades.get("cooldown",0) * 0.07
    if build_seleccionada == "assault":
        factor -= 0.08
    if "time_shard" in relics_scale0:
        factor -= 0.05
    return max(0.55, factor)

def recompensa_scale0_bonus(valor):
    bonus = 1.0
    if build_seleccionada == "anomaly":
        bonus += 0.25
    if "zero_relic" in relics_scale0:
        bonus += 0.20
    return int(valor * bonus)

def nombre_build_actual():
    b = BUILD_DEFS.get(build_seleccionada, BUILD_DEFS["balanced"])
    return b["name"] if idioma_actual == "EN" else b["name_es"]

def seleccionar_build_por_indice(indice):
    global build_seleccionada, shop_message, shop_message_text
    claves = ["balanced","assault","guardian","anomaly"]
    if 0 <= indice < len(claves):
        build_seleccionada = claves[indice]
        shop_message = 95
        shop_message_text = ("BUILD: " if idioma_actual == "EN" else "RUTA: ") + nombre_build_actual()
        guardar_progreso()

def coste_mejora(nombre):
    nivel = permanent_upgrades.get(nombre,0)
    return int(UPGRADE_DEFS[nombre]["base_cost"] * (nivel + 1) * (1 + nivel * 0.35))

def comprar_mejora(nombre):
    global monedas, shop_message, shop_message_text

    if nombre not in UPGRADE_DEFS:
        return

    if permanent_upgrades.get(nombre,0) >= UPGRADE_DEFS[nombre]["max"]:
        shop_message = 90
        shop_message_text = txt("maxed")
        return

    precio = coste_mejora(nombre)
    if monedas >= precio:
        monedas -= precio
        permanent_upgrades[nombre] += 1
        shop_message = 90
        shop_message_text = txt("purchased")
        guardar_progreso()
    else:
        shop_message = 90
        shop_message_text = txt("not_enough")

def progreso_logro(logro_id):
    logro = ACHIEVEMENTS[logro_id]
    return min(int(stats.get(logro["stat"],0)), logro["goal"])

def reclamar_logro(logro_id):
    global monedas, shop_message, shop_message_text

    if logro_id in achievement_claimed or logro_id not in ACHIEVEMENTS:
        return

    logro = ACHIEVEMENTS[logro_id]
    if progreso_logro(logro_id) >= logro["goal"]:
        achievement_claimed.add(logro_id)
        monedas += logro["reward"]
        stats["coins_earned"] += logro["reward"]
        shop_message = 90
        shop_message_text = "+" + str(logro["reward"]) + " " + txt("coins")
        guardar_progreso()

def asegurar_diarias():
    hoy = date.today().isoformat()
    ahora = time.time()
    if daily_state.get("date") != hoy or ahora >= float(daily_state.get("reset_at",0)):
        daily_state["date"] = hoy
        daily_state["reset_at"] = ahora + 24*60*60
        daily_state["base"] = {k:int(stats.get(k,0)) for k in stats}
        daily_state["claimed"] = {}
        guardar_progreso()

def texto_tiempo_diarias():
    restante = max(0, int(float(daily_state.get("reset_at",0)) - time.time()))
    horas = restante // 3600
    minutos = (restante % 3600) // 60
    return f"{horas:02d}h {minutos:02d}m"

def progreso_diaria(daily_id):
    asegurar_diarias()
    mision = DAILY_MISSION_POOL[daily_id]
    base = int(daily_state.get("base",{}).get(mision["stat"],0))
    actual = int(stats.get(mision["stat"],0))
    return min(max(0, actual - base), mision["goal"])

def reclamar_diaria(daily_id):
    global monedas, shop_message, shop_message_text

    asegurar_diarias()
    if daily_state.get("claimed",{}).get(daily_id, False) or daily_id not in DAILY_MISSION_POOL:
        return

    mision = DAILY_MISSION_POOL[daily_id]
    if progreso_diaria(daily_id) >= mision["goal"]:
        daily_state["claimed"][daily_id] = True
        monedas += mision["reward"]
        stats["coins_earned"] += mision["reward"]
        shop_message = 90
        shop_message_text = "+" + str(mision["reward"]) + " " + txt("coins")
        guardar_progreso()

def nombre_modo_juego():
    if multijugador_actual == "coop":
        return txt("local_coop")
    if multijugador_actual == "online_host":
        return txt("online_host")
    if multijugador_actual == "online_join":
        return txt("online_join")
    return txt("solo")

def coop_activo():
    return multijugador_actual in ["coop","online_host"]

def online_host_activo():
    return multijugador_actual == "online_host"

def online_join_activo():
    return multijugador_actual == "online_join"

def online_activo():
    return multijugador_actual in ["online_host","online_join"]

def coop_o_online_activo():
    return multijugador_actual in ["coop","online_host","online_join"]

def obtener_ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8",80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "127.0.0.1"

def net_send_json(sock, data):
    try:
        raw = (json.dumps(data) + "\n").encode("utf-8")
        sock.sendall(raw)
        return True
    except:
        return False

def net_recv_lines(sock, buffer):
    try:
        chunk = sock.recv(8192)
        if not chunk:
            return buffer, []
        buffer += chunk.decode("utf-8", errors="ignore")
        lines = []
        while "\n" in buffer:
            line, buffer = buffer.split("\n",1)
            if line.strip():
                lines.append(line.strip())
        return buffer, lines
    except:
        return buffer, []

def crear_frame_online():
    # LAN Online V2:
    # El host envï¿½a la pantalla interna 800x600 ya dibujada.
    # El cliente la muestra directamente, por lo que la imagen es mucho mï¿½s fiel.
    try:
        raw = pygame.image.tostring(pantalla, "RGB")
        comprimido = zlib.compress(raw, 1)
        empaquetado = base64.b64encode(comprimido).decode("ascii")

        return {
            "estado":"frame",
            "w":ANCHO,
            "h":ALTO,
            "fmt":"RGB",
            "frame":empaquetado,
            "t":time.time()
        }
    except Exception as ex:
        return None

def enviar_frame_host():
    global net_last_frame_sent

    if net_role != "host" or not net_connected or net_conn is None:
        return

    ahora = time.time()

    if ahora - net_last_frame_sent < net_frame_interval:
        return

    net_last_frame_sent = ahora

    paquete = crear_frame_online()

    if paquete is not None:
        net_send_json(net_conn, paquete)

def crear_snapshot_online():
    # Snapshot compacto para que el cliente pueda ver la partida.
    return {
        "estado":"snapshot",
        "score":int(estado.get("score",0)),
        "vidas":float(estado.get("hp",estado.get("vidas",0))),
        "nave_x":float(estado.get("nave_x",0)),
        "nave_y":float(estado.get("nave_y",0)),
        "nave_tipo":int(estado.get("nave_tipo",1)),
        "nave2_x":float(estado.get("nave2_x",0)),
        "nave2_y":float(estado.get("nave2_y",0)),
        "nave2_tipo":int(estado.get("nave2_tipo",2)),
        "balas":estado.get("balas",[])[:80],
        "balas_enemigas":estado.get("balas_enemigas",[])[:80],
        "enemigos":[
            {
                "tipo":en.get("tipo","asteroide"),
                "x":float(en.get("x",0)),
                "y":float(en.get("y",0)),
                "vida":int(en.get("vida",1))
            }
            for en in estado.get("enemigos",[])[:30]
        ],
        "boss":estado.get("boss"),
        "boss_final":estado.get("boss_final"),
        "boss_laser":estado.get("boss_laser"),
        "boss_overmind":estado.get("boss_overmind"),
        "boss_rift":estado.get("boss_rift"),
        "laser":estado.get("laser",0),
        "laser_x":estado.get("laser_x",0),
        "laser_horizontal":estado.get("laser_horizontal",0),
        "laser_y":estado.get("laser_y",0),
        "laser_cross":estado.get("laser_cross",0),
        "laser_cross_x":estado.get("laser_cross_x",0),
        "laser_cross_y":estado.get("laser_cross_y",0),
    }

def iniciar_host_lan():
    global net_role, net_server, net_conn, net_connected, net_thread_running, net_status

    cerrar_red_lan()

    net_role = "host"
    net_connected = False
    net_thread_running = True
    net_status = txt("online_waiting") + " " + obtener_ip_local() + ":" + str(NET_PORT)

    def host_thread():
        global net_server, net_conn, net_connected, net_thread_running, net_status, net_remote_inputs

        buffer = ""

        try:
            net_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            net_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            net_server.bind(("", NET_PORT))
            net_server.listen(1)
            net_server.settimeout(0.5)

            while net_thread_running and net_conn is None:
                try:
                    conn, addr = net_server.accept()
                    conn.setblocking(False)
                    net_conn = conn
                    net_connected = True
                    net_status = txt("online_connected") + ": " + str(addr[0])
                    break
                except socket.timeout:
                    pass

            while net_thread_running and net_conn is not None:
                buffer, lines = net_recv_lines(net_conn, buffer)

                for line in lines:
                    try:
                        data = json.loads(line)
                        if data.get("tipo") == "inputs":
                            with net_lock:
                                net_remote_inputs = data.get("inputs",{})
                    except:
                        pass

                time.sleep(0.004)

        except Exception as ex:
            net_status = "HOST ERROR: " + str(ex)
        finally:
            net_connected = False

    threading.Thread(target=host_thread, daemon=True).start()

def iniciar_cliente_lan(ip):
    global net_role, net_client, net_connected, net_thread_running, net_status, net_join_ip, net_client_snapshot

    cerrar_red_lan()

    net_role = "client"
    net_join_ip = ip.strip()
    net_connected = False
    net_thread_running = True
    net_status = txt("online_joining")
    net_client_snapshot = None

    def client_thread():
        global net_client, net_connected, net_thread_running, net_status, net_client_snapshot, net_client_frame_raw, net_client_frame_id

        buffer = ""

        try:
            net_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            net_client.settimeout(5)
            net_client.connect((net_join_ip, NET_PORT))
            net_client.setblocking(False)
            net_connected = True
            net_status = txt("online_client")

            while net_thread_running and net_client is not None:
                buffer, lines = net_recv_lines(net_client, buffer)

                for line in lines:
                    try:
                        data = json.loads(line)
                        if data.get("estado") == "snapshot":
                            with net_lock:
                                net_client_snapshot = data

                        elif data.get("estado") == "frame":
                            try:
                                frame_comprimido = base64.b64decode(data.get("frame",""))
                                frame_raw = zlib.decompress(frame_comprimido)

                                with net_lock:
                                    net_client_frame_raw = frame_raw
                                    net_client_frame_id += 1
                            except:
                                pass
                    except:
                        pass

                time.sleep(0.004)

        except Exception as ex:
            net_connected = False
            net_status = txt("online_failed")
        finally:
            net_connected = False

    threading.Thread(target=client_thread, daemon=True).start()

def cerrar_red_lan():
    global net_role, net_server, net_conn, net_client, net_connected, net_thread_running, net_status

    net_thread_running = False

    try:
        if net_conn:
            net_conn.close()
    except:
        pass

    try:
        if net_server:
            net_server.close()
    except:
        pass

    try:
        if net_client:
            net_client.close()
    except:
        pass

    net_server = None
    net_conn = None
    net_client = None
    net_connected = False
    net_status = ""
    net_role = "none"

def enviar_snapshot_host():
    if net_role == "host" and net_connected and net_conn is not None:
        net_send_json(net_conn, crear_snapshot_online())

def enviar_inputs_cliente(teclas):
    if net_role == "client" and net_connected and net_client is not None:
        # El cliente online usa los controles normales del Jugador 1:
        # WASD, flecha arriba y habilidades estï¿½ndar.
        # El host los recibe como acciones del Jugador 2.
        inputs = {
            "p2_move_left":tecla_pulsada(teclas,"move_left"),
            "p2_move_right":tecla_pulsada(teclas,"move_right"),
            "p2_move_up":tecla_pulsada(teclas,"move_up"),
            "p2_move_down":tecla_pulsada(teclas,"move_down"),
            "p2_shoot":tecla_pulsada(teclas,"shoot"),
            "p2_dash":tecla_pulsada(teclas,"dash"),
            "p2_special_laser":tecla_pulsada(teclas,"special_laser"),
            "p2_pulse":tecla_pulsada(teclas,"pulse"),
            "p2_ultimate_overdrive":tecla_pulsada(teclas,"ultimate_overdrive"),
            "p2_ultimate_blackhole":tecla_pulsada(teclas,"ultimate_blackhole"),
            "p2_ultimate_orbital":tecla_pulsada(teclas,"ultimate_orbital"),
        }
        net_send_json(net_client, {"tipo":"inputs","inputs":inputs})

def input_p2_activo(nombre_accion, teclas):
    if net_role == "host" and online_host_activo():
        with net_lock:
            return bool(net_remote_inputs.get(nombre_accion, False))
    return tecla_pulsada(teclas, nombre_accion)


def rect_jugador_principal():
    tam = int((42 if estado.get("coop",False) else 50) * HD_VISUAL_SCALE)
    return pygame.Rect(estado["nave_x"], estado["nave_y"], tam, tam)

def rect_jugador_2():
    if not estado.get("coop",False):
        return None
    return pygame.Rect(estado["nave2_x"], estado["nave2_y"], int(42 * HD_VISUAL_SCALE), int(42 * HD_VISUAL_SCALE))

def colisiona_con_jugador(rect_objeto):
    if rect_objeto.colliderect(rect_jugador_principal()):
        return True

    r2 = rect_jugador_2()
    if r2 is not None and rect_objeto.colliderect(r2):
        return True

    return False

def punto_colisiona_jugador(x,y):
    if rect_jugador_principal().collidepoint(x,y):
        return True

    r2 = rect_jugador_2()
    if r2 is not None and r2.collidepoint(x,y):
        return True

    return False

def nombre_dificultad():
    if dificultad_actual == "facil":
        return txt("easy")
    if dificultad_actual == "normal":
        return txt("normal_mode")
    if dificultad_actual == "dificil":
        return txt("hard")
    if dificultad_actual == "muy_dificil":
        return txt("very_hard")
    return txt("easy")

def overdrive_permitido():
    return dificultad_actual == "facil"

def ultimates_boss_permitidas():
    return dificultad_actual in ["facil", "normal"]

def aplicar_dano_jugador(cantidad=1):
    # Sistema de HP real.
    # Antes 1 punto de daï¿½o equivalï¿½a aproximadamente a 1 corazï¿½n.
    # Ahora equivale a 20 HP para que la barra tenga sentido.
    dano = cantidad * 20

    if dificultad_actual == "muy_dificil":
        dano *= 1.10

    estado["hp"] -= dano
    estado["vidas"] = estado["hp"]
    reproducir_sfx("player_hit", volumen_extra=0.85)

def registrar_enemigo_destruido():
    stats["enemies_destroyed"] += 1
    if "estado" in globals() and isinstance(estado, dict) and estado.get("estado") == "JUGANDO":
        estado["planet_mission_kills"] = estado.get("planet_mission_kills",0) + 1

def registrar_boss_derrotado():
    stats["bosses_defeated"] += 1

def debilidad_boss_cockpit(tipo):
    datos = {
        "normal":("motor", "MOTOR", "ENGINE", (255,120,80)),
        "boss":("motor", "MOTOR", "ENGINE", (255,120,80)),
        "final":("nucleo", "NUCLEO", "CORE", (200,90,255)),
        "laser":("armas", "ARMAS", "WEAPONS", (255,80,65)),
        "boss_laser":("armas", "ARMAS", "WEAPONS", (255,80,65)),
        "boss_overmind":("mente", "MENTE", "MIND", (190,80,255)),
        "boss_rift":("ancla", "ANCLA", "ANCHOR", (80,225,255)),
        "boss_hollow":("sello", "SELLO", "SEAL", (80,235,255)),
        "boss_sun_eater":("reactor", "REACTOR", "REACTOR", (255,170,55)),
        "boss_eden":("raiz", "RAIZ", "ROOT", (100,255,185))
    }
    return datos.get(tipo, datos["normal"])

def iniciar_cabina_jugable_boss(tipo, nombre, duracion):
    nombre_l = nombre.lower()
    if "overmind" in nombre_l:
        tipo = "boss_overmind"
    elif "rift" in nombre_l:
        tipo = "boss_rift"
    elif "hollow" in nombre_l:
        tipo = "boss_hollow"
    elif "sun" in nombre_l:
        tipo = "boss_sun_eater"
    elif "eden" in nombre_l:
        tipo = "boss_eden"
    elif "laser" in nombre_l:
        tipo = "boss_laser"
    debilidad = debilidad_boss_cockpit(tipo)
    estado["cockpit_scan"] = {
        "active":True,
        "x":ANCHO//2,
        "y":285,
        "target_x":ANCHO//2 + random.randint(-70,70),
        "target_y":265 + random.randint(-36,46),
        "progress":0.0,
        "system":"weapons",
        "locked":False,
        "weakness":debilidad[0],
        "message":"",
        "message_timer":0,
        "bonus_ready":False,
        "prepared":False,
        "prep_timer":0,
        "launch_ready":False,
        "color":debilidad[3]
    }
    estado["cockpit_bonus"] = None
    estado["cockpit_bonus_timer"] = 0
    estado["boss_intro"] = duracion
    estado["boss_intro_max"] = duracion
    estado["boss_intro_tipo"] = tipo
    estado["boss_intro_nombre"] = nombre
    reproducir_sfx("cockpit_boot", force=True)
    reproducir_sfx("boss_intro", force=True)

def nombre_sistema_cabina(system):
    if idioma_actual == "EN":
        return {"weapons":"WEAPONS", "shield":"SHIELD", "reactor":"REACTOR"}.get(system,"WEAPONS")
    return {"weapons":"ARMAS", "shield":"ESCUDO", "reactor":"REACTOR"}.get(system,"ARMAS")

def aplicar_bonus_cabina(system):
    scan = estado.get("cockpit_scan",{})
    estado["cockpit_bonus"] = system
    estado["cockpit_bonus_timer"] = 900
    if system == "weapons":
        estado["cockpit_damage_boost"] = max(estado.get("cockpit_damage_boost",0), 720)
        texto = "ARMAS CALIBRADAS" if idioma_actual != "EN" else "WEAPONS CALIBRATED"
        reproducir_sfx("laser_charge", volumen_extra=0.72, force=True)
    elif system == "shield":
        estado["shield"] = max(estado.get("shield",0), 260)
        estado["inv"] = max(estado.get("inv",0), 80)
        texto = "ESCUDO REFORZADO" if idioma_actual != "EN" else "SHIELD REINFORCED"
        reproducir_sfx("shield_pickup", volumen_extra=0.9, force=True)
    else:
        estado["dash_cd"] = max(0, int(estado.get("dash_cd",0) * 0.55))
        estado["player_laser_cd"] = max(0, int(estado.get("player_laser_cd",0) * 0.60))
        estado["pulse_cd"] = max(0, int(estado.get("pulse_cd",0) * 0.60))
        texto = "REACTOR SINCRONIZADO" if idioma_actual != "EN" else "REACTOR SYNCHRONIZED"
        reproducir_sfx("cockpit_scan", volumen_extra=0.9, force=True)
    scan["message"] = texto
    scan["message_timer"] = 130
    scan["prepared"] = True
    scan["prep_timer"] = 150
    scan["launch_ready"] = False
    estado["ultimate_message"] = 0
    estado["ultimate_message_text"] = ""

def actualizar_cabina_jugable_boss():
    scan = estado.get("cockpit_scan")
    if not scan or not scan.get("active",False) or estado.get("boss_intro",0) <= 0:
        return
    if scan.get("prepared",False):
        if scan.get("prep_timer",0) > 0:
            scan["prep_timer"] -= 1
            if scan["prep_timer"] in [116, 76, 36]:
                globals()["flash"] = max(globals().get("flash",0), 4)
        else:
            scan["launch_ready"] = True
            if scan.get("message_timer",0) <= 0:
                scan["message"] = "LISTO - ENTER PARA EMPEZAR ATAQUE" if idioma_actual != "EN" else "READY - ENTER TO START ATTACK"
                scan["message_timer"] = 40
        if scan.get("message_timer",0) > 0:
            scan["message_timer"] -= 1
        return
    teclas = pygame.key.get_pressed()
    velocidad = 4.8
    if teclas[pygame.K_a] or teclas[pygame.K_LEFT]:
        scan["x"] -= velocidad
    if teclas[pygame.K_d] or teclas[pygame.K_RIGHT]:
        scan["x"] += velocidad
    if teclas[pygame.K_w] or teclas[pygame.K_UP]:
        scan["y"] -= velocidad
    if teclas[pygame.K_s] or teclas[pygame.K_DOWN]:
        scan["y"] += velocidad
    scan["x"] = max(190, min(610, scan["x"]))
    scan["y"] = max(145, min(392, scan["y"]))
    distancia = math.hypot(scan["x"]-scan["target_x"], scan["y"]-scan["target_y"])
    escaneando = teclas[pygame.K_SPACE]
    if escaneando and distancia < 42:
        scan["progress"] = min(100.0, scan.get("progress",0.0) + 1.35)
    elif escaneando and distancia < 82:
        scan["progress"] = min(100.0, scan.get("progress",0.0) + 0.42)
    else:
        scan["progress"] = max(0.0, scan.get("progress",0.0) - 0.10)
    if scan["progress"] >= 100 and not scan.get("bonus_ready",False):
        scan["bonus_ready"] = True
        _, es, en, _ = debilidad_boss_cockpit(estado.get("boss_intro_tipo","normal"))
        scan["message"] = ("DEBILIDAD: " + es if idioma_actual != "EN" else "WEAKNESS: " + en)
        scan["message_timer"] = 130
        flash = globals().get("flash",0)
        globals()["flash"] = max(flash,8)
        reproducir_sfx("cockpit_scan", volumen_extra=1.1, force=True)
    if scan.get("message_timer",0) > 0:
        scan["message_timer"] -= 1

def seleccionar_sistema_cabina(system):
    scan = estado.get("cockpit_scan")
    if not scan or not scan.get("active",False):
        return
    scan["system"] = system
    scan["message"] = ("SISTEMA: " if idioma_actual != "EN" else "SYSTEM: ") + nombre_sistema_cabina(system)
    scan["message_timer"] = 65
    reproducir_sfx("pickup", volumen_extra=0.65)

def confirmar_sistema_cabina():
    scan = estado.get("cockpit_scan")
    if not scan or not scan.get("active",False):
        return
    if scan.get("prepared",False):
        if scan.get("launch_ready",False):
            scan["active"] = False
            estado["boss_intro"] = 58
            estado["boss_intro_max"] = max(58, estado.get("boss_intro_max",58))
            globals()["flash"] = max(globals().get("flash",0), 10)
            globals()["shake"] = max(globals().get("shake",0), 14)
            reproducir_sfx("transition", volumen_extra=0.82, force=True)
        else:
            scan["message"] = "PREPARANDO SISTEMA..." if idioma_actual != "EN" else "PREPARING SYSTEM..."
            scan["message_timer"] = 55
        return
    if scan.get("bonus_ready",False):
        aplicar_bonus_cabina(scan.get("system","weapons"))
    else:
        scan["message"] = "ESCANEO INCOMPLETO" if idioma_actual != "EN" else "SCAN INCOMPLETE"
        scan["message_timer"] = 70

def dano_bala_boss():
    if estado.get("cockpit_damage_boost",0) > 0:
        return 2
    return 1

def nombre_boss_desde_tipo(tipo):
    nombres = {
        "boss":"ASTEROID COMMANDER",
        "boss_final":"OMEGA DESTROYER",
        "boss_laser":"LASER OVERLORD",
        "boss_overmind":"THE OVERMIND",
        "boss_rift":"THE RIFT MONARCH",
        "boss_hollow":"THE HOLLOW SAINT",
        "boss_sun_eater":"THE SUN EATER",
        "boss_eden":"EDEN PRIME"
    }
    return nombres.get(tipo, "BOSS")

def loot_especifico_boss(tipo):
    datos = {
        "boss_laser":{"id":"laser_lens","name":"LENTE LASER","name_en":"LASER LENS","desc":"+dano de laser temporal","desc_en":"Temporary laser damage boost"},
        "boss_overmind":{"id":"overmind_eye","name":"OJO MENTAL","name_en":"MIND EYE","desc":"Mas recompensa de anomalias","desc_en":"Better anomaly reward"},
        "boss_rift":{"id":"rift_shard","name":"FRAGMENTO RIFT","name_en":"RIFT SHARD","desc":"Reactor y dash mejorados","desc_en":"Improved reactor and dash"},
        "boss_hollow":{"id":"hollow_seal","name":"SELLO ABISAL","name_en":"ABYSS SEAL","desc":"Escudo fuerte tras boss","desc_en":"Strong post-boss shield"},
        "boss_sun_eater":{"id":"sun_core","name":"NUCLEO SOLAR","name_en":"SOLAR CORE","desc":"Armas sobrecalentadas","desc_en":"Overheated weapons"},
        "boss_eden":{"id":"eden_seed","name":"SEMILLA EDEN","name_en":"EDEN SEED","desc":"Recuperacion y vida extra","desc_en":"Recovery and extra life"}
    }
    return datos.get(tipo)

def crear_opcion_loot(loot_id, name, name_en, desc, desc_en, rare=False):
    return {"id":loot_id,"name":name,"name_en":name_en,"desc":desc,"desc_en":desc_en,"rare":rare}

def generar_loot_boss(tipo):
    opciones = [
        crear_opcion_loot("weapon_core","NUCLEO DE ARMAS","WEAPON CORE","+dano contra bosses temporal","Temporary boss damage boost"),
        crear_opcion_loot("shield_core","NUCLEO DE ESCUDO","SHIELD CORE","Escudo y pequena cura","Shield and small heal"),
        crear_opcion_loot("reactor_core","NUCLEO REACTOR","REACTOR CORE","Reduce cooldowns actuales","Reduces current cooldowns"),
        crear_opcion_loot("planet_fragment","FRAGMENTO PLANETA","PLANET FRAGMENT","Monedas y mision planetaria","Coins and planet mission bonus"),
        crear_opcion_loot("rare_relic","RELIQUIA RARA","RARE RELIC","Bonus fuerte poco comun","Rare strong bonus", True)
    ]
    especial = loot_especifico_boss(tipo)
    seleccion = random.sample(opciones[:4], 2)
    if especial and random.randint(1,100) <= 72:
        seleccion.append(crear_opcion_loot(especial["id"], especial["name"], especial["name_en"], especial["desc"], especial["desc_en"], True))
    else:
        seleccion.append(random.choice(opciones))
    random.shuffle(seleccion)
    return seleccion[:3]

def iniciar_botin_boss(tipo):
    if estado.get("boss_loot_pending",False):
        return
    estado["boss_loot_pending"] = True
    estado["boss_loot_tipo"] = tipo
    estado["boss_loot_choices"] = generar_loot_boss(tipo)
    estado["boss_loot_anim"] = 0
    estado["estado"] = "BOSS_LOOT"
    reproducir_sfx("loot", force=True)

def aplicar_loot_boss(opcion):
    global monedas
    loot_id = opcion.get("id","")
    reproducir_sfx("loot", force=True)
    if loot_id in ["weapon_core","laser_lens","sun_core"]:
        estado["cockpit_damage_boost"] = max(estado.get("cockpit_damage_boost",0), 900 if loot_id != "weapon_core" else 620)
    elif loot_id in ["shield_core","hollow_seal"]:
        estado["hp"] = min(estado.get("max_hp",100), estado.get("hp",100) + (55 if loot_id == "hollow_seal" else 30))
        estado["vidas"] = estado["hp"]
        estado["shield"] = max(estado.get("shield",0), 360 if loot_id == "hollow_seal" else 240)
    elif loot_id in ["reactor_core","rift_shard"]:
        factor = 0.35 if loot_id == "rift_shard" else 0.55
        for cd in ["dash_cd","player_laser_cd","pulse_cd","ultimate_overdrive_cd","ultimate_blackhole_cd","ultimate_orbital_cd"]:
            estado[cd] = max(0, int(estado.get(cd,0) * factor))
    elif loot_id == "planet_fragment":
        estado["score"] += 22000
        ganar_monedas(3500)
        estado["planet_mission_kills"] = estado.get("planet_mission_kills",0) + 3
    elif loot_id == "overmind_eye":
        estado["score"] += 30000
        ganar_monedas(5000)
        estado["wormhole_cd"] = max(900, int(estado.get("wormhole_cd",3600)*0.55))
    elif loot_id == "eden_seed":
        estado["max_hp"] += 10
        estado["hp"] = min(estado["max_hp"], estado.get("hp",100) + 70)
        estado["vidas"] = estado["hp"]
    else:
        estado["score"] += 45000
        ganar_monedas(6500)
    estado["ultimate_message"] = 115
    estado["ultimate_message_text"] = (opcion["name_en"] if idioma_actual == "EN" else opcion["name"])
    estado["boss_loot_pending"] = False
    estado["boss_loot_choices"] = []
    estado["estado"] = "JUGANDO"

def dibujar_botin_boss():
    estado["boss_loot_anim"] = estado.get("boss_loot_anim",0) + 1
    ticks = pygame.time.get_ticks()
    pantalla.fill((2,6,14))
    dibujar_fondo_menu_animado(0.35)
    overlay = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    overlay.fill((0,0,0,135))
    pantalla.blit(overlay,(0,0))
    tipo = estado.get("boss_loot_tipo","boss")
    titulo = "BOTIN DE BOSS" if idioma_actual != "EN" else "BOSS LOOT"
    subtitulo = nombre_boss_desde_tipo(tipo)
    t1 = pygame.font.SysFont(None,54).render(titulo, True, (235,245,255))
    t2 = fuente.render(subtitulo, True, (255,220,120))
    pantalla.blit(t1,(ANCHO//2-t1.get_width()//2,72))
    pantalla.blit(t2,(ANCHO//2-t2.get_width()//2,122))

    opciones = estado.get("boss_loot_choices",[])
    xs = [155, 400, 645]
    mouse = convertir_pos_mouse(pygame.mouse.get_pos())
    for idx,op in enumerate(opciones):
        cx = xs[idx]
        rect = pygame.Rect(cx-94,185,188,285)
        hover = rect.collidepoint(mouse)
        color = (255,210,90) if op.get("rare") else (90,220,255)
        if hover:
            crear_rect_glow(pantalla,(rect.x,rect.y,rect.w,rect.h),color,65,16)
        pygame.draw.rect(pantalla,(5,14,28),rect,border_radius=10)
        pygame.draw.rect(pantalla,color,rect,2,border_radius=10)
        img_name = ASSET_LOOT.get(op["id"], "loot_rare_relic.png")
        img = asset_xfondo(img_name, (104,104))
        blit_asset_centrado(pantalla,img,cx,270,(104,104),rotacion=math.sin(ticks*0.004+idx)*2)
        nombre = op["name_en"] if idioma_actual == "EN" else op["name"]
        desc = op["desc_en"] if idioma_actual == "EN" else op["desc"]
        dibujar_texto_centrado_auto(pantalla,nombre,pygame.Rect(rect.x+10,rect.y+156,rect.w-20,36),(235,245,255),24,14)
        dibujar_texto_centrado_auto(pantalla,desc,pygame.Rect(rect.x+12,rect.y+200,rect.w-24,48),(180,215,230),19,12)
        key = pygame.font.SysFont(None,24).render(str(idx+1), True, color)
        pygame.draw.circle(pantalla,(8,18,32),(rect.x+24,rect.y+24),15)
        pantalla.blit(key,(rect.x+24-key.get_width()//2,rect.y+24-key.get_height()//2))

    hint = "1 / 2 / 3 o clic para elegir" if idioma_actual != "EN" else "Press 1 / 2 / 3 or click to choose"
    rh = fuente_peq.render(hint, True, (180,220,235))
    pantalla.blit(rh,(ANCHO//2-rh.get_width()//2,510))

def objetivo_mision_planeta():
    objetivos = {
        "ares_prime":10,
        "nebula_cryon":12,
        "vortice_umbra":14,
        "eden_9":16,
        "scale_0":3
    }
    return objetivos.get(planeta_seleccionado,10)

def actualizar_mision_planeta():
    if estado.get("planet_mission_claimed",False):
        return
    objetivo = objetivo_mision_planeta()
    if estado.get("planet_mission_kills",0) >= objetivo:
        bonus = 12000 + objetivo * 800
        estado["score"] += bonus
        ganar_monedas(bonus//10)
        estado["planet_mission_claimed"] = True
        stats["planet_missions_done"] = stats.get("planet_missions_done",0) + 1
        estado["ultimate_message"] = 130
        estado["ultimate_message_text"] = ("MISION PLANETA +" if idioma_actual != "EN" else "PLANET MISSION +") + str(bonus)

def dibujar_mision_planeta():
    objetivo = objetivo_mision_planeta()
    progreso = min(objetivo, estado.get("planet_mission_kills",0))
    texto = ("MISION PLANETA" if idioma_actual != "EN" else "PLANET MISSION") + f": {progreso}/{objetivo}"
    render = pygame.font.SysFont(None,18).render(texto, True, (170,235,220))
    pantalla.blit(render,(12,126))

def registrar_partida_si_necesario():
    global run_counted

    if not run_counted:
        stats["games_played"] += 1
        run_counted = True
        guardar_progreso()

def finalizar_partida_y_guardar(score_final):
    global run_counted

    stats["best_score"] = max(stats["best_score"], int(score_final))
    run_counted = False
    guardar_progreso()

def estado_mision(mision_id):
    if mision_id == "destroy_50":
        progreso = min(stats["enemies_destroyed"],50)
        objetivo = 50
        recompensa = 15000
        texto = txt("mission_1")
    elif mision_id == "score_100k":
        progreso = min(stats["best_score"],100000)
        objetivo = 100000
        recompensa = 25000
        texto = txt("mission_2")
    elif mision_id == "boss_1":
        progreso = min(stats["bosses_defeated"],1)
        objetivo = 1
        recompensa = 40000
        texto = txt("mission_3")
    else:
        progreso = min(stats["coins_earned"],25000)
        objetivo = 25000
        recompensa = 20000
        texto = txt("mission_4")

    completada = progreso >= objetivo
    reclamada = mission_claimed.get(mision_id,False)

    return {
        "texto":texto,
        "progreso":progreso,
        "objetivo":objetivo,
        "recompensa":recompensa,
        "completada":completada,
        "reclamada":reclamada
    }

def reclamar_mision(mision_id):
    global monedas, shop_message, shop_message_text

    datos = estado_mision(mision_id)

    if datos["completada"] and not datos["reclamada"]:
        mission_claimed[mision_id] = True
        monedas += datos["recompensa"]
        stats["coins_earned"] += datos["recompensa"]
        shop_message = 90
        shop_message_text = "+" + str(datos["recompensa"]) + " " + txt("coins")
        guardar_progreso()


def imagen_nave_por_tipo(tipo):
    if tipo == 1:
        return nave_img
    if tipo == 2:
        return nave2_img
    if tipo == 3:
        return nave_crimson_img
    if tipo == 4:
        return nave_nova_img
    if tipo == 5:
        return nave_phantom_img
    if tipo == 6:
        return nave_eclipse_img
    if tipo == 7:
        return nave_aurora_img
    if tipo == 8:
        return nave_quantum_img
    return nave_img

def preview_nave_por_tipo(tipo):
    if tipo == 3:
        return nave_crimson_preview_img
    if tipo == 4:
        return nave_nova_preview_img
    if tipo == 5:
        return nave_phantom_preview_img
    if tipo == 6:
        return nave_eclipse_preview_img
    if tipo == 7:
        return nave_aurora_preview_img
    if tipo == 8:
        return nave_quantum_preview_img
    return nave_preview_img

def color_nave_por_tipo(tipo):
    if tipo == 1:
        return (40,180,255)
    if tipo == 2:
        return (255,220,120)
    if tipo == 3:
        return (255,40,40)
    if tipo == 4:
        return (80,220,255)
    if tipo == 5:
        return (180,70,255)
    if tipo == 6:
        return (255,90,40)
    if tipo == 7:
        return (80,255,180)
    if tipo == 8:
        return (190,90,255)
    return (40,180,255)


# =====================
# FUNCION SEGURA PARA CARGAR IMAGENES
# =====================
def mezclar_color(c1, c2, factor=0.5):
    factor = max(0, min(1, factor))
    return (
        int(c1[0] * (1 - factor) + c2[0] * factor),
        int(c1[1] * (1 - factor) + c2[1] * factor),
        int(c1[2] * (1 - factor) + c2[2] * factor)
    )

def crear_sprite_procedural(nombre, tamano, color_base):
    """Fallback pixel-art para que el juego no muestre bloques planos si falta un asset."""
    w, h = tamano
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    nombre_l = nombre.lower()
    color_luz = mezclar_color(color_base, (255,255,255), 0.45)
    color_sombra = mezclar_color(color_base, (0,0,0), 0.45)
    color_nucleo = mezclar_color(color_base, (255,255,255), 0.18)

    for i in range(0, max(w, h), max(4, min(w, h)//8)):
        alpha = max(18, 70 - i)
        radio = max(1, min(w,h)//2 - i//2)
        pygame.draw.circle(surf, (color_base[0], color_base[1], color_base[2], alpha), (w//2, h//2), radio)

    if "nave" in nombre_l:
        cuerpo = [(w//2, h//10), (w*8//10, h*7//10), (w//2, h*9//10), (w*2//10, h*7//10)]
        pygame.draw.polygon(surf, color_sombra, cuerpo)
        pygame.draw.polygon(surf, color_base, [(w//2,h//8),(w*7//10,h*65//100),(w//2,h*78//100),(w*3//10,h*65//100)])
        pygame.draw.polygon(surf, color_luz, [(w//2,h//6),(w*57//100,h*62//100),(w//2,h*72//100),(w*43//100,h*62//100)])
        pygame.draw.circle(surf, (230,250,255), (w//2,h//2), max(2,min(w,h)//11))
        pygame.draw.rect(surf, (80,220,255,170), (w*42//100,h*78//100,w*16//100,max(3,h//10)))

    elif "boss" in nombre_l:
        for r in range(min(w,h)//2, min(w,h)//5, -max(5,min(w,h)//10)):
            pygame.draw.circle(surf, (color_base[0],color_base[1],color_base[2],44), (w//2,h//2), r, 2)
        pygame.draw.polygon(surf, color_sombra, [(w//2,h//12),(w*88//100,h//2),(w//2,h*92//100),(w*12//100,h//2)])
        pygame.draw.polygon(surf, color_base, [(w//2,h//7),(w*78//100,h//2),(w//2,h*82//100),(w*22//100,h//2)])
        pygame.draw.polygon(surf, color_luz, [(w//2,h//4),(w*63//100,h//2),(w//2,h*65//100),(w*37//100,h//2)])
        pygame.draw.circle(surf, (255,255,255), (w//2,h//2), max(4,min(w,h)//13))
        pygame.draw.circle(surf, color_base, (w//2,h//2), max(8,min(w,h)//8), 2)

    elif "asteroid" in nombre_l:
        pts = [(w//2,h//10),(w*82//100,h//4),(w*9//10,h*62//100),(w*62//100,h*88//100),(w//4,h*82//100),(w//10,h//2),(w//5,h//5)]
        pygame.draw.polygon(surf, color_sombra, pts)
        pygame.draw.polygon(surf, color_base, [(x-2,y-2) for x,y in pts])
        for _ in range(6):
            pygame.draw.circle(surf, color_sombra, (random.randint(w//4,w*3//4), random.randint(h//4,h*3//4)), max(2,min(w,h)//14), 1)

    elif "orb" in nombre_l or "gravity" in nombre_l or "mine" in nombre_l:
        pygame.draw.circle(surf, color_sombra, (w//2,h//2), min(w,h)//2-2)
        pygame.draw.circle(surf, color_base, (w//2,h//2), min(w,h)//3)
        pygame.draw.circle(surf, color_luz, (w//2,h//2), min(w,h)//5)
        pygame.draw.circle(surf, (230,250,255), (w//2,h//2), min(w,h)//2-4, 2)
        pygame.draw.circle(surf, color_base, (w//2,h//2), min(w,h)//2+2, 1)

    else:
        pygame.draw.polygon(surf, color_sombra, [(w//2,h//8),(w*82//100,h*35//100),(w*72//100,h*82//100),(w//2,h*94//100),(w*28//100,h*82//100),(w*18//100,h*35//100)])
        pygame.draw.polygon(surf, color_base, [(w//2,h//6),(w*74//100,h*38//100),(w*66//100,h*75//100),(w//2,h*86//100),(w*34//100,h*75//100),(w*26//100,h*38//100)])
        pygame.draw.rect(surf, color_luz, (w*42//100,h*27//100,w*16//100,h*38//100))
        pygame.draw.circle(surf, (245,255,255), (w//2,h//2), max(2,min(w,h)//12))

    pygame.draw.rect(surf, (255,255,255,35), (1,1,w-2,h-2), 1)
    return surf

def cargar_imagen(nombre, tamano, color_fallback=(120,120,120)):
    try:
        imagen = pygame.image.load(ruta_recurso(nombre))
        if imagen.get_alpha() is not None:
            imagen = imagen.convert_alpha()
        else:
            imagen = imagen.convert()
        return pygame.transform.smoothscale(imagen, hd_size(tamano))
    except:
        print("No se pudo cargar imagen:", nombre)
        return crear_sprite_procedural(nombre, hd_size(tamano), color_fallback)

ASSET_XFONDO_DIRS = [
    os.path.join(BASE_DIR, "assets", "images", "hazards"),
    os.path.join(BASE_DIR, "assets", "images", "loot"),
    os.path.join(BASE_DIR, "assets", "images", "cockpit"),
    os.path.join(BASE_DIR, "assets", "images", "cards"),
    os.path.join(BASE_DIR, "asset_concepts_v69", "assets_individuales_xfondos"),
]

def cargar_asset_xfondo(nombre, tamano=None):
    ruta = None
    for carpeta in ASSET_XFONDO_DIRS:
        candidato = os.path.join(carpeta, nombre)
        if os.path.exists(candidato):
            ruta = candidato
            break
    if ruta is None:
        ruta = ruta_recurso(nombre)
    if not os.path.exists(ruta):
        return None
    try:
        img = pygame.image.load(ruta).convert_alpha()
        if tamano:
            img = pygame.transform.smoothscale(img, tamano)
        return img
    except Exception as e:
        print("No se pudo cargar asset integrado:", nombre, e)
        return None

def blit_asset_centrado(superficie, img, cx, cy, tamano=None, alpha=None, rotacion=0):
    if img is None:
        return False
    final = img
    if tamano:
        final = pygame.transform.smoothscale(final, tamano)
    if rotacion:
        final = pygame.transform.rotozoom(final, rotacion, 1.0)
    if alpha is not None:
        final = final.copy()
        final.set_alpha(max(0, min(255, int(alpha))))
    superficie.blit(final, (int(cx-final.get_width()/2), int(cy-final.get_height()/2)))
    return True

ASSET_HAZARDS = {
    "heat_wave": "hazard_ares_heat_wave.png",
    "ice_shard": "hazard_cryon_ice_shard.png",
    "ion_strike": "hazard_umbra_ion_strike.png",
    "spore_bloom": "hazard_eden_spore.png",
    "zero_echo": "hazard_scale0_echo.png"
}

ASSET_LOOT = {
    "weapon_core":"loot_weapon_core.png",
    "shield_core":"loot_shield_core.png",
    "reactor_core":"loot_reactor_core.png",
    "planet_fragment":"loot_planet_fragment.png",
    "rare_relic":"loot_rare_relic.png",
    "laser_lens":"loot_laser_overlord_lens.png",
    "overmind_eye":"loot_overmind_eye.png",
    "rift_shard":"loot_rift_monarch_shard.png",
    "hollow_seal":"loot_hollow_saint_seal.png",
    "sun_core":"loot_sun_eater_core.png",
    "eden_seed":"loot_eden_prime_seed.png"
}

ASSET_COCKPIT = {
    "frame":"cockpit_frame_piece.png",
    "reticle":"scan_reticle.png",
    "target":"scan_target_marker.png",
    "weapons":"system_weapons_icon.png",
    "shield":"system_shield_icon.png",
    "reactor":"system_reactor_icon.png"
}

asset_cache_xfondo = {}

def asset_xfondo(nombre, tamano=None):
    clave = (nombre, tamano)
    if clave not in asset_cache_xfondo:
        asset_cache_xfondo[clave] = cargar_asset_xfondo(nombre, tamano)
    return asset_cache_xfondo[clave]

# =====================
# SISTEMA DINAMICO DE MUSICA
# =====================

MUSIC_TRACKS = {
    "menu": ["music_01_menu_mystery_leberch_space_ambient_509783.mp3"],
    "level_default": ["music_02_level_calm_monume_space_ambient_547940.mp3"],
    "ares_prime": ["music_03_ares_prime_freemusicforvideo_space_ambient_446647.mp3"],
    "nebula_cryon": ["music_04_nebula_cryon_monume_space_ambient_498030.mp3"],
    "vortice_umbra": ["music_05_vortice_umbra_freemusicforvideo_space_ambient_495614.mp3"],
    "eden_9": ["music_06_eden_9_delosound_space_ambient_cinematic_442834.mp3"],
    "scale_0": ["music_07_scale0_mystery_playstarz_music_space_ambient_435262.mp3", "musica_scale0.mp3"],
    "cockpit": ["music_08_cockpit_scan_universfield_ambient_space_background_350710.mp3"],
    "boss_light": ["music_09_boss_light_monume_space_cosmic_547903.mp3"],
    "boss_laser": ["music_10_boss_laser_delosound_space_ambient_351305.mp3"],
    "boss_overmind": ["music_11_boss_overmind_the_mountain_space_438391.mp3"],
    "boss_rift": ["music_12_boss_rift_universfield_ambient_space_background_30s_342767.mp3"],
    "boss_sun_eater": ["music_13_boss_sun_eater_playstarz_music_space_ambient_cinematic_543885.mp3"],
    "boss_eden": ["music_14_boss_eden_delosound_space_ambient_cinematic_351304.mp3"],
    "victory_loot": ["music_15_victory_loot_sigmamusicart_space_ambient_background_music_462074.mp3"],
    "legacy": ["musica1.mp3", "musica2.mp3"]
}

MUSIC_VOLUMES = {
    "menu": 0.75,
    "scale_0": 0.92,
    "cockpit": 0.86,
    "victory_loot": 0.82,
    "boss_light": 0.92,
    "boss_laser": 0.92,
    "boss_overmind": 0.94,
    "boss_rift": 0.94,
    "boss_sun_eater": 0.96,
    "boss_eden": 0.95
}

cancion_actual = None
music_context_actual = None
scale0_music_active = False

def pistas_disponibles(contexto):
    pistas = MUSIC_TRACKS.get(contexto, [])
    disponibles = [p for p in pistas if os.path.exists(ruta_recurso(p))]
    if disponibles:
        return disponibles
    return [p for p in MUSIC_TRACKS.get("legacy", []) if os.path.exists(ruta_recurso(p))]

def reproducir_musica_contexto(contexto, fade_ms=900, loop=True, force=False):
    global cancion_actual, music_context_actual, scale0_music_active
    if not AUDIO_OK:
        return
    if contexto == music_context_actual and pygame.mixer.music.get_busy() and not force:
        return

    pistas = pistas_disponibles(contexto)
    if not pistas:
        return

    nueva = random.choice(pistas)
    if len(pistas) > 1:
        intentos = 0
        while nueva == cancion_actual and intentos < 8:
            nueva = random.choice(pistas)
            intentos += 1

    try:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(max(120, fade_ms // 2))
        pygame.mixer.music.load(ruta_recurso(nueva))
        volumen_contexto = MUSIC_VOLUMES.get(contexto, 0.84)
        pygame.mixer.music.set_volume(max(0.0, min(1.0, musica_volumen * volumen_contexto)))
        pygame.mixer.music.play(-1 if loop else 0, fade_ms=fade_ms)
        cancion_actual = nueva
        music_context_actual = contexto
        scale0_music_active = (contexto == "scale_0")
    except Exception as e:
        print("Error reproduciendo:", nueva, e)

def reproducir_siguiente():
    reproducir_musica_contexto("level_default", fade_ms=900, force=True)

def reproducir_musica_scale0():
    reproducir_musica_contexto("scale_0", fade_ms=1000, force=True)
    reproducir_sfx("scale0", volumen_extra=0.75, force=True)

def restaurar_musica_normal():
    global scale0_music_active
    scale0_music_active = False
    reproducir_musica_contexto("level_default", fade_ms=850, force=True)

def contexto_musical_boss_activo():
    if estado.get("boss_laser"):
        return "boss_laser"
    if estado.get("boss_overmind"):
        return "boss_overmind"
    if estado.get("boss_rift"):
        return "boss_rift"
    if estado.get("boss_sun_eater"):
        return "boss_sun_eater"
    if estado.get("boss_eden"):
        return "boss_eden"
    if estado.get("boss") or estado.get("boss_final") or estado.get("boss_hollow"):
        return "boss_light"
    return None

def actualizar_musica_dinamica():
    if not AUDIO_OK or "estado" not in globals():
        return
    fase = estado.get("estado", "MENU")
    if fase == "MENU":
        reproducir_musica_contexto("menu", fade_ms=900)
    elif fase == "BOSS_LOOT":
        reproducir_musica_contexto("victory_loot", fade_ms=650)
    elif fase in WORMHOLE_STATES:
        reproducir_musica_contexto("scale_0", fade_ms=1000)
    elif fase == "JUGANDO":
        if estado.get("boss_intro",0) > 0 and estado.get("cockpit_scan",{}).get("active",False):
            reproducir_musica_contexto("cockpit", fade_ms=650)
            return
        contexto_boss = contexto_musical_boss_activo()
        if contexto_boss:
            reproducir_musica_contexto(contexto_boss, fade_ms=850)
            return
        reproducir_musica_contexto(planeta_seleccionado or "level_default", fade_ms=900)
    elif fase in ["PLANETAS", "OPCIONES", "TIENDA", "CONTROLES", "INFO", "PERFIL", "MISIONES", "LOGROS", "MEJORAS", "DIARIAS", "DIFICULTAD", "CODEX"]:
        reproducir_musica_contexto("menu", fade_ms=900)

reproducir_musica_contexto("menu", fade_ms=700, force=True)

# =====================
# EFECTOS DE SONIDO
# =====================

SFX_MASTER_VOLUME = 0.38
SFX_FILES = {
    "player_shot":"sfx_player_laser_shot_ribhavagrawal_230500.mp3",
    "laser_charge":"sfx_laser_charge_gregorquendel_175727.mp3",
    "cockpit_scan":"sfx_cockpit_scanner_daviddumaisaudio_194042.mp3",
    "cockpit_boot":"sfx_cockpit_system_boot_1nm0rtal_495230.mp3",
    "dash":"sfx_dash_swipe_dragonstudio_405451.mp3",
    "transition":"sfx_cinematic_transition_whoosh_rescopicsound_228295.mp3",
    "explosion":"sfx_sci_fi_explosion_09_daviddumaisaudio_190268.mp3",
    "boss_charge":"sfx_boss_weapon_charging_freesoundcommunity_96645.mp3",
    "player_hit":"sfx_player_damage_hit_ribhavagrawal_230510.mp3",
    "metal_hit":"sfx_asteroid_metal_hit_floraphonic_193281.mp3",
    "boss_intro":"sfx_boss_intro_riser_audiopapkin_289802.mp3",
    "shield_hit":"sfx_shield_impact_yodguard_382411.mp3",
    "shield_pickup":"sfx_shield_pickup_freesoundcommunity_81574.mp3",
    "coin":"sfx_coin_received_ribhavagrawal_230517.mp3",
    "loot":"sfx_boss_loot_collect_yodguard_540190.mp3",
    "pickup":"sfx_quick_pickup_freesoundcommunity_98269.mp3",
    "scale0":"sfx_scale0_alien_resonance_fnxsound_287338.mp3"
}

SFX_SETTINGS = {
    "player_shot":(0.18, 55),
    "laser_charge":(0.34, 360),
    "cockpit_scan":(0.16, 260),
    "cockpit_boot":(0.28, 520),
    "dash":(0.25, 130),
    "transition":(0.23, 900),
    "explosion":(0.30, 130),
    "boss_charge":(0.26, 460),
    "player_hit":(0.34, 240),
    "metal_hit":(0.26, 95),
    "boss_intro":(0.34, 1200),
    "shield_hit":(0.26, 260),
    "shield_pickup":(0.26, 350),
    "coin":(0.14, 90),
    "loot":(0.30, 420),
    "pickup":(0.20, 170),
    "scale0":(0.30, 1200)
}

sfx_cache = {}
sfx_last_played = {}

def cargar_sfx(nombre):
    if not AUDIO_OK:
        return None
    archivo = SFX_FILES.get(nombre)
    if not archivo:
        return None
    ruta = ruta_recurso(archivo)
    if not os.path.exists(ruta):
        return None
    try:
        snd = pygame.mixer.Sound(ruta)
        sfx_cache[nombre] = snd
        return snd
    except Exception as e:
        print("No se pudo cargar SFX:", archivo, e)
        sfx_cache[nombre] = None
        return None

def reproducir_sfx(nombre, volumen_extra=1.0, force=False):
    if not AUDIO_OK:
        return
    ahora = pygame.time.get_ticks()
    volumen_base, cooldown = SFX_SETTINGS.get(nombre, (0.22, 120))
    if not force and ahora - sfx_last_played.get(nombre, -999999) < cooldown:
        return
    snd = sfx_cache.get(nombre)
    if nombre not in sfx_cache:
        snd = cargar_sfx(nombre)
    if snd is None:
        return
    try:
        snd.set_volume(max(0.0, min(1.0, musica_volumen * SFX_MASTER_VOLUME * volumen_base * volumen_extra)))
        snd.play()
        sfx_last_played[nombre] = ahora
    except Exception:
        pass

# =====================
# IMAGENES
# =====================
menu_bg = cargar_imagen("menu_bg.png", (ANCHO,ALTO), (10,10,25))
options_bg = cargar_imagen("options_bg.png", (ANCHO,ALTO), (20,20,40))
ship_select_bg = cargar_imagen("ship_select_bg.png", (ANCHO,ALTO), (20,20,40))

nave_img = cargar_imagen("nave.png", (60,60), (0,180,255))
nave2_img = cargar_imagen("nave2.png", (60,60), (255,255,255))
nave_crimson_img = cargar_imagen("nave_crimson.png", (60,60), (255,40,40))
nave_nova_img = cargar_imagen("nave_nova.png", (60,60), (80,220,255))
nave_phantom_img = cargar_imagen("nave_phantom.png", (60,60), (180,70,255))
nave_eclipse_img = cargar_imagen("nave_eclipse.png", (60,60), (255,90,40))
nave_aurora_img = cargar_imagen("nave_aurora.png", (60,60), (80,255,180))
nave_quantum_img = cargar_imagen("nave_quantum.png", (60,60), (190,90,255))

nave_preview_img = cargar_imagen("nave.png", (150,150), (0,180,255))
nave2_preview_img = cargar_imagen("nave2.png", (150,150), (255,255,255))
nave_crimson_preview_img = cargar_imagen("nave_crimson.png", (95,95), (255,40,40))
nave_nova_preview_img = cargar_imagen("nave_nova.png", (95,95), (80,220,255))
nave_phantom_preview_img = cargar_imagen("nave_phantom.png", (95,95), (180,70,255))
nave_eclipse_preview_img = cargar_imagen("nave_eclipse.png", (95,95), (255,90,40))
nave_aurora_preview_img = cargar_imagen("nave_aurora.png", (95,95), (80,255,180))
nave_quantum_preview_img = cargar_imagen("nave_quantum.png", (95,95), (190,90,255))

moneda_img = cargar_imagen("moneda.png", (30,30), (255,220,60))

asteroid_img = cargar_imagen("asteroid_normal.png", (50,50), (120,120,120))
alien_img = cargar_imagen("alien.png", (80,80), (0,255,0))
drone_img = cargar_imagen("drone.png", (50,50), (255,255,0))
zigzag_img = cargar_imagen("zigzag.png", (80,80), (255,120,0))
crucero_img = cargar_imagen("crucero.png", (80,80), (120,120,255))
boss_img = cargar_imagen("boss.png", (170,170), (255,0,0))
boss_final_img = cargar_imagen("boss_final.png", (170,170), (180,0,255))

corazon_img = cargar_imagen("corazon.png", (30,30), (255,0,0))
bala_enemiga_img = cargar_imagen("bala_enemiga.png", (20,20), (255,60,60))
bala_boss_final_img = cargar_imagen("bala_boss_final.png", (30,30), (255,0,255))
phantom_img = cargar_imagen("phantom.png", (65,65), (160,160,255))
orb_img = cargar_imagen("orb.png", (50,50), (100,0,255))
gravity_img = cargar_imagen("gravity.png", (70,70), (0,120,255))

# NUEVOS ENEMIGOS
sentinel_img = cargar_imagen("sentinel.png", (70,70), (255,80,80))
hunter_img = cargar_imagen("hunter.png", (65,65), (255,180,0))
void_orb_img = cargar_imagen("void_orb.png", (70,70), (130,0,200))
laser_satellite_img = cargar_imagen("laser_satellite.png", (80,50), (255,40,40))

# NUEVO BOSS LASER
boss_laser_img = cargar_imagen("boss_laser.png", (190,190), (255,30,30))

# NIVEL 5 - THE VOID SWARM
parasite_img = cargar_imagen("parasite.png", (45,45), (190,40,255))
hive_img = cargar_imagen("hive.png", (90,90), (120,0,180))
shadow_phantom2_img = cargar_imagen("shadow_phantom.png", (70,70), (80,0,120))
leech_drone_img = cargar_imagen("leech_drone.png", (60,60), (180,0,255))
boss_overmind_img = cargar_imagen("boss_overmind.png", (210,210), (180,0,255))

# NIVEL 6 - QUANTUM RIFT
rift_splitter_img = cargar_imagen("rift_splitter.png", (70,70), (80,220,255))
phase_reaper_img = cargar_imagen("phase_reaper.png", (75,75), (190,90,255))
chrono_mine_img = cargar_imagen("chrono_mine.png", (60,60), (255,210,80))
boss_rift_monarch_img = cargar_imagen("boss_rift_monarch.png", (220,220), (80,220,255))

abyss_wisp_img = cargar_imagen("abyss_wisp.png", (58,58), (35,200,255))
null_seeker_img = cargar_imagen("null_seeker.png", (65,65), (35,90,180))
void_lantern_img = cargar_imagen("void_lantern.png", (78,78), (90,230,255))
solar_mantis_img = cargar_imagen("solar_mantis.png", (68,68), (255,150,35))
flare_drone_img = cargar_imagen("flare_drone.png", (62,62), (255,120,40))
helio_spire_img = cargar_imagen("helio_spire.png", (80,80), (255,205,70))
bloom_parasite_img = cargar_imagen("bloom_parasite.png", (50,50), (90,255,170))
crystal_seraph_img = cargar_imagen("crystal_seraph.png", (75,75), (190,255,240))
root_hydra_img = cargar_imagen("root_hydra.png", (90,90), (70,230,150))
boss_hollow_saint_img = cargar_imagen("boss_hollow_saint.png", (230,230), (35,220,255))
boss_sun_eater_img = cargar_imagen("boss_sun_eater.png", (230,230), (255,145,35))
boss_eden_prime_img = cargar_imagen("boss_eden_prime.png", (230,230), (90,255,180))

# =====================
# BOTONES
# =====================
MENU_BTN_W = 100
MENU_BTN_H = 30
MENU_GAP = 10
MENU_ROW1_Y = 425
MENU_ROW2_Y = 465
MENU_ROW1_X = 20
MENU_ROW2_X = 20

start_btn = hd_rect(MENU_ROW1_X + 0*(MENU_BTN_W+MENU_GAP), MENU_ROW1_Y, MENU_BTN_W, MENU_BTN_H)
options_btn = hd_rect(MENU_ROW1_X + 1*(MENU_BTN_W+MENU_GAP), MENU_ROW1_Y, MENU_BTN_W, MENU_BTN_H)
shop_btn = hd_rect(MENU_ROW1_X + 2*(MENU_BTN_W+MENU_GAP), MENU_ROW1_Y, MENU_BTN_W, MENU_BTN_H)
controls_btn = hd_rect(MENU_ROW1_X + 3*(MENU_BTN_W+MENU_GAP), MENU_ROW1_Y, MENU_BTN_W, MENU_BTN_H)
language_btn = hd_rect(MENU_ROW1_X + 4*(MENU_BTN_W+MENU_GAP), MENU_ROW1_Y, MENU_BTN_W, MENU_BTN_H)
info_btn = hd_rect(MENU_ROW1_X + 5*(MENU_BTN_W+MENU_GAP), MENU_ROW1_Y, MENU_BTN_W, MENU_BTN_H)
profile_btn = hd_rect(MENU_ROW1_X + 6*(MENU_BTN_W+MENU_GAP), MENU_ROW1_Y, MENU_BTN_W, MENU_BTN_H)

difficulty_btn = hd_rect(MENU_ROW2_X + 0*(MENU_BTN_W+MENU_GAP), MENU_ROW2_Y, MENU_BTN_W, MENU_BTN_H)
missions_btn = hd_rect(MENU_ROW2_X + 1*(MENU_BTN_W+MENU_GAP), MENU_ROW2_Y, MENU_BTN_W, MENU_BTN_H)
codex_btn = hd_rect(MENU_ROW2_X + 2*(MENU_BTN_W+MENU_GAP), MENU_ROW2_Y, MENU_BTN_W, MENU_BTN_H)
achievements_btn = hd_rect(MENU_ROW2_X + 3*(MENU_BTN_W+MENU_GAP), MENU_ROW2_Y, MENU_BTN_W, MENU_BTN_H)
upgrades_btn = hd_rect(MENU_ROW2_X + 4*(MENU_BTN_W+MENU_GAP), MENU_ROW2_Y, MENU_BTN_W, MENU_BTN_H)
daily_btn = hd_rect(MENU_ROW2_X + 5*(MENU_BTN_W+MENU_GAP), MENU_ROW2_Y, MENU_BTN_W, MENU_BTN_H)
quit_btn = hd_rect(MENU_ROW2_X + 6*(MENU_BTN_W+MENU_GAP), MENU_ROW2_Y, MENU_BTN_W, MENU_BTN_H)
planet_btn = hd_rect(335, 505, 130, 30)

planet_back_btn = hd_rect(280,520,240,55)
planet_left_btn = hd_rect(95,270,78,58)
planet_right_btn = hd_rect(627,270,78,58)
planet_select_btn = hd_rect(280,455,240,46)

# Botones internos del menï¿½ de selecciï¿½n de nave.
ship1_btn = hd_rect(100,155,260,315)
ship2_btn = hd_rect(440,155,260,315)
options_back_btn = hd_rect(280,500,240,65)

# Botones de idioma.
spanish_btn = hd_rect(165,245,210,90)
english_btn = hd_rect(425,245,210,90)
language_back_btn = hd_rect(280,500,240,65)

# Botones de tienda.
shop_back_btn = hd_rect(280,515,240,55)
shop_ship_buttons = {
    3:hd_rect(45,120,115,145),
    4:hd_rect(170,120,115,145),
    5:hd_rect(295,120,115,145),
    6:hd_rect(420,120,115,145),
    7:hd_rect(545,120,115,145),
    8:hd_rect(670,120,115,145)
}

shop_ability_buttons = {
    "triple_shot":hd_rect(45,325,115,95),
    "auto_shield":hd_rect(170,325,115,95),
    "energy_core":hd_rect(295,325,115,95),
    "coin_booster":hd_rect(420,325,115,95),
    "revive_core":hd_rect(545,325,115,95),
    "ultimate_core":hd_rect(670,325,115,95)
}

info_back_btn = hd_rect(280,520,240,55)

# Botones de dificultad.
profile_back_btn = hd_rect(280,520,240,55)
missions_back_btn = hd_rect(280,520,240,55)
codex_back_btn = hd_rect(280,520,240,55)
codex_v64_selected = 0
codex_v64_scroll = 0
codex_v64_buttons = [hd_rect(52,128+i*58,210,46) for i in range(6)]

mission_buttons = {
    "destroy_50":hd_rect(575,145,120,34),
    "score_100k":hd_rect(575,225,120,34),
    "boss_1":hd_rect(575,305,120,34),
    "coins_25k":hd_rect(575,385,120,34)
}

achievement_buttons = {
    "first_boss":hd_rect(575,112,120,30),
    "hunter_250":hd_rect(575,182,120,30),
    "score_500k":hd_rect(575,252,120,30),
    "rift_5":hd_rect(575,322,120,30),
    "millionaire":hd_rect(575,392,120,30)
}

upgrade_buttons = {
    "hp":hd_rect(575,170,120,34),
    "cooldown":hd_rect(575,270,120,34),
    "coin":hd_rect(575,370,120,34)
}

daily_buttons = {
    "daily_kills":hd_rect(575,145,120,34),
    "daily_score":hd_rect(575,225,120,34),
    "daily_boss":hd_rect(575,305,120,34),
    "daily_coins":hd_rect(575,385,120,34)
}

difficulty_back_btn = hd_rect(280,520,240,55)
difficulty_buttons = {
    "facil":hd_rect(80,150,300,86),
    "normal":hd_rect(420,150,300,86),
    "dificil":hd_rect(80,255,300,86),
    "muy_dificil":hd_rect(420,255,300,86)
}
game_mode_buttons = {
    "solo":hd_rect(35,405,175,72),
    "coop":hd_rect(220,405,175,72),
    "online_host":hd_rect(405,405,175,72),
    "online_join":hd_rect(590,405,175,72)
}

# Botï¿½n de vuelta para controles.
controls_back_btn = hd_rect(280,510,240,55)

# Botones para reasignar teclas dentro de CONTROLES.
control_action_buttons = {
    # Jugador 1
    "move_up":hd_rect(90,155,155,24),
    "move_left":hd_rect(90,183,155,24),
    "move_down":hd_rect(90,211,155,24),
    "move_right":hd_rect(90,239,155,24),
    "shoot":hd_rect(90,267,155,24),
    "dash":hd_rect(90,295,155,24),
    "special_laser":hd_rect(90,323,155,24),
    "pulse":hd_rect(90,351,155,24),
    "ultimate_overdrive":hd_rect(90,379,155,24),
    "ultimate_blackhole":hd_rect(90,407,155,24),
    "ultimate_orbital":hd_rect(90,435,155,24),

    # Jugador 2
    "p2_move_up":hd_rect(410,155,155,24),
    "p2_move_left":hd_rect(410,183,155,24),
    "p2_move_down":hd_rect(410,211,155,24),
    "p2_move_right":hd_rect(410,239,155,24),
    "p2_shoot":hd_rect(410,267,155,24),
    "p2_dash":hd_rect(410,295,155,24),
    "p2_special_laser":hd_rect(410,323,155,24),
    "p2_pulse":hd_rect(410,351,155,24),
    "p2_ultimate_overdrive":hd_rect(410,379,155,24),
    "p2_ultimate_blackhole":hd_rect(410,407,155,24),
    "p2_ultimate_orbital":hd_rect(410,435,155,24),
}
reset_keys_btn = hd_rect(300,475,200,36)

def aplicar_layout_hd_menus():
    global ship1_btn, ship2_btn, options_back_btn
    global spanish_btn, english_btn, language_back_btn
    global shop_back_btn, shop_ship_buttons, shop_ability_buttons
    global info_back_btn, profile_back_btn, missions_back_btn, codex_back_btn
    global codex_v64_buttons, mission_buttons, achievement_buttons, upgrade_buttons, daily_buttons
    global difficulty_back_btn, difficulty_buttons, game_mode_buttons
    global controls_back_btn, control_action_buttons, reset_keys_btn

    back_w, back_h = 290, 58
    back_y = ALTO - 92
    centered_back = pygame.Rect(ANCHO//2 - back_w//2, back_y, back_w, back_h)

    options_back_btn = centered_back.copy()
    language_back_btn = centered_back.copy()
    shop_back_btn = centered_back.copy()
    info_back_btn = centered_back.copy()
    profile_back_btn = centered_back.copy()
    missions_back_btn = centered_back.copy()
    codex_back_btn = centered_back.copy()
    difficulty_back_btn = centered_back.copy()
    controls_back_btn = centered_back.copy()

    ship1_btn = pygame.Rect(ANCHO//2 - 445, 175, 350, 350)
    ship2_btn = pygame.Rect(ANCHO//2 + 95, 175, 350, 350)

    spanish_btn = pygame.Rect(ANCHO//2 - 300, 300, 260, 105)
    english_btn = pygame.Rect(ANCHO//2 + 40, 300, 260, 105)

    shop_card_w, shop_card_h, shop_gap = 145, 172, 20
    shop_start_x = ANCHO//2 - ((shop_card_w*6 + shop_gap*5)//2)
    shop_ship_buttons = {
        3: pygame.Rect(shop_start_x + 0*(shop_card_w+shop_gap), 165, shop_card_w, shop_card_h),
        4: pygame.Rect(shop_start_x + 1*(shop_card_w+shop_gap), 165, shop_card_w, shop_card_h),
        5: pygame.Rect(shop_start_x + 2*(shop_card_w+shop_gap), 165, shop_card_w, shop_card_h),
        6: pygame.Rect(shop_start_x + 3*(shop_card_w+shop_gap), 165, shop_card_w, shop_card_h),
        7: pygame.Rect(shop_start_x + 4*(shop_card_w+shop_gap), 165, shop_card_w, shop_card_h),
        8: pygame.Rect(shop_start_x + 5*(shop_card_w+shop_gap), 165, shop_card_w, shop_card_h),
    }

    ability_h = 120
    shop_ability_buttons = {
        "triple_shot": pygame.Rect(shop_start_x + 0*(shop_card_w+shop_gap), 430, shop_card_w, ability_h),
        "auto_shield": pygame.Rect(shop_start_x + 1*(shop_card_w+shop_gap), 430, shop_card_w, ability_h),
        "energy_core": pygame.Rect(shop_start_x + 2*(shop_card_w+shop_gap), 430, shop_card_w, ability_h),
        "coin_booster": pygame.Rect(shop_start_x + 3*(shop_card_w+shop_gap), 430, shop_card_w, ability_h),
        "revive_core": pygame.Rect(shop_start_x + 4*(shop_card_w+shop_gap), 430, shop_card_w, ability_h),
        "ultimate_core": pygame.Rect(shop_start_x + 5*(shop_card_w+shop_gap), 430, shop_card_w, ability_h),
    }

    codex_list_x = ANCHO//2 - 520
    btn_x = ANCHO//2 + 300
    mission_buttons = {
        "destroy_50": pygame.Rect(btn_x, 157, 155, 40),
        "score_100k": pygame.Rect(btn_x, 237, 155, 40),
        "boss_1": pygame.Rect(btn_x, 317, 155, 40),
        "coins_25k": pygame.Rect(btn_x, 397, 155, 40),
    }
    daily_buttons = {
        "daily_kills": pygame.Rect(btn_x, 157, 155, 40),
        "daily_score": pygame.Rect(btn_x, 237, 155, 40),
        "daily_boss": pygame.Rect(btn_x, 317, 155, 40),
        "daily_coins": pygame.Rect(btn_x, 397, 155, 40),
    }
    achievement_buttons = {
        "first_boss": pygame.Rect(btn_x, 119, 155, 38),
        "hunter_250": pygame.Rect(btn_x, 189, 155, 38),
        "score_500k": pygame.Rect(btn_x, 259, 155, 38),
        "rift_5": pygame.Rect(btn_x, 329, 155, 38),
        "millionaire": pygame.Rect(btn_x, 399, 155, 38),
    }
    upgrade_buttons = {
        "hp": pygame.Rect(btn_x, 174, 155, 40),
        "cooldown": pygame.Rect(btn_x, 274, 155, 40),
        "coin": pygame.Rect(btn_x, 374, 155, 40),
    }

    codex_v64_buttons = [pygame.Rect(codex_list_x, 158+i*62, 300, 52) for i in range(6)]

    difficulty_buttons = {
        "facil": pygame.Rect(ANCHO//2 - 405, 190, 360, 96),
        "normal": pygame.Rect(ANCHO//2 + 45, 190, 360, 96),
        "dificil": pygame.Rect(ANCHO//2 - 405, 310, 360, 96),
        "muy_dificil": pygame.Rect(ANCHO//2 + 45, 310, 360, 96),
    }
    game_mode_buttons = {
        "solo": pygame.Rect(ANCHO//2 - 510, 470, 230, 76),
        "coop": pygame.Rect(ANCHO//2 - 255, 470, 230, 76),
        "online_host": pygame.Rect(ANCHO//2, 470, 230, 76),
        "online_join": pygame.Rect(ANCHO//2 + 255, 470, 230, 76),
    }

    p1_x = ANCHO//2 - 430
    p2_x = ANCHO//2 + 95
    control_action_buttons = {}
    acciones_base = [
        "move_up", "move_left", "move_down", "move_right", "shoot", "dash",
        "special_laser", "pulse", "ultimate_overdrive", "ultimate_blackhole", "ultimate_orbital"
    ]
    for i, accion in enumerate(acciones_base):
        control_action_buttons[accion] = pygame.Rect(p1_x, 165+i*31, 280, 26)
        control_action_buttons["p2_" + accion] = pygame.Rect(p2_x, 165+i*31, 280, 26)
    reset_keys_btn = pygame.Rect(ANCHO//2 - 110, 565, 220, 42)

aplicar_layout_hd_menus()

# =====================
# EFECTOS
# =====================
particulas=[]
shake=0
flash=0
hitstop=0
slowmo=1
slowmo_timer = 0

WORMHOLE_STATES = ["WORMHOLE_ENTER", "WORMHOLE_TRAVEL", "PLANET_APPROACH", "PLANET_DESCENT", "SCALE0_LORE", "PLANET_WALK", "SCALE0_DIRECT_INTRO", "SCALE0_MAZE", "SCALE0_RELIC_ROOM", "SCALE0_ESCAPE", "SCALE0_REWARD", "SCALE0_RETURN"]

# =====================
# EFECTOS VISUALES AVANZADOS
# =====================
ondas_expansion=[]
destellos=[]
estelas_nave=[]
particulas_energia=[]
chispas_cineticas=[]
trazos_luz=[]
micro_polvo=[]

def color_nivel_v59(nivel):
    if nivel <= 1:
        return (45,110,255)
    if nivel == 2:
        return (125,70,255)
    if nivel == 3:
        return (100,90,255)
    if nivel == 4:
        return (255,70,70)
    if nivel == 5:
        return (185,55,255)
    if nivel == 6:
        return (90,230,255)
    if nivel == 7:
        return (45,190,255)
    if nivel == 8:
        return (255,165,45)
    return (90,255,180)

def crear_glow(superficie, x, y, radio, color, alpha=55):
    glow = pygame.Surface((radio*2, radio*2), pygame.SRCALPHA)
    pygame.draw.circle(glow, (color[0], color[1], color[2], alpha), (radio, radio), radio)
    superficie.blit(glow, (x-radio, y-radio))

def crear_rect_glow(superficie, rect, color, alpha=55, expansion=18):
    glow = pygame.Surface((rect[2]+expansion*2, rect[3]+expansion*2), pygame.SRCALPHA)
    pygame.draw.rect(
        glow,
        (color[0], color[1], color[2], alpha),
        (0,0,rect[2]+expansion*2,rect[3]+expansion*2),
        border_radius=8
    )
    superficie.blit(glow, (rect[0]-expansion, rect[1]-expansion))

def crear_luz_aditiva(superficie, x, y, radio, color, alpha=55):
    radio = max(2, int(radio))
    luz = pygame.Surface((radio*2, radio*2), pygame.SRCALPHA)
    for i in range(5, 0, -1):
        r = int(radio * i / 5)
        a = int(alpha * (i / 5) * 0.16)
        pygame.draw.circle(luz, (color[0], color[1], color[2], a), (radio, radio), r)
    superficie.blit(luz, (int(x-radio), int(y-radio)))

def emitir_particulas_energia(x, y, color, cantidad=8, fuerza=3.0, vida=(18,34), tam=2):
    for _ in range(cantidad):
        ang = random.uniform(0, math.pi*2)
        vel = random.uniform(0.6, fuerza)
        particulas_energia.append({
            "x":x,
            "y":y,
            "vx":math.cos(ang)*vel,
            "vy":math.sin(ang)*vel,
            "vida":random.randint(vida[0], vida[1]),
            "max":vida[1],
            "color":color,
            "tam":tam
        })
    if len(particulas_energia) > 650:
        del particulas_energia[:len(particulas_energia)-650]

def emitir_chispas_cineticas(x, y, color, cantidad=10, fuerza=4.0, vida=(12,26), tam=2):
    for _ in range(cantidad):
        ang = random.uniform(0, math.pi*2)
        vel = random.uniform(1.0, fuerza)
        chispas_cineticas.append({
            "x": x,
            "y": y,
            "px": x,
            "py": y,
            "vx": math.cos(ang) * vel,
            "vy": math.sin(ang) * vel,
            "vida": random.randint(vida[0], vida[1]),
            "max": vida[1],
            "color": color,
            "tam": tam
        })
    if len(chispas_cineticas) > 900:
        del chispas_cineticas[:len(chispas_cineticas)-900]

def emitir_trazo_luz(x1, y1, x2, y2, color, vida=12, grosor=2):
    trazos_luz.append({
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "vida": vida,
        "max": vida,
        "color": color,
        "grosor": grosor
    })
    if len(trazos_luz) > 240:
        del trazos_luz[:len(trazos_luz)-240]

def emitir_micro_polvo(x, y, color, cantidad=4):
    for _ in range(cantidad):
        micro_polvo.append({
            "x": x + random.uniform(-12, 12),
            "y": y + random.uniform(-12, 12),
            "vx": random.uniform(-0.25, 0.25),
            "vy": random.uniform(0.35, 1.2),
            "vida": random.randint(45, 95),
            "max": 95,
            "color": color,
            "r": random.choice([1, 1, 2])
        })
    if len(micro_polvo) > 260:
        del micro_polvo[:len(micro_polvo)-260]

def actualizar_particulas_energia():
    for p in particulas_energia:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["vx"] *= 0.96
        p["vy"] *= 0.96
        p["vida"] -= 1
    particulas_energia[:] = [p for p in particulas_energia if p["vida"] > 0]

def dibujar_particulas_energia(offset_x, offset_y):
    for p in particulas_energia:
        ratio = max(0, min(1, p["vida"]/max(1,p["max"])))
        color = p["color"]
        x = int(p["x"] + offset_x)
        y = int(p["y"] + offset_y)
        crear_luz_aditiva(pantalla, x, y, 5 + p["tam"]*2, color, int(10*ratio))
        pygame.draw.circle(
            pantalla,
            mezclar_color(color,(255,255,255),0.45),
            (x,y),
            max(1,int(p["tam"]*ratio+1))
        )

def actualizar_fx_v73():
    for s in chispas_cineticas:
        s["px"] = s["x"]
        s["py"] = s["y"]
        s["x"] += s["vx"] * slowmo
        s["y"] += s["vy"] * slowmo
        s["vx"] *= 0.93
        s["vy"] = s["vy"] * 0.93 + 0.035
        s["vida"] -= 1
    chispas_cineticas[:] = [s for s in chispas_cineticas if s["vida"] > 0]

    for tr in trazos_luz:
        tr["vida"] -= 1
    trazos_luz[:] = [tr for tr in trazos_luz if tr["vida"] > 0]

    for p in micro_polvo:
        p["x"] += p["vx"] * slowmo
        p["y"] += p["vy"] * slowmo
        p["vida"] -= 1
    micro_polvo[:] = [p for p in micro_polvo if p["vida"] > 0 and -20 < p["y"] < ALTO + 30]

def dibujar_fx_detras_v73(offset_x, offset_y):
    capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    for tr in trazos_luz:
        ratio = max(0, tr["vida"] / max(1, tr["max"]))
        color = tr["color"]
        alpha = int(26 * ratio)
        pygame.draw.line(
            capa,
            (color[0], color[1], color[2], alpha),
            (int(tr["x1"]+offset_x), int(tr["y1"]+offset_y)),
            (int(tr["x2"]+offset_x), int(tr["y2"]+offset_y)),
            max(1, int(tr["grosor"] * ratio + 1))
        )

    for p in micro_polvo:
        ratio = max(0, p["vida"] / max(1, p["max"]))
        color = p["color"]
        pygame.draw.circle(
            capa,
            (color[0], color[1], color[2], int(34 * ratio)),
            (int(p["x"]+offset_x*0.25), int(p["y"]+offset_y*0.25)),
            p["r"]
        )
    pantalla.blit(capa, (0,0))

def dibujar_fx_delante_v73(offset_x, offset_y):
    capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    for s in chispas_cineticas:
        ratio = max(0, s["vida"] / max(1, s["max"]))
        color = s["color"]
        alpha = int(95 * ratio)
        x = int(s["x"] + offset_x)
        y = int(s["y"] + offset_y)
        px = int(s["px"] + offset_x)
        py = int(s["py"] + offset_y)
        pygame.draw.line(capa, (color[0], color[1], color[2], alpha), (px, py), (x, y), max(1, int(s["tam"])))
        pygame.draw.circle(capa, (255,255,255, int(35*ratio)), (x, y), max(1, int(s["tam"]*ratio)))
    pantalla.blit(capa, (0,0))

def dibujar_luces_dinamicas_v59(nivel, offset_x, offset_y):
    return
    luces = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    color_nave = color_nave_por_tipo(estado.get("nave_tipo",1))
    crear_luz_aditiva(luces, estado["nave_x"]+30+offset_x, estado["nave_y"]+30+offset_y, 28, color_nave, 7)
    if estado.get("coop",False):
        crear_luz_aditiva(luces, estado["nave2_x"]+25+offset_x, estado["nave2_y"]+25+offset_y, 26, color_nave_por_tipo(estado.get("nave2_tipo",2)), 6)

    for b in estado.get("balas",[])[:80]:
        crear_luz_aditiva(luces, b[0]+offset_x, b[1]+offset_y, 10, (90,210,255), 6)

    for b in estado.get("balas_enemigas",[])[:80]:
        color_b = (255,80,80)
        if len(b) > 4 and b[4] == "solar":
            color_b = (255,185,65)
        elif len(b) > 4 and b[4] == "rift":
            color_b = (90,230,255)
        elif len(b) > 4 and b[4] == "eden":
            color_b = (120,255,190)
        elif "boss_final" in b:
            color_b = (220,80,255)
        crear_luz_aditiva(luces, b[0]+offset_x, b[1]+offset_y, 11, color_b, 6)

    for en in estado.get("enemigos",[])[:14]:
        crear_luz_aditiva(luces, en.get("x",0)+tamano_enemigo(en.get("tipo",""))//2+offset_x, en.get("y",0)+tamano_enemigo(en.get("tipo",""))//2+offset_y, 16, color_enemigo(en.get("tipo","")), 3)

    boss, tipo = obtener_boss_activo()
    if boss is not None:
        perfil = perfil_boss_visual(tipo)
        crear_luz_aditiva(luces, boss["x"]+perfil["cx"]+offset_x, boss["y"]+perfil["cy"]+offset_y, perfil["radio"]//2, perfil["color"], 8)

    luces.set_alpha(80)
    pantalla.blit(luces,(0,0),special_flags=pygame.BLEND_RGB_ADD)

def aplicar_postprocesado_v59(nivel):
    vignette = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    for i in range(7):
        alpha = 2 + i
        pygame.draw.rect(vignette,(0,0,0,alpha),(i*7,i*5,ANCHO-i*14,ALTO-i*10),1)
    pygame.draw.rect(vignette,(0,0,0,10),(0,0,ANCHO,ALTO),18)
    pantalla.blit(vignette,(0,0))

    # Scanlines muy ligeras, para textura arcade sin ensuciar demasiado.
    scan = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    for y in range(0,ALTO,4):
        pygame.draw.line(scan,(0,0,0,2),(0,y),(ANCHO,y))
    pantalla.blit(scan,(0,0))

def color_enemigo(tipo):
    mapa = {
        "asteroide":(150,150,160),
        "alien":(80,255,120),
        "drone":(255,230,70),
        "zigzag":(255,135,45),
        "crucero":(145,160,255),
        "phantom":(155,155,255),
        "orb":(150,55,255),
        "gravity":(70,170,255),
        "sentinel":(255,85,85),
        "hunter":(255,175,55),
        "void_orb":(170,70,255),
        "laser_satellite":(255,70,70),
        "parasite":(210,70,255),
        "hive":(165,40,220),
        "shadow_phantom":(155,75,255),
        "leech_drone":(220,45,255),
        "rift_splitter":(80,230,255),
        "quantum_shard":(130,245,255),
        "phase_reaper":(200,110,255),
        "chrono_mine":(255,220,80),
        "abyss_wisp":(55,210,255),
        "null_seeker":(70,120,210),
        "void_lantern":(100,240,255),
        "solar_mantis":(255,170,55),
        "flare_drone":(255,120,55),
        "helio_spire":(255,215,80),
        "bloom_parasite":(95,255,170),
        "crystal_seraph":(200,255,245),
        "root_hydra":(80,235,155)
    }
    return mapa.get(tipo, (120,180,255))

def tamano_enemigo(tipo):
    escala = HD_VISUAL_SCALE
    if tipo in ["sentinel","void_orb","rift_splitter","phase_reaper"]:
        return int(70 * escala)
    if tipo in ["laser_satellite","void_lantern","helio_spire","root_hydra"]:
        return int(80 * escala)
    if tipo in ["hive"]:
        return int(90 * escala)
    if tipo in ["quantum_shard"]:
        return int(38 * escala)
    if tipo in ["parasite","bloom_parasite"]:
        return int(45 * escala)
    if tipo in ["chrono_mine","flare_drone"]:
        return int(60 * escala)
    if tipo in ["hunter","phantom","null_seeker","solar_mantis","crystal_seraph"]:
        return int(65 * escala)
    return int(55 * escala)

def dibujar_aura_enemigo(en, offset_x, offset_y):
    tipo = en.get("tipo","")
    color = color_enemigo(tipo)
    tam = tamano_enemigo(tipo)
    cx = int(en.get("x",0) + tam/2 + offset_x)
    cy = int(en.get("y",0) + tam/2 + offset_y)
    pulso = 0.5 + 0.5 * abs(math.sin(pygame.time.get_ticks()/240 + cx*0.01))
    crear_glow(pantalla, cx, cy, int(tam*0.34 + pulso*5), color, 8 + int(6*pulso))
    if en.get("hit_flash",0) > 0:
        pygame.draw.circle(pantalla, (255,255,255), (cx,cy), max(8,int(tam*0.42)), 2)
        crear_glow(pantalla, cx, cy, max(16,int(tam*0.48)), (255,255,255), 22)

def dibujar_barra_boss_profesional(nombre, vida, vida_max, color, y=18):
    vida = max(0, vida)
    ratio = max(0, min(1, vida / max(1, vida_max)))
    ancho = int(640 * HD_VISUAL_SCALE)
    alto = int(24 * HD_VISUAL_SCALE)
    x = ANCHO//2 - ancho//2
    marco = pygame.Rect(x, y, ancho, alto)
    crear_rect_glow(pantalla, (marco.x,marco.y,marco.w,marco.h), color, 45, 10)
    pygame.draw.rect(pantalla, (4,8,18), marco, border_radius=7)
    pygame.draw.rect(pantalla, mezclar_color(color,(255,255,255),0.12), (x+3,y+3,int((ancho-6)*ratio),alto-6), border_radius=6)
    pygame.draw.rect(pantalla, (235,245,255), marco, 2, border_radius=7)
    brillo_x = x + int((ancho-8)*ratio)
    if ratio > 0.02:
        pygame.draw.line(pantalla, (255,255,255), (brillo_x,y+4), (brillo_x,y+alto-5), 2)
    etiqueta = pygame.font.SysFont(None,22).render(nombre, True, (235,245,255))
    pantalla.blit(etiqueta, (ANCHO//2 - etiqueta.get_width()//2, y + alto + 4))

def perfil_boss_visual(tipo):
    perfiles = {
        "boss":{
            "nombre":"ASTEROID COMMANDER",
            "color":(255,85,70),
            "max":200,
            "cx":85,
            "cy":85,
            "radio":104,
            "lados":6,
            "orb":6
        },
        "boss_final":{
            "nombre":"OMEGA DESTROYER",
            "color":(190,70,255),
            "max":400,
            "cx":85,
            "cy":85,
            "radio":118,
            "lados":4,
            "orb":8
        },
        "boss_laser":{
            "nombre":"LASER OVERLORD",
            "color":(255,55,55),
            "max":650,
            "cx":95,
            "cy":95,
            "radio":136,
            "lados":3,
            "orb":10
        },
        "boss_overmind":{
            "nombre":"THE OVERMIND",
            "color":(185,45,255),
            "max":750,
            "cx":105,
            "cy":105,
            "radio":152,
            "lados":7,
            "orb":11
        },
        "boss_rift":{
            "nombre":"THE RIFT MONARCH",
            "color":(80,225,255),
            "max":950,
            "cx":110,
            "cy":110,
            "radio":146,
            "lados":5,
            "orb":12
        },
        "boss_hollow":{
            "nombre":"THE HOLLOW SAINT",
            "color":(40,220,255),
            "max":1150,
            "cx":115,
            "cy":115,
            "radio":160,
            "lados":8,
            "orb":12
        },
        "boss_sun_eater":{
            "nombre":"THE SUN EATER",
            "color":(255,165,40),
            "max":1300,
            "cx":115,
            "cy":115,
            "radio":172,
            "lados":12,
            "orb":14
        },
        "boss_eden":{
            "nombre":"EDEN PRIME",
            "color":(90,255,180),
            "max":1500,
            "cx":115,
            "cy":115,
            "radio":172,
            "lados":9,
            "orb":12
        }
    }
    return perfiles.get(tipo, perfiles["boss"])

def fase_boss_visual(tipo, vida):
    max_vida = perfil_boss_visual(tipo)["max"]
    ratio = vida / max(1, max_vida)
    if ratio > 0.66:
        return 1
    if ratio > 0.33:
        return 2
    return 3

def marcar_boss_golpeado(boss, intensidad=1):
    boss["hit_flash"] = max(boss.get("hit_flash",0), 7 + intensidad)
    boss["impact_ripple"] = max(boss.get("impact_ripple",0), 16 + intensidad*3)
    cx = boss.get("x", 0) + 95
    cy = boss.get("y", 0) + 95
    emitir_chispas_cineticas(cx, cy, (255,205,115), 8 + intensidad*3, 5.0, (12,24), 2)
    emitir_particulas_energia(cx, cy, (255,180,80), 5 + intensidad, 3.8, (12,24), 2)
    emitir_trazo_luz(cx-random.randint(15,45), cy-random.randint(10,35), cx+random.randint(15,45), cy+random.randint(10,35), (255,170,80), 10, 2)

def actualizar_fase_boss_visual(tipo, boss, fase):
    global flash, shake, slowmo, slowmo_timer
    anterior = boss.get("visual_phase", fase)
    if anterior == fase:
        boss["visual_phase"] = fase
        return
    boss["visual_phase"] = fase
    perfil = perfil_boss_visual(tipo)
    color = perfil["color"]
    cx = boss["x"] + perfil["cx"]
    cy = boss["y"] + perfil["cy"]
    marcar_boss_golpeado(boss, 4)
    explosion_boss_cinematica(cx, cy, color)
    estado["ultimate_message"] = 110
    estado["ultimate_message_text"] = ("FASE DE FURIA " if idioma_actual != "EN" else "FURY PHASE ") + str(fase)
    flash = max(flash, 18 + fase*6)
    shake = max(shake, 24 + fase*8)
    slowmo = 1
    slowmo_timer = 0

def dibujar_sello_boss(cx, cy, radio, color, lados, rotacion, fase):
    puntos = []
    for i in range(lados):
        ang = rotacion + (math.pi*2*i/lados)
        puntos.append((int(cx+math.cos(ang)*radio), int(cy+math.sin(ang)*radio*0.62)))
    if len(puntos) >= 3:
        pygame.draw.polygon(pantalla, (color[0],color[1],color[2]), puntos, 2)
    for i,p in enumerate(puntos):
        pygame.draw.circle(pantalla, mezclar_color(color,(255,255,255),0.35), p, 4 + fase)
        if i % 2 == 0:
            pygame.draw.line(pantalla, (color[0],color[1],color[2]), (cx,cy), p, 1)

def dibujar_pre_boss(tipo, boss, offset_x, offset_y):
    perfil = perfil_boss_visual(tipo)
    color = perfil["color"]
    fase = fase_boss_visual(tipo, boss.get("vida", perfil["max"]))
    ticks = pygame.time.get_ticks()
    cx = int(boss["x"] + perfil["cx"] + offset_x)
    cy = int(boss["y"] + perfil["cy"] + offset_y)
    radio = perfil["radio"] + fase*12
    boss["hit_flash"] = max(0, boss.get("hit_flash",0)-1)
    boss["impact_ripple"] = max(0, boss.get("impact_ripple",0)-1)

    crear_glow(pantalla, cx, cy, radio + 18, color, 60 + fase*14)
    crear_glow(pantalla, cx, cy, max(70, radio//2), mezclar_color(color,(255,255,255),0.28), 42)

    rot = ticks*0.0017*(1 if tipo not in ["boss_rift","boss_hollow"] else -1)
    dibujar_sello_boss(cx, cy, radio, color, perfil["lados"], rot, fase)
    dibujar_sello_boss(cx, cy, int(radio*0.72), mezclar_color(color,(255,255,255),0.22), max(3,perfil["lados"]-2), -rot*1.45, fase)

    for i in range(perfil["orb"]):
        ang = ticks*0.0024 + i*math.pi*2/perfil["orb"]
        dist_x = radio*0.78 + math.sin(ticks*0.003+i)*12
        dist_y = radio*0.45 + math.cos(ticks*0.002+i)*8
        ox = int(cx + math.cos(ang)*dist_x)
        oy = int(cy + math.sin(ang)*dist_y)
        pygame.draw.circle(pantalla, color, (ox,oy), 4 + (i+fase)%3)
        if fase >= 2:
            pygame.draw.line(pantalla, (color[0],color[1],color[2]), (cx,cy), (ox,oy), 1)

    if tipo == "boss_laser":
        for dx in [-54,54]:
            pygame.draw.line(pantalla, (255,120,120), (cx+dx, cy-radio), (cx+dx, cy+radio), 2)
    elif tipo == "boss_overmind":
        for i in range(6):
            ang = ticks*0.002+i
            p1 = (int(cx+math.cos(ang)*60), int(cy+math.sin(ang)*44))
            p2 = (int(cx+math.cos(ang)*radio*0.92), int(cy+math.sin(ang)*radio*0.55))
            pygame.draw.line(pantalla, (210,95,255), p1, p2, 3)
    elif tipo == "boss_rift":
        for i in range(5):
            x = int(cx-radio + (ticks*0.19+i*53)%(radio*2))
            pygame.draw.line(pantalla, (80,240,255), (x,cy-radio//2), (x+34,cy+radio//2), 2)
    elif tipo == "boss_hollow":
        pygame.draw.circle(pantalla, (0,0,12), (cx,cy), max(38,radio//3))
        pygame.draw.circle(pantalla, (120,245,255), (cx,cy), max(42,radio//3), 2)
    elif tipo == "boss_sun_eater":
        for i in range(18):
            ang = ticks*0.003 + i*math.pi/9
            pygame.draw.line(
                pantalla,
                (255,210,75),
                (int(cx+math.cos(ang)*72), int(cy+math.sin(ang)*72)),
                (int(cx+math.cos(ang)*(radio+22)), int(cy+math.sin(ang)*(radio+22))),
                3
            )
    elif tipo == "boss_eden":
        for i in range(8):
            ang = ticks*0.002 + i*math.pi/4
            pygame.draw.polygon(
                pantalla,
                (140,255,210),
                [
                    (int(cx+math.cos(ang)*radio), int(cy+math.sin(ang)*radio*0.48)),
                    (int(cx+math.cos(ang+0.18)*(radio-24)), int(cy+math.sin(ang+0.18)*radio*0.42)),
                    (int(cx+math.cos(ang-0.18)*(radio-24)), int(cy+math.sin(ang-0.18)*radio*0.42))
                ],
                1
            )

    if boss.get("impact_ripple",0) > 0:
        r = int((18 - boss["impact_ripple"]) * 7 + radio*0.45)
        alpha_color = mezclar_color(color,(255,255,255),0.5)
        pygame.draw.circle(pantalla, alpha_color, (cx,cy), max(12,r), 3)

def dibujar_post_boss(tipo, boss, offset_x, offset_y):
    perfil = perfil_boss_visual(tipo)
    color = perfil["color"]
    cx = int(boss["x"] + perfil["cx"] + offset_x)
    cy = int(boss["y"] + perfil["cy"] + offset_y)
    if boss.get("hit_flash",0) > 0:
        fuerza = boss.get("hit_flash",0)
        pygame.draw.circle(pantalla, (255,255,255), (cx,cy), perfil["radio"]//2 + fuerza*4, 3)
        crear_glow(pantalla, cx, cy, perfil["radio"]//2 + fuerza*8, (255,255,255), 65)
    fase = fase_boss_visual(tipo, boss.get("vida", perfil["max"]))
    if fase == 3:
        texto = pygame.font.SysFont(None,20).render("PHASE III", True, mezclar_color(color,(255,255,255),0.4))
        pantalla.blit(texto, (cx-texto.get_width()//2, cy+perfil["radio"]//2+16))

def explosion_boss_cinematica(cx, cy, color):
    for r in [35,70,110,155,205]:
        ondas_expansion.append({"x":cx,"y":cy,"r":r,"vida":32,"max":r+240,"color":color})
    for _ in range(42):
        ang = random.uniform(0, math.pi*2)
        vel = random.uniform(2.2,7.5)
        particulas.append([cx,cy,math.cos(ang)*vel,math.sin(ang)*vel,random.randint(20,48)])
    emitir_particulas_energia(cx, cy, color, 54, 8.2, (24,56), 4)
    destellos.append({"x":cx,"y":cy,"radio":160,"vida":34,"max":34,"color":color})

def dibujar_modo_boss_ambiente(offset_x, offset_y):
    boss, tipo = obtener_boss_activo()
    if boss is None:
        return
    perfil = perfil_boss_visual(tipo)
    color = perfil["color"]
    ticks = pygame.time.get_ticks()
    capa = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    pygame.draw.rect(capa, (0,0,0,42), (0,0,ANCHO,42))
    pygame.draw.rect(capa, (0,0,0,42), (0,ALTO-42,ANCHO,42))
    pygame.draw.rect(capa, (color[0],color[1],color[2],18), (0,0,ANCHO,ALTO))
    for i in range(8):
        y = int((ticks*0.09 + i*78) % (ALTO+100) - 50)
        pygame.draw.line(capa, (color[0],color[1],color[2],38), (0,y), (ANCHO,y+24), 1)
    for i in range(18):
        x = int((i*47 + ticks*0.18 + offset_x*0.2) % ANCHO)
        y = int((i*83 + math.sin(ticks*0.006+i)*32 + offset_y*0.2) % ALTO)
        pygame.draw.circle(capa, (color[0],color[1],color[2],48), (x,y), 2)
    pantalla.blit(capa,(0,0))

def dibujar_boss_cinematica_v65(offset_x, offset_y):
    boss, tipo = obtener_boss_activo()
    if boss is None:
        return
    perfil = perfil_boss_visual(tipo)
    color = perfil["color"]
    fase = fase_boss_visual(tipo, boss.get("vida", perfil["max"]))
    ticks = pygame.time.get_ticks()
    cx = int(boss["x"] + perfil["cx"] + offset_x)
    cy = int(boss["y"] + perfil["cy"] + offset_y)
    intensidad = 0.45 + fase * 0.18

    capa = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    pygame.draw.rect(capa,(0,0,0,58),(0,0,ANCHO,34))
    pygame.draw.rect(capa,(0,0,0,58),(0,ALTO-34,ANCHO,34))
    pygame.draw.rect(capa,(color[0],color[1],color[2],8 + fase*5),(0,0,ANCHO,ALTO))

    for i in range(7):
        y = int((ticks*0.11 + i*91) % (ALTO+80) - 40)
        pygame.draw.line(capa,(color[0],color[1],color[2],22+fase*5),(0,y),(ANCHO,y+18),1)
    for i in range(10):
        x = int((i*97 - ticks*0.08) % (ANCHO+120) - 60)
        pygame.draw.line(capa,(255,255,255,10+fase*3),(x,34),(x+45,ALTO-34),1)

    pantalla.blit(capa,(0,0))

    radio_base = perfil["radio"] + fase*18
    for i in range(4):
        r = int(radio_base + i*24 + math.sin(ticks*0.006+i)*8)
        pygame.draw.circle(pantalla, mezclar_color(color,(255,255,255),0.15+i*0.05), (cx,cy), r, 1)

    for i in range(12 + fase*4):
        ang = ticks*0.0028 + i*math.pi*2/(12 + fase*4)
        dist = radio_base*0.62 + math.sin(ticks*0.005+i)*14
        px = int(cx + math.cos(ang)*dist)
        py = int(cy + math.sin(ang)*dist*0.58)
        pygame.draw.circle(pantalla, color, (px,py), 2 + (i+fase)%3)
        if fase >= 2 and i % 2 == 0:
            pygame.draw.line(pantalla,(color[0],color[1],color[2]),(cx,cy),(px,py),1)

    sweep_ang = ticks*0.0035
    pygame.draw.line(
        pantalla,
        mezclar_color(color,(255,255,255),0.45),
        (cx,cy),
        (int(cx+math.cos(sweep_ang)*radio_base), int(cy+math.sin(sweep_ang)*radio_base*0.62)),
        2
    )

    etiqueta = pygame.Surface((280,58), pygame.SRCALPHA)
    etiqueta.fill((3,7,16,150))
    pygame.draw.rect(etiqueta,(color[0],color[1],color[2],120),(0,0,280,58),1,border_radius=8)
    nombre = perfil["nombre"]
    fase_txt = ("FASE " if idioma_actual != "EN" else "PHASE ") + str(fase)
    amenaza = "AMENAZA CRITICA" if idioma_actual != "EN" else "CRITICAL THREAT"
    etiqueta.blit(pygame.font.SysFont(None,22).render(nombre[:24], True, (235,245,255)),(12,8))
    etiqueta.blit(pygame.font.SysFont(None,18).render(fase_txt + "  |  " + amenaza, True, color),(12,32))
    pantalla.blit(etiqueta,(ANCHO//2-140,42))

    if fase >= 3:
        for i in range(3):
            rr = int(45 + i*34 + abs(math.sin(ticks*0.009+i))*18)
            pygame.draw.circle(pantalla,(255,255,255), (cx,cy), rr, 1)
        if ticks % 22 < 4:
            emitir_particulas_energia(cx, cy, color, 3, 3.2, (12,24), 2)

def dibujar_rayo_cinematico(superficie, orientacion, posicion, offset_x, offset_y, aviso=False, grosor=52, color=(255,40,40)):
    pulso = 0.55 + 0.45 * abs(math.sin(pygame.time.get_ticks()/70))
    core = (
        min(255, color[0] + 170),
        min(255, color[1] + 170),
        min(255, color[2] + 170)
    )
    halo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)

    if orientacion == "v":
        x = int(posicion + offset_x)
        if aviso:
            pygame.draw.line(superficie, color, (x,0), (x,ALTO), 3)
            pygame.draw.line(superficie, core, (x-9,0), (x-9,ALTO), 1)
            pygame.draw.line(superficie, core, (x+9,0), (x+9,ALTO), 1)
            return
        pygame.draw.rect(halo, (color[0],color[1],color[2],70), (x-grosor,0,grosor*2,ALTO))
        pygame.draw.rect(halo, (color[0],color[1],color[2],115), (x-grosor//2,0,grosor,ALTO))
        superficie.blit(halo,(0,0))
        pygame.draw.rect(superficie, color, (x-grosor//2,0,grosor,ALTO))
        pygame.draw.rect(superficie, core, (x-max(6,grosor//8),0,max(12,grosor//4),ALTO))
        for i in range(10):
            y = (pygame.time.get_ticks()//7 + i*73) % ALTO
            pygame.draw.circle(superficie, core, (x + random.randint(-grosor//2,grosor//2), y), random.randint(2,5))
        pygame.draw.line(superficie, (255,255,255), (x,0), (x,ALTO), max(2,int(5*pulso)))
    else:
        y = int(posicion + offset_y)
        if aviso:
            pygame.draw.line(superficie, color, (0,y), (ANCHO,y), 3)
            pygame.draw.line(superficie, core, (0,y-9), (ANCHO,y-9), 1)
            pygame.draw.line(superficie, core, (0,y+9), (ANCHO,y+9), 1)
            return
        pygame.draw.rect(halo, (color[0],color[1],color[2],70), (0,y-grosor,ANCHO,grosor*2))
        pygame.draw.rect(halo, (color[0],color[1],color[2],115), (0,y-grosor//2,ANCHO,grosor))
        superficie.blit(halo,(0,0))
        pygame.draw.rect(superficie, color, (0,y-grosor//2,ANCHO,grosor))
        pygame.draw.rect(superficie, core, (0,y-max(6,grosor//8),ANCHO,max(12,grosor//4)))
        for i in range(12):
            x = (pygame.time.get_ticks()//7 + i*67) % ANCHO
            pygame.draw.circle(superficie, core, (x, y + random.randint(-grosor//2,grosor//2)), random.randint(2,5))
        pygame.draw.line(superficie, (255,255,255), (0,y), (ANCHO,y), max(2,int(5*pulso)))

def dibujar_laser_jugador_cinematico(x, y, offset_x, offset_y, color=(40,180,255), ancho=56):
    tiempo = pygame.time.get_ticks()
    halo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    lx = int(x + offset_x)
    alto = max(0, int(y + offset_y))
    pygame.draw.rect(halo, (color[0],color[1],color[2],70), (lx-ancho//2,0,ancho,alto))
    pygame.draw.rect(halo, (color[0],color[1],color[2],110), (lx-ancho//4,0,ancho//2,alto))
    pantalla.blit(halo,(0,0))
    pygame.draw.rect(pantalla, color, (lx-ancho//2,0,ancho,alto))
    pygame.draw.rect(pantalla, (225,250,255), (lx-max(5,ancho//8),0,max(10,ancho//4),alto))
    for i in range(8):
        py = (tiempo//5 + i*59) % max(1, ALTO)
        if py < alto:
            pygame.draw.circle(pantalla, (230,250,255), (lx+random.randint(-ancho//2,ancho//2), py), random.randint(2,4))
    pygame.draw.circle(pantalla, (225,250,255), (lx, alto), 18 + int(abs(math.sin(tiempo/90))*8), 3)

def crear_tentaculo_animado(x):
    return {"x":x, "timer":115, "hit":False, "phase":random.uniform(0, math.pi*2)}

def dibujar_tentaculo_animado(t, offset_x, offset_y):
    edad = 115 - t["timer"]
    x_base = t["x"]
    aviso = t["timer"] > 72
    activo = 25 < t["timer"] <= 72
    col = (190,40,255) if activo else (120,40,170)

    if aviso:
        alpha = 55 + int(abs(math.sin(pygame.time.get_ticks()/100))*55)
        sombra = pygame.Surface((90,230), pygame.SRCALPHA)
        pygame.draw.ellipse(sombra, (140,0,200,alpha), (0,190,90,28))
        pantalla.blit(sombra,(x_base-18+offset_x, ALTO-245+offset_y))
        pygame.draw.line(pantalla, (150,80,220), (x_base+27+offset_x, ALTO-215+offset_y), (x_base+27+offset_x, ALTO-25+offset_y), 2)
        return

    altura = min(220, int(edad*5))
    segmentos = 12
    for i in range(segmentos):
        pct = i / max(1, segmentos-1)
        y = ALTO - 25 - pct*altura
        ond = math.sin(pygame.time.get_ticks()/120 + t["phase"] + pct*5) * (18*(1-pct))
        radio = int(26 - pct*12)
        cx = int(x_base + 27 + ond + offset_x)
        cy = int(y + offset_y)
        crear_glow(pantalla,cx,cy,radio+8,col,45)
        pygame.draw.ellipse(pantalla, col, (cx-radio, cy-radio//2, radio*2, radio))
        pygame.draw.ellipse(pantalla, (235,180,255), (cx-radio//3, cy-radio//4, max(4,radio//2), max(4,radio//2)))

    punta_y = int(ALTO - 25 - altura + offset_y)
    pygame.draw.polygon(
        pantalla,
        (235,180,255),
        [
            (int(x_base+27+offset_x), punta_y-24),
            (int(x_base+4+offset_x), punta_y+20),
            (int(x_base+50+offset_x), punta_y+20)
        ]
    )

def recompensa_scale0(nivel_actual):
    if nivel_actual >= 9:
        return recompensa_scale0_bonus(150000)
    if nivel_actual == 8:
        return recompensa_scale0_bonus(125000)
    if nivel_actual == 7:
        return recompensa_scale0_bonus(100000)
    if nivel_actual == 6:
        return recompensa_scale0_bonus(75000)
    return recompensa_scale0_bonus(50000)

def activar_wormhole_evento(forzado=False):
    if estado.get("wormhole_event") is not None:
        return

    estado["wormhole_event"] = {
        "x":ANCHO//2,
        "y":ALTO//2-45,
        "r":28,
        "timer":660 if forzado else 540,
        "phase":random.uniform(0,math.pi*2),
        "forced":forzado
    }
    estado["wormhole_cd"] = 9000
    estado["wormhole_forced"] = False

def iniciar_scale0_desde_wormhole():
    global flash, shake, slowmo, slowmo_timer
    estado["estado"] = "WORMHOLE_ENTER"
    estado["scale0_timer"] = 0
    estado["scale0_reward_given"] = False
    estado["scale0_orb_collected"] = False
    estado["scale0_player_x"] = 0.0
    estado["scale0_player_z"] = 0.0
    estado["scale0_walk_hint"] = 220
    estado["scale0_lore_page"] = 0
    estado["scale0_reward"] = recompensa_scale0(nivel)
    estado["scale0_seed"] = random.randint(0,999999)
    estado["wormhole_event"] = None
    estado["balas_enemigas"].clear()
    reproducir_musica_scale0()
    flash = 22
    shake = max(shake, 20)
    slowmo = 1
    slowmo_timer = 0

def cerrar_scale0_evento():
    global flash, shake, level_banner, level_banner_text
    estado["estado"] = "JUGANDO"
    estado["inv"] = max(estado.get("inv",0),150)
    estado["shield"] = max(estado.get("shield",0),180)
    estado["balas_enemigas"].clear()
    estado["enemigos"] = [en for en in estado["enemigos"] if en.get("y",0) < -60]
    estado["wormhole_cd"] = 12000
    level_banner = 120
    level_banner_text = texto_scale0("planet")
    flash = max(flash,22)
    shake = max(shake,14)
    restaurar_musica_normal()

def finalizar_scale0_evento():
    global flash, shake
    if estado.get("estado") == "SCALE0_RETURN":
        return
    estado["estado"] = "SCALE0_RETURN"
    estado["scale0_timer"] = 0
    flash = max(flash,18)
    shake = max(shake,10)

def recoger_orbe_scale0():
    global flash, shake
    if estado.get("scale0_reward_given",False):
        return
    desbloquear_scale0()
    recompensa = estado.get("scale0_reward",50000)
    estado["score"] += recompensa
    ganar_monedas(max(5000,recompensa//20))
    estado["scale0_reward_given"] = True
    estado["scale0_orb_collected"] = True
    estado["estado"] = "SCALE0_REWARD"
    estado["scale0_timer"] = 0
    estado["ultimate_message"] = 170
    estado["ultimate_message_text"] = texto_scale0("artifact_msg") + " +" + str(recompensa)
    flash = max(flash,28)
    shake = max(shake,18)

def paginas_lore_scale0():
    if idioma_actual == "EN":
        return [
            (
                "MEMORY I: THE FIRST WORLD",
                [
                    "Before the star routes existed, before the first ships learned to break light,",
                    "there was a planet that orbited no sun.",
                    "The ancient maps called it SCALE-0.",
                    "It was not a destination. It was a warning."
                ]
            ),
            (
                "MEMORY II: THE SIGNAL",
                [
                    "For centuries, SCALE-0 remained hidden between impossible frequencies.",
                    "It answered only pilots on the edge of collapse,",
                    "when space filled with war, noise and fire.",
                    "Then it opened a wound in reality.",
                    "Not to save them. To observe them."
                ]
            ),
            (
                "MEMORY III: THOSE WHO ENTERED",
                [
                    "Others arrived before you.",
                    "They left marks in stone, doors without locks,",
                    "and machines still breathing beneath the surface.",
                    "None returned unchanged.",
                    "Some found power. Others found a question."
                ]
            ),
            (
                "MEMORY IV: THE ORB",
                [
                    "At the center of the sanctuary waits a living artifact.",
                    "It does not belong to SCALE-0. SCALE-0 protects it.",
                    "If you take it, the planet will remember your name.",
                    "And perhaps, one day, it will call you again."
                ]
            )
        ]

    return [
        (
            "MEMORIA I: EL PRIMER MUNDO",
            [
                "Antes de que existieran las rutas estelares, antes incluso de que las primeras naves",
                "aprendieran a romper la luz, hubo un planeta que no orbitaba ninguna estrella.",
                "Los mapas antiguos lo llamaban SCALE-0.",
                "No era un destino. Era una advertencia."
            ]
        ),
        (
            "MEMORIA II: LA SENAL",
            [
                "Durante siglos, SCALE-0 permanecio oculto entre frecuencias imposibles.",
                "Solo respondia a pilotos al borde del colapso,",
                "cuando el espacio se llenaba de guerra, ruido y fuego.",
                "Entonces abria un agujero en la realidad.",
                "No para salvarlos. Para observarlos."
            ]
        ),
        (
            "MEMORIA III: LOS QUE ENTRARON",
            [
                "Otros llegaron antes.",
                "Dejaron marcas en la piedra, puertas sin cerradura",
                "y maquinas que seguian respirando bajo la superficie.",
                "Ninguno volvio igual.",
                "Algunos encontraron poder. Otros encontraron una pregunta."
            ]
        ),
        (
            "MEMORIA IV: EL ORBE",
            [
                "En el centro del santuario espera un artefacto vivo.",
                "No pertenece a SCALE-0. SCALE-0 lo protege.",
                "Si lo tomas, el planeta recordara tu nombre.",
                "Y puede que, algun dia, vuelva a llamarte."
            ]
        )
    ]

def texto_scale0(clave):
    textos = {
        "planet":{
            "ES":"PLANETA SCALE-0",
            "EN":"PLANET SCALE-0"
        },
        "anomaly":{
            "ES":"ANOMALIA SCALE-0",
            "EN":"SCALE-0 ANOMALY"
        },
        "coordinates":{
            "ES":"COORDENADAS: -0 / ORIGEN DESCONOCIDO",
            "EN":"COORDINATES: -0 / UNKNOWN ORIGIN"
        },
        "first_world":{
            "ES":"EL PRIMER MUNDO",
            "EN":"THE FIRST WORLD"
        },
        "first_arrival":{
            "ES":"NO ERAS EL PRIMERO EN LLEGAR.",
            "EN":"YOU WERE NOT THE FIRST TO ARRIVE."
        },
        "walk_orb":{
            "ES":"WASD PARA CAMINAR HASTA EL ORBE.",
            "EN":"WASD TO WALK TO THE ORB."
        },
        "artifact_msg":{
            "ES":"ARTEFACTO SCALE-0",
            "EN":"SCALE-0 ARTIFACT"
        },
        "artifact_recovered":{
            "ES":"ARTEFACTO SCALE-0 RECUPERADO",
            "EN":"SCALE-0 ARTIFACT RECOVERED"
        },
        "memory_unlocked":{
            "ES":"MEMORIA DEL PRIMER MUNDO DESBLOQUEADA",
            "EN":"MEMORY OF THE FIRST WORLD UNLOCKED"
        },
        "points":{
            "ES":"PUNTOS",
            "EN":"POINTS"
        },
        "reality":{
            "ES":"REALIDAD RESTAURADA",
            "EN":"REALITY RESTORED"
        },
        "armed":{
            "ES":"ANOMALIA SCALE-0 ARMADA",
            "EN":"SCALE-0 ANOMALY ARMED"
        },
        "direct_ready":{
            "ES":"ACCESO DIRECTO A SCALE-0",
            "EN":"DIRECT ACCESS TO SCALE-0"
        },
        "maze_title":{
            "ES":"SANTUARIO LABERINTO",
            "EN":"LABYRINTH SANCTUARY"
        },
        "maze_hint":{
            "ES":"WASD: MOVER | RECOGE 3 FRAGMENTOS | ESC: SALIR",
            "EN":"WASD: MOVE | COLLECT 3 FRAGMENTS | ESC: EXIT"
        },
        "fragments":{
            "ES":"FRAGMENTOS",
            "EN":"FRAGMENTS"
        },
        "door_locked":{
            "ES":"LA PUERTA NECESITA 3 FRAGMENTOS",
            "EN":"THE DOOR NEEDS 3 FRAGMENTS"
        },
        "orb_room":{
            "ES":"CAMARA DEL ORBE",
            "EN":"ORB CHAMBER"
        },
        "escape":{
            "ES":"REGRESO A LA ORBITA",
            "EN":"RETURN TO ORBIT"
        }
    }
    return textos.get(clave,{}).get(idioma_actual,textos.get(clave,{}).get("ES",clave))

SCALE0_TILE = 32
SCALE0_MAZE_FALLBACK = [
    "#########################",
    "#S....#.......#.........#",
    "#.###.#.#####.#.#####.#.#",
    "#...#...#...#...#...#.#.#",
    "###.#####.#.#####.#.#.#.#",
    "#...#.....#.....#.#.#...#",
    "#.###.#########.#.#.###.#",
    "#.....#...F...#...#.....#",
    "#.#####.#####.#####.###.#",
    "#.#.....#...#.....#...#.#",
    "#.#.#####.#.#####.###.#.#",
    "#...#F....#....F#.....#.#",
    "#.########D###########..#",
    "#.........#.............#",
    "#.#######.#.###########.#",
    "#.......#...#...........#",
    "#.#####.#####.#####.###.#",
    "#...............#.....O.#",
    "#########################"
]

def mapa_scale0_actual():
    return estado.get("scale0_maze_map", SCALE0_MAZE_FALLBACK)

def desbloquear_scale0():
    if stats.get("scale0_unlocked",0) <= 0:
        stats["scale0_unlocked"] = 1
        guardar_progreso()

def scale0_es_muro_tile(tx, ty, fragmentos=None):
    mapa = mapa_scale0_actual()
    if ty < 0 or ty >= len(mapa) or tx < 0 or tx >= len(mapa[0]):
        return True
    tile = mapa[ty][tx]
    if tile == "#":
        return True
    if tile == "D" and (fragmentos is None or fragmentos < 3):
        return True
    return False

def scale0_punto_bloqueado(x, y, fragmentos):
    margen = 9
    puntos = [
        (x-margen,y-margen),
        (x+margen,y-margen),
        (x-margen,y+margen),
        (x+margen,y+margen)
    ]
    for pxp,pyp in puntos:
        if scale0_es_muro_tile(int(pxp//SCALE0_TILE), int(pyp//SCALE0_TILE), fragmentos):
            return True
    return False

def generar_mapa_scale0(seed=None):
    rng = random.Random(seed if seed is not None else random.randint(0,9999999))
    w, h = 25, 19
    grid = [["#" for _ in range(w)] for _ in range(h)]
    start = (1,1)
    grid[start[1]][start[0]] = "."
    stack = [start]
    visitados = {start}
    dirs = [(2,0),(-2,0),(0,2),(0,-2)]

    while stack:
        x,y = stack[-1]
        opciones = []
        for dx,dy in dirs:
            nx,ny = x+dx,y+dy
            if 1 <= nx < w-1 and 1 <= ny < h-1 and (nx,ny) not in visitados:
                opciones.append((nx,ny,dx,dy))
        if opciones:
            nx,ny,dx,dy = rng.choice(opciones)
            grid[y+dy//2][x+dx//2] = "."
            grid[ny][nx] = "."
            visitados.add((nx,ny))
            stack.append((nx,ny))
        else:
            stack.pop()

    # Abre algunas conexiones extra para que el laberinto sea menos rÃ­gido.
    for _ in range(22):
        x = rng.randrange(2,w-2)
        y = rng.randrange(2,h-2)
        if grid[y][x] == "#" and ((grid[y][x-1] == "." and grid[y][x+1] == ".") or (grid[y-1][x] == "." and grid[y+1][x] == ".")):
            grid[y][x] = "."

    def vecinos(c):
        x,y = c
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx,ny = x+dx,y+dy
            if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] != "#":
                yield (nx,ny)

    cola = [start]
    padres = {start:None}
    for c in cola:
        for n in vecinos(c):
            if n not in padres:
                padres[n] = c
                cola.append(n)

    orb = max(padres, key=lambda c: abs(c[0]-start[0]) + abs(c[1]-start[1]))
    path = []
    actual = orb
    while actual is not None:
        path.append(actual)
        actual = padres[actual]
    path.reverse()
    puerta = path[-2] if len(path) > 3 else None

    grid[start[1]][start[0]] = "S"
    if puerta:
        grid[puerta[1]][puerta[0]] = "D"
    grid[orb[1]][orb[0]] = "O"

    # Candidatos alcanzables antes de abrir la puerta.
    bloqueados = {puerta, orb, start}
    cola = [start]
    alcanzables = {start}
    for c in cola:
        x,y = c
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            n = (x+dx,y+dy)
            nx,ny = n
            if 0 <= nx < w and 0 <= ny < h and n not in alcanzables and n not in bloqueados and grid[ny][nx] != "#":
                alcanzables.add(n)
                cola.append(n)

    candidatos = [c for c in alcanzables if abs(c[0]-start[0]) + abs(c[1]-start[1]) > 6]
    rng.shuffle(candidatos)
    fragmentos = []
    for c in candidatos:
        if all(abs(c[0]-f[0]) + abs(c[1]-f[1]) >= 7 for f in fragmentos):
            fragmentos.append(c)
        if len(fragmentos) >= 3:
            break
    while len(fragmentos) < 3 and candidatos:
        c = candidatos.pop()
        if c not in fragmentos:
            fragmentos.append(c)

    for fx,fy in fragmentos[:3]:
        grid[fy][fx] = "F"

    return ["".join(fila) for fila in grid]

def preparar_scale0_laberinto(directo=False):
    estado["estado"] = "SCALE0_DIRECT_INTRO" if directo else "SCALE0_MAZE"
    estado["scale0_timer"] = 0
    estado["scale0_reward_given"] = False
    estado["scale0_orb_collected"] = False
    if "scale0_chapter" not in estado or directo:
        estado["scale0_chapter"] = 1
    estado["scale0_reward"] = recompensa_scale0_bonus(90000 + estado.get("scale0_chapter",1)*25000) if directo else estado.get("scale0_reward",75000)
    estado["scale0_maze_fragments"] = []
    estado["scale0_maze_msg"] = 0
    estado["scale0_maze_msg_text"] = ""
    estado["scale0_maze_hurt_cd"] = 0
    estado["scale0_maze_map"] = generar_mapa_scale0(random.randint(0,9999999) + estado.get("scale0_chapter",1)*777)
    suelo_enemigos = []
    for y,linea in enumerate(mapa_scale0_actual()):
        for x,tile in enumerate(linea):
            if tile == "S":
                estado["scale0_maze_px"] = x*SCALE0_TILE + SCALE0_TILE//2
                estado["scale0_maze_py"] = y*SCALE0_TILE + SCALE0_TILE//2
            elif tile == "F":
                estado["scale0_maze_fragments"].append({"x":x*SCALE0_TILE+16,"y":y*SCALE0_TILE+16,"taken":False})
            elif tile == "O":
                estado["scale0_maze_orb_x"] = x*SCALE0_TILE + 16
                estado["scale0_maze_orb_y"] = y*SCALE0_TILE + 16
            if tile == "." and x > 4 and y > 3:
                suelo_enemigos.append((x,y))
    random.shuffle(suelo_enemigos)
    estado["scale0_maze_enemies"] = []
    enemigos_objetivo = min(5, 2 + estado.get("scale0_chapter",1))
    for x,y in suelo_enemigos[:enemigos_objetivo]:
        eje = "x" if random.randint(0,1) == 0 else "y"
        centro = x*SCALE0_TILE + 16 if eje == "x" else y*SCALE0_TILE + 16
        estado["scale0_maze_enemies"].append({
            "x":x*SCALE0_TILE+16,
            "y":y*SCALE0_TILE+16,
            "axis":eje,
            "dir":random.choice([-1,1]),
            "min":centro-48,
            "max":centro+48,
            "phase":random.randint(0,160)
        })
    reproducir_musica_scale0()

def iniciar_scale0_directo():
    global flash, shake, slowmo, slowmo_timer
    preparar_scale0_laberinto(True)
    estado["score"] = max(estado.get("score",0), 0)
    flash = max(flash,18)
    shake = max(shake,10)
    slowmo = 1
    slowmo_timer = 0

def avanzar_capitulo_scale0():
    global flash, shake
    cap = estado.get("scale0_chapter",1)
    if cap < 3:
        estado["scale0_chapter"] = cap + 1
        preparar_scale0_laberinto(False)
        estado["scale0_maze_msg"] = 150
        estado["scale0_maze_msg_text"] = (f"CAPITULO {cap+1}" if idioma_actual != "EN" else f"CHAPTER {cap+1}")
        flash = max(flash,18)
        shake = max(shake,12)
        return True
    return False

def otorgar_reliquia_scale0():
    disponibles = ["zero_relic","time_shard","vital_orb"]
    nombres = {
        "zero_relic":("NUCLEO CERO","ZERO CORE"),
        "time_shard":("FRAGMENTO TEMPORAL","TIME SHARD"),
        "vital_orb":("ORBE VITAL","VITAL ORB")
    }
    for relic in disponibles:
        if relic not in relics_scale0:
            relics_scale0.add(relic)
            guardar_progreso()
            return nombres[relic][1 if idioma_actual == "EN" else 0]
    return "SCALE-0"

def dibujar_piloto_scale0(x, y, caminando, ticks):
    paso = math.sin(ticks*0.018)*2 if caminando else 0
    sombra = pygame.Surface((34,14), pygame.SRCALPHA)
    pygame.draw.ellipse(sombra,(0,0,0,80),(0,0,34,14))
    pantalla.blit(sombra,(x-17,y+12))
    pygame.draw.rect(pantalla,(18,20,42),(x-7,y-13,14,21),border_radius=3)
    pygame.draw.rect(pantalla,(225,235,255),(x-8,y-20,16,11),border_radius=4)
    pygame.draw.rect(pantalla,(15,22,38),(x-5,y-18,10,5))
    pygame.draw.rect(pantalla,(235,90,70),(x-9,y-12,18,7))
    pygame.draw.line(pantalla,(245,205,80),(x-10,y-10),(x-22,y+3),3)
    pygame.draw.line(pantalla,(35,45,70),(x-5,y+7),(x-9,y+16+paso),3)
    pygame.draw.line(pantalla,(35,45,70),(x+5,y+7),(x+9,y+16-paso),3)

def dibujar_scale0_tile(tile, x, y, ticks):
    rect = pygame.Rect(x,y,SCALE0_TILE,SCALE0_TILE)
    if tile == "#":
        pygame.draw.rect(pantalla,(5,18,26),rect)
        pygame.draw.rect(pantalla,(22,65,72),(x+2,y+2,SCALE0_TILE-4,SCALE0_TILE-4),1)
        if (x+y)//SCALE0_TILE % 2 == 0:
            pygame.draw.line(pantalla,(70,180,160),(x+7,y+24),(x+24,y+9),1)
    elif tile == "D":
        pygame.draw.rect(pantalla,(12,30,36),rect)
        pygame.draw.rect(pantalla,(130,255,220),rect,2)
        pygame.draw.circle(pantalla,(255,220,120),(x+16,y+16),4+int(abs(math.sin(ticks*0.01))*3))
    else:
        base = (9,42,38) if tile != "O" else (14,52,50)
        pygame.draw.rect(pantalla,base,rect)
        if (x*3+y*5) % 7 == 0:
            pygame.draw.rect(pantalla,(18,72,62),(x+6,y+20,4,7))
            pygame.draw.rect(pantalla,(18,72,62),(x+17,y+10,3,8))
        if (x+y) % 5 == 0:
            pygame.draw.circle(pantalla,(90,210,170),(x+22,y+22),1)

def dibujar_scale0_laberinto():
    global flash, shake
    ticks = pygame.time.get_ticks()
    t = estado.get("scale0_timer",0)
    teclas = pygame.key.get_pressed()
    px = float(estado.get("scale0_maze_px",48))
    py = float(estado.get("scale0_maze_py",48))
    px_seguro, py_seguro = px, py
    fragmentos = sum(1 for f in estado.get("scale0_maze_fragments",[]) if f.get("taken"))
    if estado.get("scale0_maze_hurt_cd",0) > 0:
        estado["scale0_maze_hurt_cd"] -= 1
    velocidad = 2.25
    dx = (1 if teclas[pygame.K_d] else 0) - (1 if teclas[pygame.K_a] else 0)
    dy = (1 if teclas[pygame.K_s] else 0) - (1 if teclas[pygame.K_w] else 0)
    if dx and dy:
        dx *= 0.707
        dy *= 0.707
    nx = px + dx*velocidad
    ny = py
    if not scale0_punto_bloqueado(nx, ny, fragmentos):
        px = nx
    ny = py + dy*velocidad
    if not scale0_punto_bloqueado(px, ny, fragmentos):
        py = ny
    estado["scale0_maze_px"] = px
    estado["scale0_maze_py"] = py

    for enemigo in estado.get("scale0_maze_enemies",[]):
        eje = enemigo.get("axis","x")
        nuevo = enemigo[eje] + enemigo.get("dir",1) * 0.82
        old = enemigo[eje]
        enemigo[eje] = nuevo
        if enemigo[eje] < enemigo.get("min",0) or enemigo[eje] > enemigo.get("max",0) or scale0_punto_bloqueado(enemigo["x"], enemigo["y"], 3):
            enemigo[eje] = old
            enemigo["dir"] *= -1
        ciclo = (ticks//2 + enemigo.get("phase",0)) % 180
        peligroso = ciclo < 78
        if peligroso and estado.get("scale0_maze_hurt_cd",0) <= 0 and math.hypot(px-enemigo["x"], py-enemigo["y"]) < 16:
            px = px_seguro
            py = py_seguro
            estado["scale0_maze_px"] = px
            estado["scale0_maze_py"] = py
            estado["scale0_maze_hurt_cd"] = 60
            estado["scale0_maze_msg"] = 95
            estado["scale0_maze_msg_text"] = "ECO HOSTIL - ESPERA SU FASE" if idioma_actual != "EN" else "HOSTILE ECHO - WAIT ITS PHASE"
            flash = max(flash,10)
            shake = max(shake,8)

    for frag in estado.get("scale0_maze_fragments",[]):
        if not frag.get("taken") and math.hypot(px-frag["x"], py-frag["y"]) < 21:
            frag["taken"] = True
            stats["scale0_fragments"] = max(stats.get("scale0_fragments",0), fragmentos + 1)
            estado["scale0_maze_msg"] = 80
            estado["scale0_maze_msg_text"] = texto_scale0("fragments") + f" {fragmentos+1}/3"
            flash = max(flash,8)

    fragmentos = sum(1 for f in estado.get("scale0_maze_fragments",[]) if f.get("taken"))
    orb_x = estado.get("scale0_maze_orb_x",736)
    orb_y = estado.get("scale0_maze_orb_y",560)
    if math.hypot(px-orb_x, py-orb_y) < 24:
        if fragmentos >= 3:
            if not avanzar_capitulo_scale0():
                estado["estado"] = "SCALE0_RELIC_ROOM"
                estado["scale0_timer"] = 0
                flash = max(flash,18)
            return
        estado["scale0_maze_msg"] = 90
        estado["scale0_maze_msg_text"] = texto_scale0("door_locked")

    pantalla.fill((1,8,12))
    for y,linea in enumerate(mapa_scale0_actual()):
        for x,tile in enumerate(linea):
            dibujar_scale0_tile(tile, x*SCALE0_TILE, y*SCALE0_TILE, ticks)

    # Detalles de ambiente del santuario.
    for i in range(46):
        sx = int((i*83 + ticks*0.035) % ANCHO)
        sy = int((i*47 + math.sin(ticks*0.003+i)*22) % ALTO)
        pygame.draw.circle(pantalla,(80,255,220,42),(sx,sy),1)
    for i in range(9):
        yy = int(95 + i*54 + math.sin(ticks*0.003+i)*9)
        pygame.draw.line(pantalla,(40,130,120),(0,yy),(ANCHO,yy+11),1)

    for frag in estado.get("scale0_maze_fragments",[]):
        if frag.get("taken"):
            continue
        crear_glow(pantalla,int(frag["x"]),int(frag["y"]),22,(120,255,220),55)
        pygame.draw.polygon(pantalla,(160,255,230),[(frag["x"],frag["y"]-9),(frag["x"]+8,frag["y"]),(frag["x"],frag["y"]+9),(frag["x"]-8,frag["y"])])
        pygame.draw.circle(pantalla,(255,240,140),(int(frag["x"]),int(frag["y"])),3)

    for enemigo in estado.get("scale0_maze_enemies",[]):
        ex,ey = int(enemigo["x"]), int(enemigo["y"])
        ciclo = (ticks//2 + enemigo.get("phase",0)) % 180
        peligroso = ciclo < 78
        if peligroso:
            crear_glow(pantalla,ex,ey,25,(220,80,255),58)
            pygame.draw.circle(pantalla,(76,18,112),(ex,ey),11)
            pygame.draw.circle(pantalla,(245,165,255),(ex,ey),12,2)
            pygame.draw.circle(pantalla,(255,225,255),(ex-3,ey-2),3)
            pygame.draw.circle(pantalla,(230,120,255),(ex,ey),18,1)
        else:
            crear_glow(pantalla,ex,ey,18,(80,190,210),26)
            pygame.draw.circle(pantalla,(18,52,66),(ex,ey),8)
            pygame.draw.circle(pantalla,(115,235,235),(ex,ey),10,1)
            pygame.draw.line(pantalla,(120,240,230),(ex-8,ey),(ex+8,ey),1)

    if fragmentos >= 3:
        crear_glow(pantalla,int(orb_x),int(orb_y),34,(255,220,120),80)
    else:
        crear_glow(pantalla,int(orb_x),int(orb_y),22,(80,140,150),35)
    pygame.draw.circle(pantalla,(255,230,140) if fragmentos >= 3 else (85,130,140),(int(orb_x),int(orb_y)),11)
    pygame.draw.circle(pantalla,(160,255,230),(int(orb_x),int(orb_y)),18,2)

    dibujar_piloto_scale0(int(px), int(py), dx != 0 or dy != 0, ticks)

    overlay = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    crear_glow(overlay,int(px),int(py),150,(50,220,190),45)
    pantalla.blit(overlay,(0,0))

    hud = pygame.Rect(10,10,310,74)
    pygame.draw.rect(pantalla,(3,12,22),hud,border_radius=8)
    pygame.draw.rect(pantalla,(90,230,210),hud,2,border_radius=8)
    titulo = fuente_peq.render(texto_scale0("maze_title") + f" {estado.get('scale0_chapter',1)}/3", True, (225,245,255))
    fr = fuente_peq.render(f"{texto_scale0('fragments')}: {fragmentos}/3", True, (120,255,220))
    hint = pygame.font.SysFont(None,17).render(texto_scale0("maze_hint"), True, (160,205,220))
    pantalla.blit(titulo,(hud.x+14,hud.y+10))
    pantalla.blit(fr,(hud.x+14,hud.y+32))
    pantalla.blit(hint,(hud.x+14,hud.y+54))
    if estado.get("scale0_maze_msg",0) > 0:
        estado["scale0_maze_msg"] -= 1
        msg = fuente.render(estado.get("scale0_maze_msg_text",""), True, (255,230,120))
        pantalla.blit(msg,(ANCHO//2-msg.get_width()//2,92))

def dibujar_scale0_relic_room():
    t = estado.get("scale0_timer",0)
    pantalla.fill((0,8,12))
    cx,cy = ANCHO//2,ALTO//2
    for i in range(14):
        r = 38 + i*24 + int(math.sin(t*0.03+i)*6)
        pygame.draw.circle(pantalla,(60,255,220) if i%2 else (255,220,120),(cx,cy),r,1)
    for i in range(32):
        ang = i*math.pi/16 + t*0.035
        dist = 55 + (i%6)*34
        pygame.draw.circle(pantalla,(140,255,230),(int(cx+math.cos(ang)*dist),int(cy+math.sin(ang)*dist)),2)
    crear_glow(pantalla,cx,cy,150,(120,255,220),125)
    crear_glow(pantalla,cx,cy,82,(255,220,120),82)
    pygame.draw.circle(pantalla,(255,235,150),(cx,cy),36)
    pygame.draw.circle(pantalla,(220,255,245),(cx,cy),58,3)
    titulo = pygame.font.SysFont(None,50).render(texto_scale0("orb_room"), True, (230,255,245))
    pantalla.blit(titulo,(ANCHO//2-titulo.get_width()//2,92))
    if t > 90:
        relic_name = otorgar_reliquia_scale0()
        stats["scale0_runs"] = stats.get("scale0_runs",0) + 1
        desbloquear_scale0()
        recoger_orbe_scale0()
        estado["ultimate_message"] = 180
        estado["ultimate_message_text"] = ("RELIQUIA: " if idioma_actual != "EN" else "RELIC: ") + relic_name

def avanzar_lore_scale0():
    paginas = paginas_lore_scale0()
    estado["scale0_lore_page"] = estado.get("scale0_lore_page",0) + 1
    estado["scale0_timer"] = 0
    if estado["scale0_lore_page"] >= len(paginas):
        estado["estado"] = "PLANET_WALK"
        estado["scale0_timer"] = 0

def actualizar_wormhole_evento(nivel_actual):
    if estado.get("estado") != "JUGANDO":
        return

    if hay_boss_activo() or nivel_actual < 4:
        if estado.get("wormhole_event"):
            estado["wormhole_event"]["timer"] -= 2
            if estado["wormhole_event"]["timer"] <= 0:
                estado["wormhole_event"] = None
        return

    if estado.get("wormhole_event") is None:
        estado["wormhole_cd"] = max(0, estado.get("wormhole_cd",3600)-1)
        puede_forzar = estado.get("wormhole_forced",False)
        aparece_raro = estado["wormhole_cd"] <= 0 and random.randint(1,3300) == 1
        if puede_forzar or aparece_raro:
            activar_wormhole_evento(puede_forzar)
        return

    w = estado.get("wormhole_event")
    if not w:
        return

    w["timer"] -= 1
    w["phase"] += 0.08
    w["r"] = min(72, w["r"] + 0.12)

    cx = w["x"] - 25
    cy = w["y"] - 25
    distancia_nave = math.hypot(estado["nave_x"]-cx, estado["nave_y"]-cy)
    w["locked"] = distancia_nave < 190
    if distancia_nave < 210:
        estado["nave_x"] += (cx - estado["nave_x"]) / 120
        estado["nave_y"] += (cy - estado["nave_y"]) / 120
        estado["nave_x"] = int(estado["nave_x"])
        estado["nave_y"] = int(estado["nave_y"])

    rect_w = pygame.Rect(w["x"]-w["r"], w["y"]-w["r"], w["r"]*2, w["r"]*2)
    if colisiona_con_jugador(rect_w):
        iniciar_scale0_desde_wormhole()
        return

    if w["timer"] <= 0:
        estado["wormhole_event"] = None

def actualizar_micro_anomalias(nivel_actual):
    if estado.get("estado") != "JUGANDO" or nivel_actual < 2 or hay_boss_activo():
        return
    estado.setdefault("micro_anomalias",[])
    if len(estado["micro_anomalias"]) < 2 and random.randint(1,1300) == 1:
        estado["micro_anomalias"].append({
            "x":random.randint(60,ANCHO-60),
            "y":random.randint(245,ALTO-90),
            "vida":520,
            "phase":random.uniform(0,math.pi*2)
        })
    nuevas = []
    jugador = pygame.Rect(estado["nave_x"],estado["nave_y"],50,50)
    for a in estado["micro_anomalias"]:
        a["vida"] -= 1
        rect = pygame.Rect(a["x"]-18,a["y"]-18,36,36)
        if rect.colliderect(jugador):
            bonus = recompensa_scale0_bonus(3500 + nivel_actual*900)
            estado["score"] += bonus
            ganar_monedas(max(100,bonus//25))
            estado["ultimate_message"] = 100
            estado["ultimate_message_text"] = ("ANOMALIA +" if idioma_actual != "EN" else "ANOMALY +") + str(bonus)
            emitir_particulas_energia(a["x"],a["y"],(120,255,220),24,4.5,(18,34),2)
            continue
        if a["vida"] > 0:
            nuevas.append(a)
    estado["micro_anomalias"] = nuevas

def dibujar_micro_anomalias():
    ticks = pygame.time.get_ticks()
    for a in estado.get("micro_anomalias",[]):
        x,y = int(a["x"]),int(a["y"])
        pulso = abs(math.sin(ticks*0.006+a.get("phase",0)))
        crear_glow(pantalla,x,y,28+int(pulso*14),(120,255,220),55)
        pygame.draw.circle(pantalla,(30,120,130),(x,y),12)
        pygame.draw.circle(pantalla,(150,255,235),(x,y),12,2)
        pygame.draw.arc(pantalla,(255,220,120),(x-22,y-22,44,44),ticks*0.004,ticks*0.004+3.8,2)

def dibujar_hud_v64():
    panel = pygame.Surface((236,50), pygame.SRCALPHA)
    panel.fill((3,10,20,118))
    color = (120,255,220) if build_seleccionada == "anomaly" else ((255,120,80) if build_seleccionada == "assault" else ((120,210,255) if build_seleccionada == "guardian" else (210,230,245)))
    pygame.draw.rect(panel,color+(95,),(0,0,236,50),1,border_radius=8)
    texto_build = pygame.font.SysFont(None,19).render(("BUILD: " if idioma_actual == "EN" else "RUTA: ") + nombre_build_actual(), True, (235,245,255))
    texto_relic = pygame.font.SysFont(None,17).render(("RELICS: " if idioma_actual == "EN" else "RELIQUIAS: ") + str(len(relics_scale0)) + "/3", True, (160,220,220))
    panel.blit(texto_build,(10,8))
    panel.blit(texto_relic,(10,28))
    pantalla.blit(panel,(ANCHO-248,ALTO-62))

def dibujar_icono_codex(tipo, cx, cy, color):
    crear_glow(pantalla,cx,cy,28,color,35)
    if tipo == "build":
        pygame.draw.polygon(pantalla,color,[(cx,cy-18),(cx+17,cy+12),(cx,cy+5),(cx-17,cy+12)])
        pygame.draw.circle(pantalla,(235,245,255),(cx,cy-2),5)
    elif tipo == "relic":
        pygame.draw.polygon(pantalla,color,[(cx,cy-20),(cx+18,cy),(cx,cy+20),(cx-18,cy)])
        pygame.draw.circle(pantalla,(255,235,140),(cx,cy),6)
    elif tipo == "anomaly":
        pygame.draw.circle(pantalla,(25,40,55),(cx,cy),17)
        pygame.draw.circle(pantalla,color,(cx,cy),17,2)
        pygame.draw.arc(pantalla,(255,220,120),(cx-24,cy-24,48,48),0.4,4.8,2)
    elif tipo == "planet":
        pygame.draw.circle(pantalla,color,(cx,cy),18)
        pygame.draw.arc(pantalla,(235,245,255),(cx-26,cy-10,52,20),0.0,math.pi,2)
    elif tipo == "scale0":
        pygame.draw.rect(pantalla,(4,16,24),(cx-17,cy-17,34,34),1)
        pygame.draw.circle(pantalla,color,(cx,cy),15,2)
        pygame.draw.line(pantalla,color,(cx-21,cy),(cx+21,cy),1)
        pygame.draw.line(pantalla,color,(cx,cy-21),(cx,cy+21),1)
    elif tipo == "boss":
        pygame.draw.polygon(pantalla,color,[(cx,cy-20),(cx+19,cy-7),(cx+12,cy+17),(cx-12,cy+17),(cx-19,cy-7)],2)
        pygame.draw.circle(pantalla,(255,245,220),(cx,cy),5)
    else:
        pygame.draw.rect(pantalla,(6,18,30),(cx-17,cy-17,34,34),border_radius=5)
        pygame.draw.rect(pantalla,color,(cx-17,cy-17,34,34),2,border_radius=5)
        pygame.draw.circle(pantalla,color,(cx,cy),5)

def entradas_codex_v64():
    if idioma_actual == "EN":
        return [
            {"title":"PILOT ROUTES","short":"Build system","icon":"build","color":(120,255,220),"story":"The pilots of ScaleTale no longer fly only by instinct. Each route is a combat doctrine loaded into the ship before launch.","how":"Press 1-4 in the main menu. Balanced is neutral, Assault is faster, Guardian is safer and Anomaly improves secret rewards.","effect":"Changes cooldowns, starting protection, max life or Scale-0 rewards."},
            {"title":"SCALE-0 RELICS","short":"Permanent artifacts","icon":"relic","color":(255,220,120),"story":"Some objects recovered from Scale-0 keep resonating after the run ends. They become permanent fragments of the pilot profile.","how":"Complete the three Scale-0 labyrinth chapters to recover a relic from the final chamber.","effect":"Relics can improve rewards, cooldowns and maximum life."},
            {"title":"MICRO ANOMALIES","short":"Run events","icon":"anomaly","color":(140,255,235),"story":"Scale-0 sometimes leaks tiny echoes into normal space. They are unstable, brief and valuable.","how":"During normal levels, touch a small anomaly before it fades away.","effect":"Grants score and coins. Anomaly route improves the reward."},
            {"title":"PLANET MISSIONS","short":"Planet objectives","icon":"planet","color":(110,190,255),"story":"Every planet has conditions, hazards and pilot contracts. The selected planet now matters beyond the background.","how":"Start a run after choosing a planet. The HUD shows a small objective such as destroying enemies.","effect":"Completing it grants score and coins during the run."},
            {"title":"SCALE-0 CHAPTERS","short":"Three labyrinths","icon":"scale0","color":(120,255,220),"story":"Scale-0 is not one room. It unfolds in layers, like a memory defending itself.","how":"Collect three fragments in each labyrinth, avoid hostile echoes and reach the orb. Chapter 3 opens the relic chamber.","effect":"Turns Scale-0 into a special mode with progression and rewards."},
            {"title":"BOSS FURY PHASES","short":"Boss escalation","icon":"boss","color":(255,95,95),"story":"Bosses now react when damaged. Their systems overload, their attacks intensify and the arena warns the pilot.","how":"Lower a boss health bar enough to trigger a new phase.","effect":"Adds pulse, warning and cinematic escalation before stronger attacks."}
        ]
    return [
        {"title":"RUTAS DE PILOTO","short":"Sistema de builds","icon":"build","color":(120,255,220),"story":"Los pilotos de ScaleTale ya no vuelan solo por instinto. Cada ruta es una doctrina de combate cargada antes del despegue.","how":"Pulsa 1-4 en el menu principal. Equilibrio es neutral, Asalto es mas rapido, Guardian es mas seguro y Anomalia mejora recompensas secretas.","effect":"Cambia cooldowns, proteccion inicial, vida maxima o recompensas de Scale-0."},
        {"title":"RELIQUIAS SCALE-0","short":"Artefactos permanentes","icon":"relic","color":(255,220,120),"story":"Algunos objetos recuperados en Scale-0 siguen resonando tras terminar la partida. Se convierten en fragmentos permanentes del perfil.","how":"Completa los tres capitulos del laberinto Scale-0 para recuperar una reliquia en la camara final.","effect":"Las reliquias pueden mejorar recompensas, cooldowns y vida maxima."},
        {"title":"MICRO ANOMALIAS","short":"Eventos de partida","icon":"anomaly","color":(140,255,235),"story":"Scale-0 a veces filtra pequenos ecos al espacio normal. Son inestables, duran poco y valen la pena.","how":"Durante niveles normales, toca una pequena anomalia antes de que desaparezca.","effect":"Da puntos y monedas. La ruta Anomalia mejora la recompensa."},
        {"title":"MISIONES DE PLANETA","short":"Objetivos planetarios","icon":"planet","color":(110,190,255),"story":"Cada planeta tiene condiciones, peligros y contratos de piloto. El planeta elegido ahora importa mas alla del fondo.","how":"Empieza una partida tras elegir planeta. El HUD muestra un objetivo pequeno, como destruir enemigos.","effect":"Completarlo da puntos y monedas durante la partida."},
        {"title":"CAPITULOS SCALE-0","short":"Tres laberintos","icon":"scale0","color":(120,255,220),"story":"Scale-0 no es una sola sala. Se despliega por capas, como una memoria defendiendose.","how":"Recoge tres fragmentos en cada laberinto, evita ecos hostiles y llega al orbe. El capitulo 3 abre la camara de reliquia.","effect":"Convierte Scale-0 en un modo especial con progresion y recompensas."},
        {"title":"FASES DE FURIA","short":"Escalada de bosses","icon":"boss","color":(255,95,95),"story":"Los bosses reaccionan al dano. Sus sistemas se sobrecargan, sus ataques escalan y la arena avisa al piloto.","how":"Baja suficiente la vida de un boss para activar una nueva fase.","effect":"Anade pulso, aviso y escalada cinematografica antes de ataques mas fuertes."}
    ]

def dibujar_wormhole_evento(offset_x, offset_y):
    w = estado.get("wormhole_event")
    if not w:
        return

    cx = int(w["x"]+offset_x)
    cy = int(w["y"]+offset_y)
    t = pygame.time.get_ticks()
    radio = int(w["r"])
    lock = w.get("locked",False)
    crear_glow(pantalla,cx,cy,radio+62,(120,40,255),95 if lock else 70)
    crear_glow(pantalla,cx,cy,radio+28,(35,220,255),70 if lock else 45)

    for i in range(26):
        ang = w["phase"]*1.4 + i*math.pi/13
        largo = radio + 85 + int(math.sin(t/180+i)*20)
        x1 = int(cx + math.cos(ang)*(radio+12))
        y1 = int(cy + math.sin(ang)*(radio+12))
        x2 = int(cx + math.cos(ang)*largo)
        y2 = int(cy + math.sin(ang)*largo)
        pygame.draw.line(pantalla,(70,210,255) if i%2 else (160,80,255),(x2,y2),(x1,y1),1)

    for i in range(18):
        ang = w["phase"] + i*math.pi/9
        r1 = radio + math.sin(t/110+i)*9
        x = int(cx + math.cos(ang)*r1)
        y = int(cy + math.sin(ang)*r1)
        pygame.draw.circle(pantalla,(240,250,255) if lock and i%4==0 else (170,90,255),(x,y),5 if lock else 4)

    for i in range(6):
        ang = -w["phase"]*1.3 + i*math.pi/3
        pygame.draw.arc(
            pantalla,
            (70,230,255),
            (cx-radio-i*8,cy-radio-i*8,(radio+i*8)*2,(radio+i*8)*2),
            ang,
            ang+1.2,
            3
        )

    pygame.draw.circle(pantalla,(2,0,10),(cx,cy),max(12,radio-18))
    pygame.draw.circle(pantalla,(230,250,255),(cx,cy),radio,2)
    if lock:
        pygame.draw.circle(pantalla,(255,255,255),(cx,cy),radio+10,1)
        pygame.draw.line(pantalla,(120,255,240),(int(estado["nave_x"]+25+offset_x),int(estado["nave_y"]+25+offset_y)),(cx,cy),1)
    texto = pygame.font.SysFont(None,22).render("SCALE-0", True, (210,240,255))
    pantalla.blit(texto,(cx-texto.get_width()//2,cy+radio+14))

def dibujar_planeta_pixelado(cx, cy, radio, seed=0):
    crear_glow(pantalla,cx,cy,radio+42,(40,210,255),45)
    crear_glow(pantalla,cx-radio//4,cy-radio//5,max(18,radio//2),(120,255,220),28)

    pygame.draw.circle(pantalla,(4,12,28),(cx,cy),radio)
    pygame.draw.circle(pantalla,(12,42,75),(cx,cy),radio,0)

    paso = max(3, radio//18)
    rng = random.Random(seed + radio//3)
    nube_shift = pygame.time.get_ticks()//90

    for y in range(-radio, radio+paso, paso):
        for x in range(-radio, radio+paso, paso):
            if x*x + y*y <= radio*radio:
                borde = math.sqrt(max(0,radio*radio-y*y))
                luz = 0.35 + 0.65*((x+borde)/(borde*2+1))
                ruido = math.sin((x+seed)*0.045) + math.cos((y-seed)*0.052) + math.sin((x+y)*0.031)

                if ruido > 0.45:
                    base=(22,130,105)
                elif ruido < -0.75:
                    base=(6,20,46)
                else:
                    base=(13,62,108)

                color=(int(base[0]*luz),int(base[1]*luz),int(base[2]*luz))
                pygame.draw.rect(pantalla,color,(cx+x,cy+y,paso+1,paso+1))

                if rng.random() < 0.008 and radio > 100:
                    pygame.draw.rect(pantalla,(210,180,80),(cx+x,cy+y,max(2,paso),max(2,paso)))

    nube = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    for i in range(9):
        yy = int(cy-radio*0.65 + i*radio*0.16)
        ancho = int(radio*(1.4 + 0.2*math.sin(i)))
        xx = int(cx-ancho//2 + math.sin((pygame.time.get_ticks()+i*500)/900)*radio*0.18 + nube_shift%max(1,paso*5))
        pygame.draw.ellipse(nube,(210,255,245,30),(xx,yy,ancho,max(5,radio//13)))
    pantalla.blit(nube,(0,0))

    sombra = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    pygame.draw.circle(sombra,(0,0,10,95),(cx+radio//3,cy+radio//5),radio)
    pantalla.blit(sombra,(0,0))
    pygame.draw.circle(pantalla,(170,245,255),(cx,cy),radio,3)

def dibujar_escena_scale0():
    global flash, shake
    estado["scale0_timer"] = estado.get("scale0_timer",0) + 1
    t = estado["scale0_timer"]
    fase = estado["estado"]
    seed = estado.get("scale0_seed",0)

    pantalla.fill((0,0,8))

    if fase == "SCALE0_DIRECT_INTRO":
        progreso = min(1.0,t/95)
        pantalla.fill((0,6,10))
        for i in range(90):
            x = int((i*97 + t*1.2) % ANCHO)
            y = int((i*43 + math.sin(t*0.02+i)*28) % ALTO)
            pygame.draw.circle(pantalla,(55,160,145),(x,y),1)
        for i in range(8):
            r = int(32 + i*34 + progreso*80)
            pygame.draw.circle(pantalla,(80,255,220) if i%2 else (150,80,255),(ANCHO//2,ALTO//2),r,1)
        crear_glow(pantalla,ANCHO//2,ALTO//2,115+int(progreso*120),(100,255,220),105)
        titulo = pygame.font.SysFont(None,54).render(texto_scale0("direct_ready"), True, (230,255,245))
        sub = fuente.render(texto_scale0("maze_title"), True, (140,255,220))
        pantalla.blit(titulo,(ANCHO//2-titulo.get_width()//2,208))
        pantalla.blit(sub,(ANCHO//2-sub.get_width()//2,265))
        if t > 105:
            estado["estado"] = "SCALE0_MAZE"
            estado["scale0_timer"] = 0
            flash = max(flash,16)

    elif fase == "SCALE0_MAZE":
        dibujar_scale0_laberinto()

    elif fase == "SCALE0_RELIC_ROOM":
        dibujar_scale0_relic_room()

    elif fase == "SCALE0_ESCAPE":
        progreso = min(1.0,t/85)
        dibujar_fondo_profundo(nivel_anterior_visual,0,0)
        overlay = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
        overlay.fill((0,0,0,int(230*(1-progreso))))
        pantalla.blit(overlay,(0,0))
        texto = fuente.render(texto_scale0("escape"), True, (220,255,245))
        pantalla.blit(texto,(ANCHO//2-texto.get_width()//2,270))
        if t > 85:
            cerrar_scale0_evento()

    elif fase == "WORMHOLE_ENTER":
        cx,cy = ANCHO//2,ALTO//2
        zoom = min(1.0,t/135)
        fade = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
        fade.fill((0,0,8,min(180,int(t*1.2))))
        pantalla.blit(fade,(0,0))
        for i in range(46):
            ang = t*0.075 + i*math.pi/23
            r = 380 - zoom*340 + (i%7)*18
            x = int(cx + math.cos(ang)*r)
            y = int(cy + math.sin(ang)*r)
            color = (90,220,255) if i%2 else (180,80,255)
            pygame.draw.line(pantalla,color,(x,y),(cx,cy),2)
        crear_glow(pantalla,cx,cy,80+int(zoom*200),(130,40,255),105)
        crear_glow(pantalla,cx,cy,45+int(zoom*120),(50,230,255),70)
        pygame.draw.circle(pantalla,(0,0,8),(cx,cy),45+int(zoom*170))
        for i in range(10):
            r = int(60 + i*28 + zoom*80)
            pygame.draw.circle(pantalla,(80,220,255) if i%2 else (160,80,255),(cx,cy),r,1)
        nave_zoom = pygame.transform.rotozoom(imagen_nave_por_tipo(estado.get("nave_tipo",1)), t*4, max(0.25,1.0-zoom*0.7))
        pantalla.blit(nave_zoom,(cx-nave_zoom.get_width()//2,cy+120-int(zoom*140)))
        if t < 95:
            alerta = fuente.render(texto_scale0("anomaly"), True, (230,245,255))
            pantalla.blit(alerta,(ANCHO//2-alerta.get_width()//2,70))
        if t > 138:
            estado["estado"]="WORMHOLE_TRAVEL"
            estado["scale0_timer"]=0
            flash=max(flash,18)

    elif fase == "WORMHOLE_TRAVEL":
        cx,cy = ANCHO//2,ALTO//2
        pulso_color = int(80 + 70*abs(math.sin(t/35)))
        for i in range(120):
            ang = (i*137.5 + t*1.4) * math.pi/180
            dist = (i*19 + t*7) % 760
            x1 = int(cx + math.cos(ang)*dist*0.16)
            y1 = int(cy + math.sin(ang)*dist*0.16)
            x2 = int(cx + math.cos(ang)*(dist+115))
            y2 = int(cy + math.sin(ang)*(dist+115))
            color=(80,170,255) if i%3 else (190,120,255)
            pygame.draw.line(pantalla,color,(x1,y1),(x2,y2),1)
        for i in range(9):
            r = int((t*4 + i*95) % 760)
            pygame.draw.circle(pantalla,(60,pulso_color,255),(cx,cy),r,1)
        radio = 30 + int(min(1.0,t/230)*45)
        dibujar_planeta_pixelado(cx, cy, radio, seed)
        texto = fuente.render(texto_scale0("planet"), True, (220,245,255))
        pantalla.blit(texto,(ANCHO//2-texto.get_width()//2,42))
        sub = fuente_peq.render(texto_scale0("coordinates"), True, (140,230,255))
        pantalla.blit(sub,(ANCHO//2-sub.get_width()//2,83))
        dibujar_cabina_scale0_v66(t)
        if t > 240:
            estado["estado"]="PLANET_APPROACH"
            estado["scale0_timer"]=0

    elif fase == "PLANET_APPROACH":
        cx,cy = ANCHO//2,ALTO//2+12
        for i in range(80):
            x = (i*97 + t*2) % ANCHO
            y = (i*53 + t) % ALTO
            pygame.draw.circle(pantalla,(110,160,210),(int(x),int(y)),1)
        progreso = min(1.0,t/430)
        eased = progreso*progreso*(3-2*progreso)
        radio = int(70 + eased*355)
        luna_x = int(cx + 190 - eased*90)
        luna_y = int(cy - 130 + eased*40)
        crear_glow(pantalla,luna_x,luna_y,32,(120,220,255),38)
        pygame.draw.circle(pantalla,(70,130,160),(luna_x,luna_y),20)
        dibujar_planeta_pixelado(cx, cy, radio, seed)
        if t < 180:
            txt_intro = fuente.render(texto_scale0("first_world"), True, (220,245,255))
            pantalla.blit(txt_intro,(ANCHO//2-txt_intro.get_width()//2,42))
        dibujar_cabina_scale0_v66(t)
        if t > 430:
            estado["estado"]="PLANET_DESCENT"
            estado["scale0_timer"]=0
            flash=max(flash,24)

    elif fase == "PLANET_DESCENT":
        paso = max(7, 34 - t//5)
        for y in range(0,ALTO,paso):
            for x in range(0,ANCHO,paso):
                ruido = (x*13 + y*7 + seed + t*11) % 255
                color = (12,55+ruido//7,50+ruido//10) if ruido%3 else (5,18,34)
                pygame.draw.rect(pantalla,color,(x,y,paso,paso))
        velo = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
        pygame.draw.circle(velo,(220,255,240,50),(ANCHO//2,ALTO//2),max(20,300-t*2))
        pantalla.blit(velo,(0,0))
        for i in range(18):
            x = int((i*53 + t*9) % ANCHO)
            pygame.draw.line(pantalla,(180,255,230),(x,0),(x-35,ALTO),1)
        if t > 145:
            estado["estado"]="SCALE0_LORE"
            estado["scale0_timer"]=0
            estado["scale0_lore_page"]=0

    elif fase == "SCALE0_LORE":
        paginas = paginas_lore_scale0()
        pagina_idx = min(estado.get("scale0_lore_page",0), len(paginas)-1)
        titulo_lore, lineas_lore = paginas[pagina_idx]
        progreso = min(1.0,t/55)
        salida = max(0.0,(t-285)/45)

        pantalla.fill((1,5,12))
        for i in range(80):
            x = int((i*97 + t*0.4) % ANCHO)
            y = int((i*41 + t*0.18) % ALTO)
            pygame.draw.circle(pantalla,(45,90,130),(x,y),1)

        panel_alpha = int(210*progreso*(1-salida))
        panel_lore = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
        panel_lore.fill((0,0,0,max(0,min(210,panel_alpha))))
        pantalla.blit(panel_lore,(0,0))

        barrido_x = int(-ANCHO + min(1.0,t/70)*ANCHO*2)
        pygame.draw.rect(pantalla,(50,220,255),(barrido_x,0,4,ALTO))
        pygame.draw.rect(pantalla,(120,80,255),(barrido_x-18,0,2,ALTO))

        marco = pygame.Rect(80,105,640,360)
        crear_rect_glow(pantalla,(marco.x,marco.y,marco.w,marco.h),(70,230,255),45,18)
        pygame.draw.rect(pantalla,(3,12,24),marco,border_radius=8)
        pygame.draw.rect(pantalla,(90,230,255),marco,2,border_radius=8)

        titulo_render = pygame.font.SysFont(None,38).render(titulo_lore, True, (225,250,255))
        pantalla.blit(titulo_render,(ANCHO//2-titulo_render.get_width()//2,135))

        y_lore = 198
        lineas_visibles = min(len(lineas_lore), max(0,(t-45)//38))
        for idx,linea in enumerate(lineas_lore[:lineas_visibles]):
            color_linea = (210,230,245) if idx < len(lineas_lore)-1 else (255,230,140)
            render = pygame.font.SysFont(None,25).render(linea, True, color_linea)
            pantalla.blit(render,(ANCHO//2-render.get_width()//2,y_lore))
            y_lore += 36

        page_text = f"{pagina_idx+1}/{len(paginas)}"
        page_render = fuente_peq.render(page_text, True, (120,255,220))
        pantalla.blit(page_render,(marco.right-page_render.get_width()-22,marco.bottom-34))

        hint_text = "ENTER / SPACE" if idioma_actual == "EN" else "ENTER / ESPACIO"
        hint_render = fuente_peq.render(hint_text, True, (120,180,210))
        pantalla.blit(hint_render,(marco.x+22,marco.bottom-34))

        for i in range(12):
            pxp = int(marco.x + 30 + ((t*1.4+i*61) % (marco.w-60)))
            pyp = int(marco.y + 42 + math.sin(t/28+i)*135)
            pygame.draw.rect(pantalla,(120,255,220),(pxp,pyp,3,3))

        continuar = fuente_peq.render("ENTER / SPACE" if idioma_actual == "EN" else "ENTER / ESPACIO", True, (190,240,255))
        pantalla.blit(continuar,(ANCHO//2-continuar.get_width()//2,marco.bottom+18))

    elif fase == "PLANET_WALK":
        teclas = pygame.key.get_pressed()
        px = float(estado.get("scale0_player_x",0.0))
        pz = float(estado.get("scale0_player_z",0.0))
        vel = 0.72
        if teclas[pygame.K_w]:
            pz += vel
        if teclas[pygame.K_s]:
            pz -= vel
        if teclas[pygame.K_a]:
            px -= vel
        if teclas[pygame.K_d]:
            px += vel
        px = max(-42,min(42,px))
        pz = max(0,min(105,pz))
        estado["scale0_player_x"] = px
        estado["scale0_player_z"] = pz
        caminando = teclas[pygame.K_w] or teclas[pygame.K_s] or teclas[pygame.K_a] or teclas[pygame.K_d]
        bob = math.sin(t/8)*4 if caminando else math.sin(t/35)*2

        horizonte = 245
        pantalla.fill((3,8,18))
        pygame.draw.rect(pantalla,(6,14,25),(0,0,ANCHO,horizonte))
        pygame.draw.rect(pantalla,(8,22,24),(0,horizonte,ANCHO,ALTO-horizonte))
        crear_glow(pantalla,ANCHO-130,92,82,(80,180,255),45)
        pygame.draw.circle(pantalla,(38,80,112),(ANCHO-130,92),48)
        pygame.draw.circle(pantalla,(130,220,255),(ANCHO-130,92),48,1)

        niebla = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
        for i in range(7):
            yy = horizonte + 35 + i*38
            pygame.draw.ellipse(niebla,(120,255,220,14),(int(-120 + (t*0.6+i*90)%980),yy,260,32))
        pantalla.blit(niebla,(0,0))

        for i in range(24):
            depth = i/23
            y = int(horizonte + depth*depth*(ALTO-horizonte+80) + bob)
            ancho = int(35 + depth*620)
            color = (18,70+int(depth*80),70)
            pygame.draw.line(pantalla,color,(ANCHO//2-ancho,y),(ANCHO//2+ancho,y),1)

        for i in range(-10,11):
            x_far = ANCHO//2 + int((i*18 - px*3))
            x_near = ANCHO//2 + int((i*78 - px*10))
            pygame.draw.line(pantalla,(18,80,76),(x_far,horizonte+int(bob)),(x_near,ALTO),1)

        for side in [-1,1]:
            for i in range(5):
                depth = 0.35 + i*0.13
                rx = int(ANCHO//2 + side*(160 + i*45 - px*3*depth))
                ry = int(horizonte + depth*210 + bob)
                rw = int(28 + depth*36)
                rh = int(55 + depth*80)
                rect_ruina = pygame.Rect(rx-rw//2, ry-rh, rw, rh)
                pygame.draw.rect(pantalla,(7,26,30),rect_ruina)
                pygame.draw.rect(pantalla,(55,160,135),rect_ruina,1)

        puerta_z = 112
        escala = max(0.42, 1.0 - (puerta_z-pz)/140)
        puerta_y = int(150 + (1-escala)*90 + bob*0.4)
        puerta_w = int(100*escala)
        puerta_h = int(172*escala)
        puerta_x = int(ANCHO//2 - puerta_w//2 - px*escala*2.2)
        monolito = pygame.Rect(puerta_x,puerta_y,puerta_w,puerta_h)
        crear_rect_glow(pantalla,(monolito.x,monolito.y,monolito.w,monolito.h),(90,255,200),60,24)
        pygame.draw.rect(pantalla,(4,18,24),monolito)
        pygame.draw.rect(pantalla,(120,255,210),monolito,2)
        for i in range(4):
            yy = monolito.y + 28 + i*max(10,monolito.h//6)
            pygame.draw.line(pantalla,(180,255,220),(monolito.x+12,yy),(monolito.right-12,yy),1)

        orb_z = 96
        orb_dist = max(8, orb_z-pz)
        orb_scale = max(0.55, 3.5 - orb_dist/34)
        orb_x = int(ANCHO//2 - px*orb_scale*7)
        orb_y = int(310 - orb_scale*34 + bob*0.5)
        orb_r = int(13*orb_scale)
        intensidad = max(0.0,1.0-orb_dist/96)
        crear_glow(pantalla,orb_x,orb_y,orb_r+34,(120,255,220),95+int(intensidad*55))
        crear_glow(pantalla,orb_x,orb_y,orb_r+18,(255,225,120),70)
        pedestal = pygame.Rect(orb_x-int(24*orb_scale), orb_y+orb_r+8, int(48*orb_scale), int(34*orb_scale))
        pygame.draw.rect(pantalla,(8,28,30),pedestal)
        pygame.draw.rect(pantalla,(120,255,210),pedestal,1)
        pygame.draw.circle(pantalla,(255,235,150),(orb_x,orb_y),orb_r)
        pygame.draw.circle(pantalla,(150,255,235),(orb_x,orb_y),orb_r+8,2)
        pygame.draw.circle(pantalla,(255,255,245),(orb_x-int(orb_r*0.3),orb_y-int(orb_r*0.35)),max(3,orb_r//4))
        pygame.draw.arc(pantalla,(210,255,245),(orb_x-orb_r-18,orb_y-orb_r-10,(orb_r+18)*2,(orb_r+10)*2),t*0.06,t*0.06+3.8,2)
        pygame.draw.arc(pantalla,(255,220,120),(orb_x-orb_r-24,orb_y-orb_r-18,(orb_r+24)*2,(orb_r+18)*2),-t*0.045,-t*0.045+2.9,2)
        for i in range(10):
            py = int(orb_y + orb_r + 28 - ((t*2+i*17) % 95))
            pygame.draw.circle(pantalla,(160,255,225),(orb_x+int(math.sin(t/20+i)*orb_r*1.8),py),2)

        mensaje = texto_scale0("first_arrival")
        secreto = texto_scale0("walk_orb")
        r1 = fuente.render(mensaje, True, (220,245,255))
        r2 = fuente_peq.render(secreto, True, (140,255,210))
        pantalla.blit(r1,(ANCHO//2-r1.get_width()//2,55))
        pantalla.blit(r2,(ANCHO//2-r2.get_width()//2,95))

        barra = pygame.Rect(220,560,360,12)
        pygame.draw.rect(pantalla,(10,25,35),barra,border_radius=5)
        progreso_barra = min(1.0,pz/96)
        pygame.draw.rect(pantalla,(120,255,210),(barra.x,barra.y,int(barra.w*progreso_barra),barra.h),border_radius=5)
        pygame.draw.rect(pantalla,(210,255,245),barra,1,border_radius=5)

        if pz >= 92 and abs(px) <= 14:
            recoger_orbe_scale0()

    elif fase == "SCALE0_REWARD":
        pantalla.fill((2,8,14))
        cx,cy = ANCHO//2,ALTO//2
        for i in range(48):
            ang = i*math.pi/14 + t*0.045
            r = 30 + t*1.9 + (i%6)*13
            color = (120,255,220) if i%2 else (255,220,120)
            pygame.draw.circle(pantalla,color,(int(cx+math.cos(ang)*r),int(cy+math.sin(ang)*r)),3)
        for i in range(5):
            pygame.draw.circle(pantalla,(80,220,255),(cx,cy),60+i*28+int(math.sin(t/12+i)*6),1)
        crear_glow(pantalla,cx,cy,145,(120,255,220),125)
        crear_glow(pantalla,cx,cy,78,(255,220,120),80)
        pygame.draw.circle(pantalla,(255,235,150),(cx,cy),34)
        pygame.draw.circle(pantalla,(220,255,245),(cx,cy),54,3)
        texto = fuente.render(texto_scale0("artifact_recovered"), True, (240,255,245))
        memoria = fuente_peq.render(texto_scale0("memory_unlocked"), True, (140,255,220))
        premio = fuente.render("+" + str(estado.get("scale0_reward",50000)) + " " + texto_scale0("points"), True, (255,230,120))
        pantalla.blit(texto,(ANCHO//2-texto.get_width()//2,115))
        pantalla.blit(memoria,(ANCHO//2-memoria.get_width()//2,155))
        pantalla.blit(premio,(ANCHO//2-premio.get_width()//2,190))
        if t > 165:
            finalizar_scale0_evento()

    elif fase == "SCALE0_RETURN":
        progreso = min(1.0,t/95)
        dibujar_fondo_profundo(nivel_anterior_visual,0,0)
        overlay = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
        overlay.fill((0,0,0,int(210*(1-progreso))))
        pantalla.blit(overlay,(0,0))
        cx,cy = ANCHO//2,ALTO//2
        radio = int(280*(1-progreso)+25)
        pygame.draw.circle(pantalla,(120,255,220),(cx,cy),radio,2)
        texto = fuente.render(texto_scale0("reality"), True, (220,255,245))
        pantalla.blit(texto,(ANCHO//2-texto.get_width()//2,260))
        if t > 95:
            cerrar_scale0_evento()

def explosion(x,y):
    global shake
    shake=20
    reproducir_sfx("explosion", volumen_extra=0.8)
    emitir_particulas_energia(x, y, (255,220,120), 22, 5.4, (18,42), 3)

    ondas_expansion.append({
        "x":x,
        "y":y,
        "r":8,
        "max":90,
        "vida":32,
        "color":(255,220,120)
    })

    destellos.append({
        "x":x,
        "y":y,
        "vida":18,
        "max":18,
        "radio":65,
        "color":(255,245,200)
    })

    for _ in range(28):
        particulas.append([
            x,y,
            random.uniform(-5,5),
            random.uniform(-5,5),
            random.randint(20,42)
        ])

    for _ in range(18):
        ang = random.uniform(0, math.pi*2)
        vel = random.uniform(3,7)
        particulas.append([
            x,y,
            math.cos(ang)*vel,
            math.sin(ang)*vel,
            random.randint(12,26)
        ])

def particulas_laser_vertical(x):
    for _ in range(10):
        particulas.append([
            x + random.randint(-30,30),
            random.randint(0,ALTO),
            random.uniform(-2,2),
            random.uniform(-2,2),
            random.randint(10,25)
        ])

def particulas_laser_horizontal(y, color=None):
    for _ in range(10):
        p=[
            random.randint(0,ANCHO),
            y + random.randint(-25,25),
            random.uniform(-2,2),
            random.uniform(-2,2),
            random.randint(10,25)
        ]
        if color:
            p.append(color)
        particulas.append(p)

# Particulas para lasers pequeï¿½os de enemigos.
# Vertical: salen desde arriba y abajo hacia la zona del rayo.
def particulas_laser_vertical_lados(x, y1=0, y2=ALTO):
    for _ in range(8):
        particulas.append([
            x + random.randint(-18,18),
            y1 + random.randint(0,40),
            random.uniform(-1.8,1.8),
            random.uniform(1,3),
            random.randint(10,22)
        ])

        particulas.append([
            x + random.randint(-18,18),
            y2 - random.randint(0,40),
            random.uniform(-1.8,1.8),
            random.uniform(-3,-1),
            random.randint(10,22)
        ])

# Horizontal: salen desde izquierda y derecha hacia el centro del rayo.
def particulas_laser_horizontal_lados(y, x1=0, x2=ANCHO):
    for _ in range(8):
        particulas.append([
            x1 + random.randint(0,40),
            y + random.randint(-18,18),
            random.uniform(1,3),
            random.uniform(-1.8,1.8),
            random.randint(10,22)
        ])

        particulas.append([
            x2 - random.randint(0,40),
            y + random.randint(-18,18),
            random.uniform(-3,-1),
            random.uniform(-1.8,1.8),
            random.randint(10,22)
        ])

# =====================
# PARTICULAS HABILIDADES JUGADOR
# =====================
def particulas_dash(x, y, direccion):
    for _ in range(18):
        particulas.append([
            x + 25,
            y + random.randint(5,50),
            random.uniform(-2,2) - direccion*2,
            random.uniform(-2,2),
            random.randint(12,26)
        ])

def particulas_laser_jugador(x, y):
    for _ in range(14):
        particulas.append([
            x + random.randint(-22,22),
            random.randint(0, max(1, int(y))),
            random.uniform(-1.5,1.5),
            random.uniform(-2,1),
            random.randint(12,24)
        ])

def particulas_pulso(x, y, radio):
    for _ in range(20):
        ang = random.uniform(0, math.pi*2)
        particulas.append([
            x + math.cos(ang)*radio,
            y + math.sin(ang)*radio,
            math.cos(ang)*random.uniform(2,5),
            math.sin(ang)*random.uniform(2,5),
            random.randint(14,30)
        ])

def activar_pulso_jugador(centro_x, centro_y):
    global shake, flash

    radio_pulso = 190

    estado["balas_enemigas"] = [
        b for b in estado["balas_enemigas"]
        if math.hypot(b[0]-centro_x, b[1]-centro_y) > radio_pulso
    ]

    enemigos_restantes_pulso = []

    for en in estado["enemigos"]:
        distancia = math.hypot((en["x"]+35)-centro_x, (en["y"]+35)-centro_y)

        if distancia < radio_pulso:
            en["vida"] -= 5

        if en["vida"] <= 0:
            estado["score"] += PUNTOS.get(en["tipo"], 1000)
            registrar_enemigo_destruido()
            ganar_monedas(PUNTOS.get(en["tipo"], 1000)//10)
            explosion(en["x"], en["y"])
        else:
            enemigos_restantes_pulso.append(en)

    estado["enemigos"] = enemigos_restantes_pulso

    if estado["boss"]:
        boss_temp = estado["boss"]
        if math.hypot((boss_temp["x"]+75)-centro_x, (boss_temp["y"]+75)-centro_y) < radio_pulso+80:
            boss_temp["vida"] -= 18
            marcar_boss_golpeado(boss_temp, 2)

    if estado["boss_final"]:
        boss_temp = estado["boss_final"]
        if math.hypot((boss_temp["x"]+85)-centro_x, (boss_temp["y"]+85)-centro_y) < radio_pulso+90:
            boss_temp["vida"] -= 18
            marcar_boss_golpeado(boss_temp, 2)

    if estado["boss_laser"]:
        boss_temp = estado["boss_laser"]
        if math.hypot((boss_temp["x"]+95)-centro_x, (boss_temp["y"]+95)-centro_y) < radio_pulso+100:
            boss_temp["vida"] -= 18
            marcar_boss_golpeado(boss_temp, 2)

    if estado.get("boss_overmind"):
        boss_temp = estado["boss_overmind"]
        if math.hypot((boss_temp["x"]+105)-centro_x, (boss_temp["y"]+105)-centro_y) < radio_pulso+110:
            boss_temp["vida"] -= 18
            marcar_boss_golpeado(boss_temp, 2)

    if estado.get("boss_rift"):
        boss_temp = estado["boss_rift"]
        if math.hypot((boss_temp["x"]+110)-centro_x, (boss_temp["y"]+110)-centro_y) < radio_pulso+120:
            boss_temp["vida"] -= 18
            marcar_boss_golpeado(boss_temp, 2)

    for clave_boss in ["boss_hollow", "boss_sun_eater", "boss_eden"]:
        if estado.get(clave_boss):
            boss_temp = estado[clave_boss]
            if math.hypot((boss_temp["x"]+115)-centro_x, (boss_temp["y"]+115)-centro_y) < radio_pulso+125:
                boss_temp["vida"] -= 18
                marcar_boss_golpeado(boss_temp, 2)

    particulas_pulso(centro_x, centro_y, 60)
    shake = 28
    flash = 14

# =====================
# CINEMATICAS DE BOSSES
# =====================
def activar_intro_boss(tipo, nombre, duracion):
    iniciar_cabina_jugable_boss(tipo, nombre, duracion)

def congelar_ataques_durante_intro_boss():
    estado["balas_enemigas"].clear()
    estado["laser"] = 0
    estado["laser_horizontal"] = 0
    estado["laser_cross"] = 0
    estado["laser_sweep"] = 0
    for clave in ["boss","boss_final","boss_laser","boss_overmind","boss_rift","boss_hollow","boss_sun_eater","boss_eden"]:
        boss = estado.get(clave)
        if boss:
            boss["cool"] = 1
    for clave_lista in ["void_zones","tentacles","rift_attacks","quantum_fields","abyss_zones","silence_rings","solar_waves","eden_roots","crystal_rain","life_pulses"]:
        if clave_lista in estado:
            estado[clave_lista].clear()

def color_cockpit_por_tipo_v66(tipo):
    if tipo == "laser":
        return (255,70,55)
    if tipo == "final":
        return (190,70,255)
    if tipo in ["boss_rift"]:
        return (80,225,255)
    if tipo in ["boss_hollow"]:
        return (70,230,255)
    if tipo in ["boss_sun_eater"]:
        return (255,165,55)
    if tipo in ["boss_eden"]:
        return (100,255,185)
    return (255,85,70)

def dibujar_silueta_boss_cockpit_v66(superficie, tipo, cx, cy, escala, color):
    sombra = (2,5,12)
    glow_alpha = 38
    crear_glow(superficie, cx, cy, int(90*escala), color, glow_alpha)
    if tipo == "laser":
        pygame.draw.circle(superficie,sombra,(cx,cy),int(34*escala))
        pygame.draw.rect(superficie,sombra,(cx-int(18*escala),cy-int(70*escala),int(36*escala),int(140*escala)),border_radius=max(4,int(7*escala)))
        pygame.draw.line(superficie,color,(cx,cy-int(90*escala)),(cx,cy+int(92*escala)),max(2,int(3*escala)))
    elif tipo == "final":
        pts=[]
        for i in range(6):
            a=-math.pi/2+i*math.pi*2/6
            pts.append((int(cx+math.cos(a)*48*escala),int(cy+math.sin(a)*42*escala)))
        pygame.draw.polygon(superficie,sombra,pts)
        pygame.draw.circle(superficie,color,(cx,cy),max(4,int(8*escala)),1)
    elif tipo == "boss_sun_eater":
        pygame.draw.circle(superficie,sombra,(cx,cy),int(42*escala))
        for i in range(12):
            a=i*math.pi/6
            pygame.draw.line(superficie,sombra,(int(cx+math.cos(a)*42*escala),int(cy+math.sin(a)*42*escala)),(int(cx+math.cos(a)*72*escala),int(cy+math.sin(a)*72*escala)),max(2,int(5*escala)))
    elif tipo == "boss_eden":
        pygame.draw.circle(superficie,sombra,(cx,cy),int(38*escala))
        for i in range(5):
            a=-math.pi/2+i*math.pi*2/5
            pygame.draw.polygon(superficie,sombra,[
                (cx,cy),
                (int(cx+math.cos(a-0.18)*72*escala),int(cy+math.sin(a-0.18)*58*escala)),
                (int(cx+math.cos(a+0.18)*72*escala),int(cy+math.sin(a+0.18)*58*escala))
            ])
    else:
        pygame.draw.circle(superficie,sombra,(cx,cy),int(43*escala))
        pygame.draw.rect(superficie,sombra,(cx-int(52*escala),cy-int(18*escala),int(104*escala),int(36*escala)),border_radius=max(4,int(8*escala)))
    pygame.draw.circle(superficie,color,(cx,cy),max(12,int(54*escala)),2)
    pygame.draw.line(superficie,mezclar_color(color,(255,255,255),0.35),(cx-int(70*escala),cy),(cx+int(70*escala),cy),1)
    pygame.draw.line(superficie,mezclar_color(color,(255,255,255),0.35),(cx,cy-int(55*escala)),(cx,cy+int(55*escala)),1)

def dibujar_cabina_primera_persona_v66(tipo, nombre, tiempo_restante, offset_x, offset_y, color):
    ticks = pygame.time.get_ticks()
    max_t = max(1, estado.get("boss_intro_max", tiempo_restante))
    progreso = 1 - max(0, min(1, tiempo_restante / max_t))
    scan_cabina = estado.get("cockpit_scan",{})
    if scan_cabina.get("active",False):
        progreso = 0.34 + min(0.42, scan_cabina.get("progress",0) / 240)
        if scan_cabina.get("prepared",False):
            progreso = 0.76
    tema_planeta = planeta_por_id(planeta_seleccionado)["palette"][1]
    fondo = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    fondo.fill((2,5,14,255))

    # Tunel estelar visto desde la cabina.
    centro_x = ANCHO//2 + int(offset_x*0.55 + math.sin(ticks*0.004)*9)
    centro_y = 235 + int(offset_y*0.35 + math.cos(ticks*0.003)*7)
    for i in range(90):
        ang = i*2.399 + ticks*0.0007
        profundidad = ((i*37 + ticks*0.28) % 420) / 420
        dist = 28 + profundidad*440
        x = int(centro_x + math.cos(ang)*dist*1.25)
        y = int(centro_y + math.sin(ang)*dist*0.72)
        largo = 3 + int(profundidad*14)
        col = mezclar_color((210,230,255), tema_planeta, 0.28)
        pygame.draw.line(fondo,(col[0],col[1],col[2],80),(x,y),(int(x+math.cos(ang)*largo),int(y+math.sin(ang)*largo)),1)

    # Planeta y niebla de fondo, dependiente del planeta seleccionado.
    planeta_color = planeta_por_id(planeta_seleccionado)["palette"][0]
    pygame.draw.circle(fondo,(planeta_color[0],planeta_color[1],planeta_color[2],42),(ANCHO-115,118),82)
    pygame.draw.circle(fondo,(tema_planeta[0],tema_planeta[1],tema_planeta[2],28),(ANCHO-115,118),118,2)
    for i in range(5):
        y = int(95+i*46+math.sin(ticks*0.003+i)*12)
        pygame.draw.ellipse(fondo,(tema_planeta[0],tema_planeta[1],tema_planeta[2],18),(40+i*20,y,ANCHO-120,22),1)

    # Silueta del boss aproximandose desde el exterior.
    escala = 0.62 + progreso*0.72
    boss_x = centro_x + int(math.sin(ticks*0.002)*18)
    boss_y = centro_y + int(10 + progreso*24)
    dibujar_silueta_boss_cockpit_v66(fondo, tipo, boss_x, boss_y, escala, color)
    lock_w = int(88 * escala)
    lock_h = int(64 * escala)
    for sx, sy in [(-1,-1),(1,-1),(-1,1),(1,1)]:
        x0 = boss_x + sx*lock_w
        y0 = boss_y + sy*lock_h
        pygame.draw.line(fondo,color,(x0,y0),(x0-sx*24,y0),2)
        pygame.draw.line(fondo,color,(x0,y0),(x0,y0-sy*24),2)
    for i in range(4):
        rr = int((42+i*20) * escala + math.sin(ticks*0.008+i)*5)
        pygame.draw.circle(fondo,(color[0],color[1],color[2],78),(boss_x,boss_y),rr,1)
    scan_txt = pygame.font.SysFont(None,18).render(("SCAN " if idioma_actual == "EN" else "ESCANEO ") + str(int(progreso*100)) + "%", True, mezclar_color(color,(255,255,255),0.4))
    fondo.blit(scan_txt,(boss_x-scan_txt.get_width()//2,boss_y+int(78*escala)))

    pantalla.blit(fondo,(0,0))

    # Cristal y estructura fisica de cabina.
    cristal = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    pygame.draw.polygon(cristal,(0,0,0,222),[(0,0),(118,0),(218,600),(0,600)])
    pygame.draw.polygon(cristal,(0,0,0,222),[(800,0),(682,0),(582,600),(800,600)])
    pygame.draw.polygon(cristal,(0,0,0,238),[(0,438),(800,438),(800,600),(0,600)])
    pygame.draw.polygon(cristal,(5,13,25,208),[(118,0),(682,0),(582,438),(218,438)])
    pygame.draw.polygon(cristal,(8,22,40,70),[(160,34),(640,34),(560,400),(240,400)])
    pygame.draw.polygon(cristal,(235,250,255,24),[(184,54),(616,54),(598,82),(202,86)],1)
    pygame.draw.line(cristal,(tema_planeta[0],tema_planeta[1],tema_planeta[2],85),(218,438),(118,0),3)
    pygame.draw.line(cristal,(tema_planeta[0],tema_planeta[1],tema_planeta[2],85),(582,438),(682,0),3)
    pygame.draw.line(cristal,(255,255,255,26),(250,76),(228,386),1)
    pygame.draw.line(cristal,(255,255,255,20),(550,68),(572,386),1)
    for i in range(5):
        y = 456 + i*20
        pygame.draw.line(cristal,(tema_planeta[0],tema_planeta[1],tema_planeta[2],28),(34,y),(766,y),1)
    pygame.draw.rect(cristal,(2,7,15,225),(26,448,748,126),border_radius=18)
    pygame.draw.rect(cristal,(color[0],color[1],color[2],70),(26,448,748,126),2,border_radius=18)
    pygame.draw.polygon(cristal,(0,0,0,145),[(246,448),(554,448),(602,574),(198,574)])
    pygame.draw.line(cristal,(color[0],color[1],color[2],55),(250,448),(198,574),2)
    pygame.draw.line(cristal,(color[0],color[1],color[2],55),(550,448),(602,574),2)
    pantalla.blit(cristal,(0,0))

    # HUD de cabina.
    hud = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    pygame.draw.rect(hud,(3,10,22,205),(46,474,192,70),border_radius=8)
    pygame.draw.rect(hud,(3,10,22,205),(562,474,192,70),border_radius=8)
    pygame.draw.rect(hud,(4,13,24,220),(266,454,268,98),border_radius=10)
    pygame.draw.rect(hud,(color[0],color[1],color[2],120),(46,474,192,70),1,border_radius=8)
    pygame.draw.rect(hud,(tema_planeta[0],tema_planeta[1],tema_planeta[2],120),(562,474,192,70),1,border_radius=8)
    pygame.draw.rect(hud,(color[0],color[1],color[2],115),(266,454,268,98),1,border_radius=10)
    vida_ratio = max(0, min(1, estado.get("hp", estado.get("vidas",100)) / max(1, estado.get("max_hp",100))))
    pygame.draw.rect(hud,(18,36,54),(68,512,146,10),border_radius=5)
    pygame.draw.rect(hud,(80,255,160),(68,512,int(146*vida_ratio),10),border_radius=5)
    energia = 0.5 + 0.5*math.sin(ticks*0.006)
    pygame.draw.rect(hud,(18,36,54),(584,512,146,10),border_radius=5)
    pygame.draw.rect(hud,tema_planeta,(584,512,int(146*energia),10),border_radius=5)
    scan_cx, scan_cy = 400, 500
    for i in range(8):
        ang = ticks*0.004+i*math.pi*2/8
        x = scan_cx + int(math.cos(ang)*64)
        y = scan_cy + int(math.sin(ang)*27)
        pygame.draw.circle(hud,color,(x,y),3)
        pygame.draw.line(hud,(color[0],color[1],color[2],70),(scan_cx,scan_cy),(x,y),1)
    pygame.draw.ellipse(hud,(color[0],color[1],color[2],95),(scan_cx-86,scan_cy-42,172,84),1)
    pygame.draw.ellipse(hud,(color[0],color[1],color[2],62),(scan_cx-55,scan_cy-27,110,54),1)
    sweep = ticks*0.006
    pygame.draw.line(hud,mezclar_color(color,(255,255,255),0.48),(scan_cx,scan_cy),(int(scan_cx+math.cos(sweep)*82),int(scan_cy+math.sin(sweep)*38)),2)
    pygame.draw.circle(hud,(255,255,255,75),(scan_cx,scan_cy),7,1)
    pygame.draw.rect(hud,(color[0],color[1],color[2],70),(scan_cx-22,scan_cy-44,44,88),1)
    pygame.draw.line(hud,(color[0],color[1],color[2],90),(scan_cx-96,scan_cy),(scan_cx-68,scan_cy),2)
    pygame.draw.line(hud,(color[0],color[1],color[2],90),(scan_cx+68,scan_cy),(scan_cx+96,scan_cy),2)

    texto_sistemas = "SISTEMAS" if idioma_actual != "EN" else "SYSTEMS"
    texto_escaneo = "ESCANEO" if idioma_actual != "EN" else "SCAN"
    texto_armas = "ARMAS" if idioma_actual != "EN" else "WEAPONS"
    hud.blit(pygame.font.SysFont(None,22).render(texto_sistemas, True, (230,245,255)),(68,486))
    hud.blit(pygame.font.SysFont(None,18).render("HP " + str(int(vida_ratio*100)) + "%", True, (160,230,210)),(68,526))
    hud.blit(pygame.font.SysFont(None,22).render(texto_escaneo, True, (230,245,255)),(584,486))
    hud.blit(pygame.font.SysFont(None,18).render(texto_armas + " " + str(int(energia*100)) + "%", True, (170,220,245)),(584,526))

    mensaje = ("FIJANDO OBJETIVO: " if idioma_actual != "EN" else "LOCKING TARGET: ") + nombre[:22]
    mensaje2 = "CABINA PRIMERA PERSONA" if idioma_actual != "EN" else "FIRST PERSON COCKPIT"
    hud.blit(pygame.font.SysFont(None,22).render(mensaje2, True, color),(ANCHO//2-112,462))
    hud.blit(pygame.font.SysFont(None,18).render(mensaje, True, (230,245,255)),(ANCHO//2-142,536))

    pantalla.blit(hud,(0,0))

    if estado.get("cockpit_scan",{}).get("active",False):
        dibujar_overlay_cabina_jugable_v69(color)

def dibujar_overlay_cabina_jugable_v69(color):
    scan = estado.get("cockpit_scan",{})
    ticks = pygame.time.get_ticks()
    tx, ty = int(scan.get("target_x",ANCHO//2)), int(scan.get("target_y",285))
    rx, ry = int(scan.get("x",ANCHO//2)), int(scan.get("y",285))
    progreso = max(0, min(100, scan.get("progress",0)))
    sistema = scan.get("system","weapons")
    preparado = scan.get("prepared",False)
    preparando = preparado and scan.get("prep_timer",0) > 0
    capa = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)

    if not preparado:
        pulse = 0.5 + 0.5*math.sin(ticks*0.012)
        target_img = asset_xfondo(ASSET_COCKPIT["target"], (92,92))
        if not blit_asset_centrado(capa,target_img,tx,ty,(92,92),alpha=185):
            pygame.draw.circle(capa,(color[0],color[1],color[2],36),(tx,ty),46+int(pulse*8),2)
            pygame.draw.circle(capa,(255,245,210,48),(tx,ty),18,1)
        for i in range(4):
            ang = ticks*0.006 + i*math.pi/2
            pygame.draw.line(capa,(color[0],color[1],color[2],70),(tx,ty),(int(tx+math.cos(ang)*62),int(ty+math.sin(ang)*38)),1)

        objetivo_color = (120,255,220) if progreso >= 100 else (230,245,255)
        reticle_img = asset_xfondo(ASSET_COCKPIT["reticle"], (82,82))
        if not blit_asset_centrado(capa,reticle_img,rx,ry,(82,82),alpha=225,rotacion=ticks*0.018):
            pygame.draw.line(capa,objetivo_color,(rx-28,ry),(rx-8,ry),2)
            pygame.draw.line(capa,objetivo_color,(rx+8,ry),(rx+28,ry),2)
            pygame.draw.line(capa,objetivo_color,(rx,ry-28),(rx,ry-8),2)
            pygame.draw.line(capa,objetivo_color,(rx,ry+8),(rx,ry+28),2)
            pygame.draw.circle(capa,objetivo_color,(rx,ry),34,1)

    panel = pygame.Rect(246,72,308,78)
    pygame.draw.rect(capa,(3,10,22,206),panel,border_radius=8)
    pygame.draw.rect(capa,(color[0],color[1],color[2],130),panel,1,border_radius=8)
    titulo = "ESCANEO DE AMENAZA" if idioma_actual != "EN" else "THREAT SCAN"
    texto = pygame.font.SysFont(None,21).render(titulo, True, (235,245,255))
    capa.blit(texto,(panel.centerx-texto.get_width()//2,panel.y+9))
    barra = pygame.Rect(panel.x+24,panel.y+38,panel.w-48,10)
    pygame.draw.rect(capa,(18,35,50),barra,border_radius=5)
    pygame.draw.rect(capa,(120,255,220), (barra.x,barra.y,int(barra.w*progreso/100),barra.h), border_radius=5)
    pygame.draw.rect(capa,(235,245,255),barra,1,border_radius=5)
    if preparado:
        hint = "SYSTEM READY | ENTER START ATTACK" if idioma_actual == "EN" else "SISTEMA LISTO | ENTER EMPEZAR ATAQUE"
    else:
        hint = "SPACE SCAN | 1 WEAPONS 2 SHIELD 3 REACTOR | ENTER PREPARE" if idioma_actual == "EN" else "ESPACIO ESCANEA | 1 ARMAS 2 ESCUDO 3 REACTOR | ENTER PREPARAR"
    hint_render = pygame.font.SysFont(None,16).render(hint, True, (165,210,225))
    capa.blit(hint_render,(panel.centerx-hint_render.get_width()//2,panel.y+56))

    sys_rect = pygame.Rect(286,158,228,34)
    pygame.draw.rect(capa,(2,8,16,178),sys_rect,border_radius=6)
    pygame.draw.rect(capa,(120,255,220,120) if progreso >= 100 else (color[0],color[1],color[2],95),sys_rect,1,border_radius=6)
    sys_text = ("SISTEMA: " if idioma_actual != "EN" else "SYSTEM: ") + nombre_sistema_cabina(sistema)
    sys_render = pygame.font.SysFont(None,21).render(sys_text, True, (230,245,255))
    capa.blit(sys_render,(sys_rect.centerx-sys_render.get_width()//2,sys_rect.y+8))
    system_img = asset_xfondo(ASSET_COCKPIT.get(sistema, ASSET_COCKPIT["weapons"]), (42,42))
    blit_asset_centrado(capa, system_img, sys_rect.x+23, sys_rect.centery, (42,42))

    if preparado:
        centro = (ANCHO//2, 304)
        prep_ratio = 1.0 - max(0, min(1, scan.get("prep_timer",0) / 150))
        system_color = {
            "weapons":(255,100,70),
            "shield":(90,255,170),
            "reactor":(120,210,255)
        }.get(sistema,color)
        for i in range(5):
            r = int(34 + i*22 + prep_ratio*38 + math.sin(ticks*0.01+i)*5)
            pygame.draw.circle(capa,(system_color[0],system_color[1],system_color[2],72-i*9),centro,r,2)
        if sistema == "weapons":
            for i in range(10):
                ang = ticks*0.012 + i*math.pi/5
                pygame.draw.line(capa,(255,180,110,125),centro,(int(centro[0]+math.cos(ang)*92),int(centro[1]+math.sin(ang)*46)),2)
        elif sistema == "shield":
            pygame.draw.arc(capa,(120,255,190,150),(centro[0]-115,centro[1]-64,230,128),0.1,ticks*0.008+4.8,4)
            pygame.draw.arc(capa,(210,255,235,105),(centro[0]-82,centro[1]-46,164,92),math.pi,ticks*0.006+math.pi+3.8,3)
        else:
            for i in range(8):
                x = centro[0] - 110 + i*31
                alto = int(14 + prep_ratio*52 + math.sin(ticks*0.012+i)*10)
                pygame.draw.rect(capa,(120,220,255,105),(x,centro[1]+52-alto,16,alto),border_radius=3)

        launch = scan.get("launch_ready",False)
        boton = pygame.Rect(286,386,228,42)
        pygame.draw.rect(capa,(5,16,26,215),boton,border_radius=9)
        pygame.draw.rect(capa,system_color if launch else (90,115,130),boton,2,border_radius=9)
        texto_boton = "START ATTACK" if idioma_actual == "EN" else "EMPEZAR ATAQUE"
        if not launch:
            texto_boton = "PREPARANDO..." if idioma_actual != "EN" else "PREPARING..."
        rb = pygame.font.SysFont(None,25).render(texto_boton, True, (235,250,255))
        capa.blit(rb,(boton.centerx-rb.get_width()//2,boton.centery-rb.get_height()//2))

    if scan.get("message_timer",0) > 0 and scan.get("message"):
        msg = pygame.font.SysFont(None,25).render(scan.get("message",""), True, (255,230,125))
        pygame.draw.rect(capa,(2,8,16,190),(ANCHO//2-msg.get_width()//2-18,206,msg.get_width()+36,34),border_radius=8)
        capa.blit(msg,(ANCHO//2-msg.get_width()//2,214))

    pantalla.blit(capa,(0,0))

def dibujar_transicion_cockpit_v66(tiempo_restante, color):
    max_t = max(1, estado.get("boss_intro_max", tiempo_restante))
    progreso = 1 - max(0, min(1, tiempo_restante / max_t))
    entrada = max(0, 1 - progreso / 0.22)
    salida = max(0, (progreso - 0.78) / 0.22)
    fuerza = max(entrada, salida)
    if fuerza <= 0:
        return

    ticks = pygame.time.get_ticks()
    capa = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    cx, cy = ANCHO//2, ALTO//2

    # ViÃ±eta suave y deformacion simulada: no tapa la cabina, la "empuja".
    alpha = int(95 * fuerza)
    pygame.draw.rect(capa,(0,0,0,alpha),(0,0,ANCHO,ALTO))
    for i in range(9):
        r = int(55 + i*54 + fuerza*75 + math.sin(ticks*0.008+i)*6)
        a = int((34 - i*3) * fuerza)
        pygame.draw.circle(capa,(color[0],color[1],color[2],max(0,a)),(cx,cy),r,2)

    for i in range(18):
        ang = ticks*0.006 + i*math.pi*2/18
        largo = int(90 + fuerza*170)
        x1 = int(cx + math.cos(ang)*(65 + fuerza*30))
        y1 = int(cy + math.sin(ang)*(42 + fuerza*20))
        x2 = int(cx + math.cos(ang)*largo)
        y2 = int(cy + math.sin(ang)*largo*0.72)
        pygame.draw.line(capa,(color[0],color[1],color[2],int(42*fuerza)),(x1,y1),(x2,y2),1)

    if entrada > 0:
        texto = "ENTRANDO EN CABINA" if idioma_actual != "EN" else "ENTERING COCKPIT"
    else:
        texto = "VOLVIENDO AL COMBATE" if idioma_actual != "EN" else "RETURNING TO COMBAT"
    render = pygame.font.SysFont(None,22).render(texto, True, mezclar_color(color,(255,255,255),0.45))
    pygame.draw.rect(capa,(2,8,18,int(120*fuerza)),(ANCHO//2-160,88,320,34),border_radius=8)
    pygame.draw.rect(capa,(color[0],color[1],color[2],int(120*fuerza)),(ANCHO//2-160,88,320,34),1,border_radius=8)
    capa.blit(render,(ANCHO//2-render.get_width()//2,96))

    if salida > 0.65:
        flash_alpha = int((salida-0.65)/0.35 * 80)
        capa.fill((color[0],color[1],color[2],flash_alpha), special_flags=pygame.BLEND_RGBA_ADD)

    pantalla.blit(capa,(0,0))

def dibujar_marco_cabina_simple_v66(color, alerta_texto="", subtitulo=""):
    capa = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    pygame.draw.polygon(capa,(0,0,0,185),[(0,0),(118,0),(205,600),(0,600)])
    pygame.draw.polygon(capa,(0,0,0,185),[(800,0),(682,0),(595,600),(800,600)])
    pygame.draw.polygon(capa,(0,0,0,205),[(0,478),(800,478),(800,600),(0,600)])
    pygame.draw.line(capa,(color[0],color[1],color[2],85),(118,0),(205,478),2)
    pygame.draw.line(capa,(color[0],color[1],color[2],85),(682,0),(595,478),2)
    pygame.draw.rect(capa,(3,10,22,135),(260,500,280,58),border_radius=8)
    pygame.draw.rect(capa,(color[0],color[1],color[2],105),(260,500,280,58),1,border_radius=8)
    if alerta_texto:
        capa.blit(pygame.font.SysFont(None,22).render(alerta_texto, True, (230,245,255)),(ANCHO//2-126,512))
    if subtitulo:
        capa.blit(pygame.font.SysFont(None,18).render(subtitulo, True, color),(ANCHO//2-126,535))
    pantalla.blit(capa,(0,0))

def dibujar_cabina_scale0_v66(ticks):
    color = (120,255,235)
    for i in range(8):
        r = int(70+i*52+math.sin(ticks*0.004+i)*10)
        pygame.draw.circle(pantalla,(80,255,235), (ANCHO//2,ALTO//2), r, 1)
    for i in range(16):
        x = int((i*73 + ticks*0.2) % ANCHO)
        y = int((i*59 + math.sin(ticks*0.006+i)*90 + ALTO//2) % ALTO)
        pygame.draw.rect(pantalla,(120,255,240),(x-8,y-8,16,16),1)
    texto = "CABINA SCALE-0" if idioma_actual != "EN" else "SCALE-0 COCKPIT"
    sub = "NAVEGACION ANOMALA" if idioma_actual != "EN" else "ANOMALOUS NAVIGATION"
    dibujar_marco_cabina_simple_v66(color, texto, sub)

def dibujar_cabina_emergencia_v66():
    if estado.get("estado") != "JUGANDO" or estado.get("boss_intro",0) > 0:
        return
    max_hp = max(1, estado.get("max_hp",100))
    hp = estado.get("hp", estado.get("vidas", max_hp))
    if hp > max_hp * 0.28:
        return
    ticks = pygame.time.get_ticks()
    alpha = 20 + int(abs(math.sin(ticks*0.012))*28)
    capa = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    pygame.draw.rect(capa,(255,35,35,alpha),(0,0,ANCHO,ALTO),6)
    for i in range(6):
        x = int((i*161 + math.sin(ticks*0.005+i)*25) % ANCHO)
        pygame.draw.line(capa,(255,80,80,36),(x,0),(x+35,ALTO),1)
    texto = "CABINA DANADA" if idioma_actual != "EN" else "COCKPIT DAMAGED"
    sub = "SISTEMAS CRITICOS" if idioma_actual != "EN" else "CRITICAL SYSTEMS"
    pantalla.blit(capa,(0,0))
    dibujar_marco_cabina_simple_v66((255,65,65), texto, sub)

def dibujar_intro_boss(offset_x, offset_y):
    if estado.get("boss_intro",0) <= 0:
        return

    t = estado["boss_intro"]
    tipo = estado.get("boss_intro_tipo","normal")
    nombre = estado.get("boss_intro_nombre","WARNING")

    overlay = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)

    if tipo == "normal":
        color = (255,40,40)
        alpha = 100
        titulo = "WARNING"
    elif tipo == "final":
        color = (190,40,255)
        alpha = 135
        titulo = "DANGER"
    else:
        color = (255,60,35)
        alpha = 150
        titulo = "SYSTEM ALERT"

    color = color_cockpit_por_tipo_v66(tipo)
    dibujar_cabina_primera_persona_v66(tipo, nombre, t, offset_x, offset_y, color)
    dibujar_transicion_cockpit_v66(t, color)

    overlay.fill((0,0,0,6))
    pantalla.blit(overlay,(0,0))

    pygame.draw.rect(pantalla,(0,0,0),(0,0,ANCHO,46))

    desplazamiento = (t * 8) % 80

    for x in range(-80, ANCHO+80, 80):
        pygame.draw.line(
            pantalla,
            color,
            (x+desplazamiento,52),
            (x+desplazamiento+28,52),
            2
        )

    texto_titulo = pygame.font.SysFont(None,30).render(titulo, True, color)
    texto_nombre = pygame.font.SysFont(None,24).render(nombre, True, BLANCO)
    texto_sub = pygame.font.SysFont(None,17).render(
        "ENTRADA DE AMENAZA DETECTADA" if idioma_actual != "EN" else "THREAT ENTRY DETECTED",
        True,
        mezclar_color(color,(255,255,255),0.42)
    )
    pantalla.blit(texto_titulo,(24,10))
    pantalla.blit(texto_nombre,(ANCHO//2 - texto_nombre.get_width()//2,9))
    pantalla.blit(texto_sub,(ANCHO - texto_sub.get_width() - 24,15))

    carga = 1 - max(0, min(1, t / max(1, estado.get("boss_intro_max", t))))
    barra_w = 360
    barra_x = ANCHO//2 - barra_w//2
    pygame.draw.rect(pantalla,(4,8,18),(barra_x,58,barra_w,7),border_radius=4)
    pygame.draw.rect(pantalla,color,(barra_x,58,int(barra_w*carga),7),border_radius=4)
    pygame.draw.rect(pantalla,(235,245,255),(barra_x,58,barra_w,7),1,border_radius=4)

    scan_y = int(92 + math.sin(pygame.time.get_ticks()*0.008)*18)
    pygame.draw.line(pantalla,(color[0],color[1],color[2]),(255,scan_y),(545,scan_y),1)


# =====================
# ULTIMATE ATTACKS - SOLO BOSSES
# =====================
def hay_boss_activo():
    return (
        estado.get("boss") is not None or
        estado.get("boss_final") is not None or
        estado.get("boss_laser") is not None or
        estado.get("boss_overmind") is not None or
        estado.get("boss_rift") is not None or
        estado.get("boss_hollow") is not None or
        estado.get("boss_sun_eater") is not None or
        estado.get("boss_eden") is not None
    )

def obtener_boss_activo():
    if estado.get("boss"):
        return estado["boss"], "boss"
    if estado.get("boss_final"):
        return estado["boss_final"], "boss_final"
    if estado.get("boss_laser"):
        return estado["boss_laser"], "boss_laser"
    if estado.get("boss_overmind"):
        return estado["boss_overmind"], "boss_overmind"
    if estado.get("boss_rift"):
        return estado["boss_rift"], "boss_rift"
    if estado.get("boss_hollow"):
        return estado["boss_hollow"], "boss_hollow"
    if estado.get("boss_sun_eater"):
        return estado["boss_sun_eater"], "boss_sun_eater"
    if estado.get("boss_eden"):
        return estado["boss_eden"], "boss_eden"
    return None, None

def centro_boss_activo():
    boss, tipo = obtener_boss_activo()

    if boss is None:
        return ANCHO//2, 120

    if tipo == "boss":
        return boss["x"]+75, boss["y"]+75

    if tipo == "boss_final":
        return boss["x"]+85, boss["y"]+85

    if tipo == "boss_overmind":
        return boss["x"]+105, boss["y"]+105

    if tipo == "boss_rift":
        return boss["x"]+110, boss["y"]+110

    if tipo in ["boss_hollow", "boss_sun_eater", "boss_eden"]:
        return boss["x"]+115, boss["y"]+115

    return boss["x"]+95, boss["y"]+95

def particulas_black_hole(cx, cy):
    for _ in range(18):
        ang = random.uniform(0, math.pi*2)
        radio = random.randint(70,210)
        particulas.append([
            cx + math.cos(ang)*radio,
            cy + math.sin(ang)*radio,
            -math.cos(ang)*random.uniform(1,4),
            -math.sin(ang)*random.uniform(1,4),
            random.randint(18,38)
        ])

def particulas_orbital(x):
    for _ in range(24):
        particulas.append([
            x + random.randint(-55,55),
            random.randint(0,ALTO),
            random.uniform(-2,2),
            random.uniform(-4,4),
            random.randint(16,34)
        ])

def particulas_overdrive(x, y):
    for _ in range(14):
        particulas.append([
            x + random.randint(-15,75),
            y + random.randint(0,60),
            random.uniform(-3,3),
            random.uniform(-3,3),
            random.randint(12,26)
        ])

# =====================
# ESTRELLAS
# =====================
estrellas=[
    {
        "x":random.randint(0,ANCHO),
        "y":random.randint(0,ALTO),
        "vel":random.uniform(0.5,2)
    }
    for _ in range(120)
]

# =====================
# FONDO CON PROFUNDIDAD
# =====================
estrellas_lejanas=[
    {
        "x":random.randint(0,ANCHO),
        "y":random.randint(0,ALTO),
        "vel":random.uniform(0.15,0.45),
        "r":random.choice([1,1,1,2])
    }
    for _ in range(90)
]

estrellas_medias=[
    {
        "x":random.randint(0,ANCHO),
        "y":random.randint(0,ALTO),
        "vel":random.uniform(0.7,1.5),
        "r":random.choice([1,2])
    }
    for _ in range(70)
]

nebulosas=[
    {
        "x":random.randint(-200,ANCHO),
        "y":random.randint(-200,ALTO),
        "vel":random.uniform(0.08,0.25),
        "radio":random.randint(90,180),
        "alpha":random.randint(18,38),
        "tipo":random.choice(["azul","morado","rojo"])
    }
    for _ in range(8)
]

meteoritos_fondo=[]

# =====================
# MENU CINEMATICO Y FONDOS VIVOS EXTRA
# =====================
menu_estrellas=[
    {
        "x":random.randint(0,ANCHO),
        "y":random.randint(0,ALTO),
        "vel":random.uniform(0.15,0.9),
        "r":random.choice([1,1,2])
    }
    for _ in range(130)
]

menu_nebulosas=[
    {
        "x":random.randint(-150,ANCHO),
        "y":random.randint(-150,ALTO),
        "radio":random.randint(100,220),
        "vel":random.uniform(0.05,0.18),
        "color":random.choice([
            (60,120,255),
            (150,60,255),
            (255,60,120)
        ]),
        "alpha":random.randint(18,42)
    }
    for _ in range(7)
]

menu_decor_ships=[
    {
        "x":random.randint(-300,ANCHO),
        "y":random.randint(80,420),
        "vel":random.uniform(0.35,0.9),
        "scale":random.uniform(0.45,0.85),
        "tipo":random.choice([1,2])
    }
    for _ in range(4)
]

menu_asteroides=[
    {
        "x":random.randint(-500,ANCHO),
        "y":random.randint(30,ALTO-80),
        "vel":random.uniform(0.8,2.4),
        "rot":random.randint(0,360),
        "rot_vel":random.uniform(-1.8,1.8),
        "size":random.randint(24,70),
        "depth":random.uniform(0.45,1.15)
    }
    for _ in range(9)
]

menu_cometas=[]

planetas_fondo=[
    {
        "x":random.randint(80,ANCHO-80),
        "y":random.randint(40,260),
        "radio":random.randint(34,72),
        "vel":random.uniform(0.015,0.05),
        "color":random.choice([
            (70,130,255),
            (160,70,255),
            (255,90,70),
            (70,220,180)
        ]),
        "alpha":random.randint(8,18)
    }
    for _ in range(2)
]

tormentas_fondo=[
    {
        "x":random.randint(0,ANCHO),
        "y":random.randint(0,ALTO),
        "vida":random.randint(80,240),
        "max":240
    }
    for _ in range(3)
]

def dibujar_planetas_fondo(nivel, offset_x, offset_y):
    # Planetas decorativos lentos con glow suave.
    capa = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)

    for p in planetas_fondo:
        p["y"] += p["vel"] * slowmo

        if p["y"] > ALTO + 160:
            p["y"] = -160
            p["x"] = random.randint(80,ANCHO-80)

        color = p["color"]

        if nivel >= 4:
            color = (
                min(255,(color[0]+220)//2),
                max(0,(color[1]+35)//2),
                max(0,(color[2]+45)//2)
            )

        pygame.draw.circle(
            capa,
            (color[0],color[1],color[2],max(4,p["alpha"]//2)),
            (
                int(p["x"]+offset_x*0.08),
                int(p["y"]+offset_y*0.08)
            ),
            max(18,int(p["radio"]*0.72))
        )

        pygame.draw.circle(
            capa,
            (255,255,255,5),
            (
                int(p["x"]-p["radio"]//3+offset_x*0.08),
                int(p["y"]-p["radio"]//3+offset_y*0.08)
            ),
            max(4,p["radio"]//8)
        )

    pantalla.blit(capa,(0,0))

def dibujar_tormentas_fondo(nivel, offset_x, offset_y):
    if nivel < 4:
        return

    for t in tormentas_fondo:
        t["vida"] -= 1

        if t["vida"] <= 0:
            t["x"] = random.randint(0,ANCHO)
            t["y"] = random.randint(0,ALTO)
            t["vida"] = random.randint(120,260)

        if random.randint(1,35)==1:
            pygame.draw.line(
                pantalla,
                (255,80,100),
                (
                    int(t["x"]+offset_x*0.2),
                    int(t["y"]+offset_y*0.2)
                ),
                (
                    int(t["x"]+random.randint(-80,80)+offset_x*0.2),
                    int(t["y"]+random.randint(-80,80)+offset_y*0.2)
                ),
                1
            )

def dibujar_fondo_menu_animado(intensidad=1.0):
    tiempo = pygame.time.get_ticks() / 1000

    pantalla.fill((0,0,14))

    capa_neb = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)

    for n in menu_nebulosas:
        n["y"] += n["vel"] * 0.85 * intensidad

        if n["y"] > ALTO + 220:
            n["y"] = -220
            n["x"] = random.randint(-150,ANCHO)

        pulso = int(7*math.sin(tiempo*1.4 + n["x"]))
        color = n["color"]

        pygame.draw.circle(
            capa_neb,
            (color[0],color[1],color[2],max(5,n["alpha"]+pulso)),
            (
                int(n["x"]),
                int(n["y"])
            ),
            n["radio"]
        )

    pantalla.blit(capa_neb,(0,0))

    # estrellas animadas
    for e in menu_estrellas:
        e["y"] += e["vel"] * intensidad

        if e["y"] > ALTO:
            e["y"] = 0
            e["x"] = random.randint(0,ANCHO)

        pygame.draw.circle(
            pantalla,
            (180,180,220),
            (
                int(e["x"]),
                int(e["y"])
            ),
            e["r"]
        )

    # asteroides decorativos
    for a in menu_asteroides:
        a["x"] += a["vel"] * a["depth"] * intensidad
        a["y"] += math.sin(tiempo + a["x"]*0.01) * 0.15
        a["rot"] += a["rot_vel"]

        if a["x"] > ANCHO + 140:
            a["x"] = random.randint(-500,-120)
            a["y"] = random.randint(30,ALTO-80)
            a["vel"] = random.uniform(0.8,2.4)
            a["size"] = random.randint(24,70)
            a["depth"] = random.uniform(0.45,1.15)

        ast_img = pygame.transform.scale(asteroid_img,(a["size"],a["size"]))
        ast_img = pygame.transform.rotate(ast_img,a["rot"])

        crear_glow(
            pantalla,
            int(a["x"]+a["size"]//2),
            int(a["y"]+a["size"]//2),
            max(18,int(a["size"]*0.8)),
            (150,150,170),
            int(22*a["depth"])
        )

        pantalla.blit(ast_img,(a["x"],a["y"]))

    # cometas
    if random.randint(1,190)==1 and len(menu_cometas)<3:
        menu_cometas.append([
            random.randint(-120,ANCHO),
            random.randint(-80,180),
            random.uniform(4,7),
            random.uniform(2,4),
            random.randint(45,80)
        ])

    nuevos_menu_cometas=[]

    for c in menu_cometas:
        c[0]+=c[2] * intensidad
        c[1]+=c[3] * intensidad
        c[4]-=1

        pygame.draw.line(
            pantalla,
            (100,220,255),
            (
                int(c[0]),
                int(c[1])
            ),
            (
                int(c[0]-70),
                int(c[1]-45)
            ),
            3
        )

        crear_glow(
            pantalla,
            int(c[0]),
            int(c[1]),
            22,
            (100,220,255),
            70
        )

        pygame.draw.circle(
            pantalla,
            (220,250,255),
            (
                int(c[0]),
                int(c[1])
            ),
            4
        )

        if c[0]<ANCHO+140 and c[1]<ALTO+120 and c[4]>0:
            nuevos_menu_cometas.append(c)

    menu_cometas[:] = nuevos_menu_cometas

    # naves decorativas de fondo
    for s in menu_decor_ships:
        s["x"] += s["vel"] * intensidad

        if s["x"] > ANCHO + 200:
            s["x"] = -250
            s["y"] = random.randint(80,420)
            s["scale"] = random.uniform(0.45,0.85)
            s["tipo"] = random.choice([1,2])

        img_base = nave_img if s["tipo"] == 1 else nave2_img
        tam = max(25,int(60*s["scale"]))
        img = pygame.transform.scale(img_base,(tam,tam))

        crear_glow(
            pantalla,
            int(s["x"]+tam//2),
            int(s["y"]+tam//2),
            int(24*s["scale"]),
            (40,180,255) if s["tipo"]==1 else (255,220,120),
            38
        )

        pantalla.blit(img,(s["x"],s["y"]))

    # lï¿½neas hologrï¿½ficas sutiles
    for i in range(8):
        x_line = int((i*120 + tiempo*18) % (ANCHO+160)) - 80
        pygame.draw.line(
            pantalla,
            (20,90,140),
            (x_line,0),
            (x_line-120,ALTO),
            1
        )


def aplicar_admin_next_run():
    global shake, flash, slowmo, slowmo_timer

    if admin_next_mode == "normal":
        return

    estado["score"] = admin_next_score
    estado["enemigos"].clear()
    estado["balas_enemigas"].clear()
    estado["boss"] = None
    estado["boss_final"] = None
    estado["boss_laser"] = None
    if "boss_overmind" in estado:
        estado["boss_overmind"] = None
    if "boss_rift" in estado:
        estado["boss_rift"] = None
    if "boss_hollow" in estado:
        estado["boss_hollow"] = None
    if "boss_sun_eater" in estado:
        estado["boss_sun_eater"] = None
    if "boss_eden" in estado:
        estado["boss_eden"] = None

    if admin_next_mode == "level4":
        estado["boss_spawned"] = True
        estado["boss_final_spawned"] = True
        estado["boss_laser_spawned"] = False

    elif admin_next_mode == "level5":
        estado["score"] = 280000
        estado["boss_spawned"] = True
        estado["boss_final_spawned"] = True
        estado["boss_laser_spawned"] = False
        estado["boss_overmind_spawned"] = False
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        estado["void_zones"].clear()
        estado["tentacles"].clear()
        flash = 10
        shake = 18

    elif admin_next_mode == "overmind":
        estado["score"] = 360000
        estado["boss_spawned"] = True
        estado["boss_final_spawned"] = True
        estado["boss_laser_spawned"] = True
        estado["boss_overmind_spawned"] = True
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        estado["void_zones"].clear()
        estado["tentacles"].clear()
        estado["boss_overmind"] = {
            "x":295,
            "y":35,
            "vida":750,
            "dir":1,
            "cool":0
        }
        activar_intro_boss("final", "THE OVERMIND", 160)
        flash = 18
        shake = 40
        slowmo = 1
        slowmo_timer = 0

    elif admin_next_mode == "level6":
        estado["score"] = 520000
        estado["boss_spawned"] = True
        estado["boss_final_spawned"] = True
        estado["boss_laser_spawned"] = True
        estado["boss_overmind_spawned"] = True
        estado["boss_rift_spawned"] = False
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        estado["rift_attacks"].clear()
        estado["quantum_fields"].clear()
        estado["void_zones"].clear()
        estado["tentacles"].clear()
        flash = 10
        shake = 20

    elif admin_next_mode == "rift_boss":
        estado["score"] = 720000
        estado["boss_spawned"] = True
        estado["boss_final_spawned"] = True
        estado["boss_laser_spawned"] = True
        estado["boss_overmind_spawned"] = True
        estado["boss_rift_spawned"] = True
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        estado["rift_attacks"].clear()
        estado["quantum_fields"].clear()
        estado["void_zones"].clear()
        estado["tentacles"].clear()
        estado["boss_rift"] = {
            "x":290,
            "y":25,
            "vida":950,
            "dir":1,
            "cool":0,
            "teleport":0
        }
        activar_intro_boss("final", "THE RIFT MONARCH", 170)
        flash = 20
        shake = 45
        slowmo = 1
        slowmo_timer = 0

    elif admin_next_mode == "level7":
        estado["score"] = 760000
        estado["boss_spawned"] = True
        estado["boss_final_spawned"] = True
        estado["boss_laser_spawned"] = True
        estado["boss_overmind_spawned"] = True
        estado["boss_rift_spawned"] = True
        estado["boss_hollow_spawned"] = False
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        estado["abyss_zones"].clear()
        estado["silence_rings"].clear()
        flash = 10
        shake = 22

    elif admin_next_mode == "hollow_boss":
        estado["score"] = 1040000
        estado["boss_spawned"] = True
        estado["boss_final_spawned"] = True
        estado["boss_laser_spawned"] = True
        estado["boss_overmind_spawned"] = True
        estado["boss_rift_spawned"] = True
        estado["boss_hollow_spawned"] = True
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        estado["abyss_zones"].clear()
        estado["silence_rings"].clear()
        estado["boss_hollow"] = {"x":285,"y":22,"vida":1150,"dir":1,"cool":0}
        activar_intro_boss("final", "THE HOLLOW SAINT", 170)
        flash = 20
        shake = 48
        slowmo = 1
        slowmo_timer = 0

    elif admin_next_mode == "level8":
        estado["score"] = 1050000
        estado["boss_spawned"] = True
        estado["boss_final_spawned"] = True
        estado["boss_laser_spawned"] = True
        estado["boss_overmind_spawned"] = True
        estado["boss_rift_spawned"] = True
        estado["boss_hollow_spawned"] = True
        estado["boss_sun_eater_spawned"] = False
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        estado["solar_waves"].clear()
        flash = 10
        shake = 24

    elif admin_next_mode == "sun_boss":
        estado["score"] = 1380000
        estado["boss_spawned"] = True
        estado["boss_final_spawned"] = True
        estado["boss_laser_spawned"] = True
        estado["boss_overmind_spawned"] = True
        estado["boss_rift_spawned"] = True
        estado["boss_hollow_spawned"] = True
        estado["boss_sun_eater_spawned"] = True
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        estado["solar_waves"].clear()
        estado["boss_sun_eater"] = {"x":285,"y":24,"vida":1300,"dir":1,"cool":0,"angle":0}
        activar_intro_boss("laser", "THE SUN EATER", 175)
        flash = 24
        shake = 54
        slowmo = 1
        slowmo_timer = 0

    elif admin_next_mode == "level9":
        estado["score"] = 1400000
        estado["boss_spawned"] = True
        estado["boss_final_spawned"] = True
        estado["boss_laser_spawned"] = True
        estado["boss_overmind_spawned"] = True
        estado["boss_rift_spawned"] = True
        estado["boss_hollow_spawned"] = True
        estado["boss_sun_eater_spawned"] = True
        estado["boss_eden_spawned"] = False
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        estado["eden_roots"].clear()
        estado["crystal_rain"].clear()
        estado["life_pulses"].clear()
        flash = 10
        shake = 26

    elif admin_next_mode == "eden_boss":
        estado["score"] = 1750000
        estado["boss_spawned"] = True
        estado["boss_final_spawned"] = True
        estado["boss_laser_spawned"] = True
        estado["boss_overmind_spawned"] = True
        estado["boss_rift_spawned"] = True
        estado["boss_hollow_spawned"] = True
        estado["boss_sun_eater_spawned"] = True
        estado["boss_eden_spawned"] = True
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        estado["eden_roots"].clear()
        estado["crystal_rain"].clear()
        estado["life_pulses"].clear()
        estado["boss_eden"] = {"x":285,"y":20,"vida":1500,"dir":1,"cool":0}
        activar_intro_boss("final", "EDEN PRIME", 190)
        flash = 28
        shake = 62
        slowmo = 1
        slowmo_timer = 0

    elif admin_next_mode == "scale0_event":
        estado["score"] = 300000
        estado["boss_spawned"] = True
        estado["boss_final_spawned"] = True
        estado["boss_laser_spawned"] = True
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        estado["wormhole_forced"] = True
        estado["wormhole_cd"] = 1
        estado["wormhole_event"] = None
        estado["ultimate_message"] = 160
        estado["ultimate_message_text"] = texto_scale0("armed")
        flash = 12
        shake = 18

    elif admin_next_mode == "scale0_direct":
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        desbloquear_scale0()
        iniciar_scale0_directo()

    elif admin_next_mode == "boss1":
        estado["boss"] = {
            "x":300,
            "y":50,
            "vida":200,
            "dir":1,
            "cool":0
        }
        estado["boss_spawned"] = True
        activar_intro_boss("normal", "ASTEROID COMMANDER", 90)
        shake = 20

    elif admin_next_mode == "boss2":
        estado["boss_final"] = {
            "x":250,
            "y":50,
            "vida":400,
            "dir":1,
            "cool":0
        }
        estado["boss_spawned"] = True
        estado["boss_final_spawned"] = True
        activar_intro_boss("final", "OMEGA DESTROYER", 120)
        shake = 25

    elif admin_next_mode == "boss_laser":
        estado["boss_laser"] = {
            "x":250,
            "y":35,
            "vida":650,
            "dir":1,
            "cool":0
        }
        estado["boss_spawned"] = True
        estado["boss_final_spawned"] = True
        estado["boss_laser_spawned"] = True
        activar_intro_boss("laser", "LASER OVERLORD", 150)
        shake = 35
        flash = 12
        slowmo = 1
        slowmo_timer = 0

    elif admin_next_mode == "all_new_enemies":
        estado["boss_spawned"] = True
        estado["boss_final_spawned"] = True
        estado["boss_laser_spawned"] = False

        enemigos_prueba = [
            ("sentinel", 90, -70, 12),
            ("hunter", 240, -120, 10),
            ("void_orb", 410, -90, 14),
            ("laser_satellite", 570, -100, 16),
        ]

        for tipo_enemigo, x_enemigo, y_enemigo, vida_enemigo in enemigos_prueba:
            estado["enemigos"].append({
                "tipo":tipo_enemigo,
                "x":x_enemigo,
                "y":y_enemigo,
                "vida":vida_enemigo
            })

        shake = 18
        flash = 6


def dibujar_admin_panel():
    if not admin_panel and admin_message_timer <= 0:
        return

    overlay = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    overlay.fill((0,0,0,145))
    pantalla.blit(overlay,(0,0))

    panel = pygame.Rect(75,65,650,500)

    crear_rect_glow(
        pantalla,
        (panel.x,panel.y,panel.w,panel.h),
        (80,220,255),
        70,
        18
    )

    pygame.draw.rect(pantalla,(5,15,32),panel,border_radius=16)
    pygame.draw.rect(pantalla,(80,220,255),panel,2,border_radius=16)

    titulo_admin = pygame.font.SysFont(None,42).render("ADMIN ACCESS", True, BLANCO)
    pantalla.blit(
        titulo_admin,
        (
            panel.centerx - titulo_admin.get_width()//2,
            panel.y + 18
        )
    )

    if admin_panel:

        if admin_stage == "user":
            label = "USERNAME:"
            hint = "Enter username and press ENTER"
            shown_input = admin_input

        elif admin_stage == "coins":
            label = "COINS:"
            hint = "Enter amount. Use negative number to subtract"
            shown_input = admin_input

        elif admin_stage == "menu":
            menu_lines = [
                "A - Add coins",
                "B - Admin functions",
                "",
                "ESC - close"
            ]

            y = panel.y + 82
            for line in menu_lines:
                render = fuente.render(line, True, (200,230,255) if line else BLANCO)
                pantalla.blit(render,(panel.x+70,y))
                y += 35

            if admin_message_timer > 0 and admin_message:
                msg_render = fuente.render(admin_message, True, (255,230,120))
                pantalla.blit(
                    msg_render,
                    (
                        panel.centerx - msg_render.get_width()//2,
                        panel.y + 245
                    )
                )

            return

        elif admin_stage == "admin":
            fuente_admin = pygame.font.SysFont(None,18)
            menu_lines = [
                "A - Next run: Normal",
                "B - Level 4 enemies",
                "C - Boss 1",
                "D - Boss 2",
                "E - Laser Boss",
                "F - New enemy test",
                "G - Level 5 Void Swarm",
                "H - Overmind Boss",
                "I - Level 6 Quantum Rift",
                "J - Rift Monarch Boss",
                "K - Level 7 Silent Abyss",
                "L - Hollow Saint Boss",
                "M - Level 8 Solar Graveyard",
                "N - Sun Eater Boss",
                "O - Level 9 Eden Core",
                "P - Eden Prime Boss",
                "Q - Force Scale-0 Event",
                "R - Direct Scale-0 Labyrinth",
                "",
                "TYPE LETTER + ENTER | BACKSPACE - return"
            ]

            y = panel.y + 70
            for line in menu_lines:
                render = fuente_admin.render(line, True, (200,230,255) if line else BLANCO)
                pantalla.blit(render,(panel.x+55,y))
                y += 20

            command = fuente_admin.render("COMMAND: " + (admin_input if admin_input else "_"), True, (120,255,210))
            pantalla.blit(command,(panel.x+55,panel.y+430))

            active = fuente_admin.render("ACTIVE: " + admin_next_mode.upper(), True, (255,230,120))
            pantalla.blit(active,(panel.x+55,panel.y+455))

            if admin_message_timer > 0 and admin_message:
                msg_render = fuente_admin.render(admin_message, True, (255,230,120))
                pantalla.blit(
                    msg_render,
                    (
                        panel.centerx - msg_render.get_width()//2,
                        panel.y + 405
                    )
                )

            return

        label_render = fuente.render(label, True, (180,220,255))
        pantalla.blit(label_render,(panel.x+45,panel.y+82))

        input_rect = pygame.Rect(panel.x+45,panel.y+112,panel.w-90,38)
        pygame.draw.rect(pantalla,(0,0,0),input_rect,border_radius=8)
        pygame.draw.rect(pantalla,(120,220,255),input_rect,2,border_radius=8)

        blink = "_" if (pygame.time.get_ticks()//400)%2==0 else ""
        input_render = fuente.render(shown_input + blink, True, BLANCO)
        pantalla.blit(input_render,(input_rect.x+10,input_rect.y+8))

        hint_render = fuente_peq.render(hint, True, (150,190,220))
        pantalla.blit(hint_render,(panel.x+45,panel.y+162))

        esc_render = fuente_peq.render("ESC = close", True, (150,190,220))
        pantalla.blit(esc_render,(panel.x+45,panel.y+182))

    if admin_message_timer > 0 and admin_message:
        msg_render = fuente.render(admin_message, True, (255,230,120))
        pantalla.blit(
            msg_render,
            (
                panel.centerx - msg_render.get_width()//2,
                panel.y + 230
            )
        )


def dibujar_texto_multilinea(superficie, texto, x, y, ancho, fuente_usada, color, salto=24):
    palabras = texto.split(" ")
    linea = ""

    for palabra in palabras:
        prueba = linea + palabra + " "
        if fuente_usada.size(prueba)[0] <= ancho:
            linea = prueba
        else:
            render = fuente_usada.render(linea.strip(), True, color)
            superficie.blit(render,(x,y))
            y += salto
            linea = palabra + " "

    if linea.strip():
        render = fuente_usada.render(linea.strip(), True, color)
        superficie.blit(render,(x,y))
        y += salto

    return y

def numero_compacto(valor):
    try:
        valor = int(valor)
    except Exception:
        return str(valor)

    negativo = valor < 0
    valor_abs = abs(valor)
    unidades = [
        (1_000_000_000_000, "T"),
        (1_000_000_000, "B"),
        (1_000_000, "M"),
        (1_000, "K"),
    ]

    for base, sufijo in unidades:
        if valor_abs >= base:
            numero = valor_abs / base
            texto = f"{numero:.1f}{sufijo}" if numero < 100 else f"{int(numero)}{sufijo}"
            return ("-" if negativo else "") + texto

    return str(valor)

def fuente_ajustada(texto, max_ancho, tam_max=30, tam_min=13):
    for tam in range(tam_max, tam_min-1, -1):
        f = pygame.font.SysFont(None, tam)
        if f.size(str(texto))[0] <= max_ancho:
            return f
    return pygame.font.SysFont(None, tam_min)

def dibujar_texto_centrado_auto(superficie, texto, rect, color=BLANCO, tam_max=30, tam_min=13):
    f = fuente_ajustada(str(texto), rect[2]-10, tam_max, tam_min)
    render = f.render(str(texto), True, color)
    superficie.blit(
        render,
        (
            rect[0] + rect[2]//2 - render.get_width()//2,
            rect[1] + rect[3]//2 - render.get_height()//2
        )
    )

def dibujar_texto_multilinea_auto(superficie, texto, rect, color=BLANCO, tam_max=24, tam_min=13, salto_extra=3):
    texto = str(texto)

    for tam in range(tam_max, tam_min-1, -1):
        f = pygame.font.SysFont(None, tam)
        palabras = texto.split(" ")
        lineas = []
        linea = ""

        for palabra in palabras:
            prueba = (linea + palabra + " ").strip()
            if f.size(prueba)[0] <= rect[2]-12:
                linea = prueba + " "
            else:
                if linea.strip():
                    lineas.append(linea.strip())
                linea = palabra + " "

        if linea.strip():
            lineas.append(linea.strip())

        alto_total = len(lineas) * (tam + salto_extra)

        if alto_total <= rect[3]-8 or tam == tam_min:
            y = rect[1] + 5
            for linea_final in lineas:
                render = f.render(linea_final, True, color)
                superficie.blit(render,(rect[0]+6,y))
                y += tam + salto_extra
            return y

def dibujar_menu_cinematico():
    tiempo = pygame.time.get_ticks() / 1000

    pantalla.fill((0,0,12))

    capa_neb = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)

    for n in menu_nebulosas:
        n["y"] += n["vel"]

        if n["y"] > ALTO + 220:
            n["y"] = -220
            n["x"] = random.randint(-150,ANCHO)

        pulso = int(8*math.sin(tiempo*1.5 + n["x"]))
        color = n["color"]

        pygame.draw.circle(
            capa_neb,
            (color[0],color[1],color[2],max(5,n["alpha"]+pulso)),
            (
                int(n["x"]),
                int(n["y"])
            ),
            n["radio"]
        )

    pantalla.blit(capa_neb,(0,0))

    # estrellas del menï¿½ con profundidad
    for e in menu_estrellas:
        e["y"] += e["vel"]

        if e["y"] > ALTO:
            e["y"] = 0
            e["x"] = random.randint(0,ANCHO)

        pygame.draw.circle(
            pantalla,
            (180,180,220),
            (
                int(e["x"]),
                int(e["y"])
            ),
            e["r"]
        )

    # asteroides decorativos del menï¿½
    for a in menu_asteroides:
        a["x"] += a["vel"] * a["depth"]
        a["y"] += math.sin(tiempo + a["x"]*0.01) * 0.15
        a["rot"] += a["rot_vel"]

        if a["x"] > ANCHO + 140:
            a["x"] = random.randint(-500,-120)
            a["y"] = random.randint(30,ALTO-80)
            a["vel"] = random.uniform(0.8,2.4)
            a["size"] = random.randint(24,70)
            a["depth"] = random.uniform(0.45,1.15)

        ast_img = pygame.transform.scale(asteroid_img,(a["size"],a["size"]))
        ast_img = pygame.transform.rotate(ast_img,a["rot"])

        crear_glow(
            pantalla,
            int(a["x"]+a["size"]//2),
            int(a["y"]+a["size"]//2),
            max(18,int(a["size"]*0.8)),
            (150,150,170),
            int(22*a["depth"])
        )

        pantalla.blit(ast_img,(a["x"],a["y"]))

    # cometas decorativos ocasionales
    if random.randint(1,180)==1 and len(menu_cometas)<3:
        menu_cometas.append([
            random.randint(-120,ANCHO),
            random.randint(-80,180),
            random.uniform(4,7),
            random.uniform(2,4),
            random.randint(45,80)
        ])

    nuevos_menu_cometas=[]

    for c in menu_cometas:
        c[0]+=c[2]
        c[1]+=c[3]
        c[4]-=1

        pygame.draw.line(
            pantalla,
            (100,220,255),
            (
                int(c[0]),
                int(c[1])
            ),
            (
                int(c[0]-70),
                int(c[1]-45)
            ),
            3
        )

        crear_glow(
            pantalla,
            int(c[0]),
            int(c[1]),
            22,
            (100,220,255),
            70
        )

        pygame.draw.circle(
            pantalla,
            (220,250,255),
            (
                int(c[0]),
                int(c[1])
            ),
            4
        )

        if c[0]<ANCHO+140 and c[1]<ALTO+120 and c[4]>0:
            nuevos_menu_cometas.append(c)

    menu_cometas[:] = nuevos_menu_cometas

    # naves decorativas de fondo
    for s in menu_decor_ships:
        s["x"] += s["vel"]

        if s["x"] > ANCHO + 200:
            s["x"] = -250
            s["y"] = random.randint(80,420)
            s["scale"] = random.uniform(0.45,0.85)
            s["tipo"] = random.choice([1,2])

        img_base = nave_img if s["tipo"] == 1 else nave2_img
        tam = max(25,int(60*s["scale"]))
        img = pygame.transform.scale(img_base,(tam,tam))

        crear_glow(
            pantalla,
            int(s["x"]+tam//2),
            int(s["y"]+tam//2),
            int(24*s["scale"]),
            (40,180,255) if s["tipo"]==1 else (255,220,120),
            38
        )

        pantalla.blit(img,(s["x"],s["y"]))

    # nave principal flotante
    nave_menu = nave_img if nave_seleccionada == 1 else nave2_img
    nave_big = pygame.transform.smoothscale(nave_menu, hd_size((125,125)))

    nave_x = ANCHO//2 - nave_big.get_width()//2
    nave_y = 180 + int(math.sin(tiempo*2)*12)

    crear_glow(
        pantalla,
        ANCHO//2,
        nave_y+nave_big.get_height()//2,
        90,
        (40,180,255) if nave_seleccionada==1 else (255,220,120),
        70
    )

    pantalla.blit(nave_big,(nave_x,nave_y))

    # tï¿½tulo animado grande con glow
    titulo_font = pygame.font.SysFont(None,92)
    titulo = titulo_font.render("ScaleTale", True, BLANCO)
    titulo_glow = titulo_font.render("ScaleTale", True, (60,180,255))
    subtitulo = fuente.render(txt("subtitle"), True, (180,220,255))

    titulo_y = 58 + int(math.sin(tiempo*1.4)*4)

    crear_glow(
        pantalla,
        ANCHO//2,
        titulo_y+40,
        135,
        (60,180,255),
        58
    )

    pantalla.blit(
        titulo_glow,
        (
            ANCHO//2 - titulo_glow.get_width()//2 + 2,
            titulo_y + 2
        )
    )

    pantalla.blit(
        titulo,
        (
            ANCHO//2 - titulo.get_width()//2,
            titulo_y
        )
    )

    pygame.draw.line(
        pantalla,
        (80,220,255),
        (
            ANCHO//2 - 180,
            titulo_y + 84
        ),
        (
            ANCHO//2 + 180,
            titulo_y + 84
        ),
        2
    )

    pantalla.blit(
        subtitulo,
        (
            ANCHO//2 - subtitulo.get_width()//2,
            145
        )
    )

    # Monedas visibles en menï¿½
    coin_box = pygame.Rect(ANCHO-310, 26, 250, 48)
    crear_rect_glow(pantalla,coin_box,(255,220,80),38,10)
    pygame.draw.rect(pantalla,(22,16,4),coin_box,border_radius=10)
    pygame.draw.rect(pantalla,(255,220,80),coin_box,2,border_radius=10)
    pantalla.blit(moneda_img,(coin_box.x+12,coin_box.y+8))
    monedas_render = fuente.render(numero_compacto(monedas), True, BLANCO)
    pantalla.blit(monedas_render,(coin_box.x+58,coin_box.y+13))

    # Botones interactivos con hover
    mx,my = convertir_pos_mouse(pygame.mouse.get_pos())

    botones = [
        (start_btn, txt("start")),
        (options_btn, txt("ships")),
        (shop_btn, txt("shop")),
        (controls_btn, txt("controls")),
        (language_btn, txt("language")),
        (info_btn, txt("info")),
        (profile_btn, txt("profile")),
        (difficulty_btn, txt("difficulty")),
        (missions_btn, txt("missions")),
        (codex_btn, txt("codex")),
        (achievements_btn, txt("achievements")),
        (upgrades_btn, txt("upgrades")),
        (daily_btn, txt("daily")),
        (quit_btn, txt("quit")),
        (planet_btn, "PLANETS" if idioma_actual == "EN" else "PLANETAS")
    ]

    for rect,texto_boton in botones:
        hover = rect.collidepoint((mx,my))
        color_borde = (80,220,255) if hover else (100,120,160)
        color_fill = (20,45,75) if hover else (5,15,30)

        if hover:
            crear_rect_glow(
                pantalla,
                (rect.x,rect.y,rect.w,rect.h),
                (80,220,255),
                70,
                14
            )

        pygame.draw.rect(pantalla,color_fill,rect,border_radius=8)
        pygame.draw.rect(pantalla,color_borde,rect,2,border_radius=8)

        dibujar_texto_centrado_auto(pantalla, texto_boton, rect, BLANCO, 24, 13)

    # pequeï¿½o aviso
    build_hint = ("1-4 BUILDS: " if idioma_actual == "EN" else "1-4 RUTAS: ") + nombre_build_actual()
    build_render = fuente_peq.render(build_hint, True, (120,255,220))
    pantalla.blit(build_render,(ANCHO//2-build_render.get_width()//2,ALTO-55))
    ayuda = fuente_peq.render(txt("help"), True, (160,190,220))
    pantalla.blit(
        ayuda,
        (
            ANCHO//2 - ayuda.get_width()//2,
            ALTO-32
        )
    )

def dibujar_selector_planetas():
    dibujar_fondo_menu_animado(0.75)
    mx,my = convertir_pos_mouse(pygame.mouse.get_pos())
    titulo = pygame.font.SysFont(None,54).render("PLANET SELECT" if idioma_actual == "EN" else "SELECCIONA PLANETA", True, BLANCO)
    pantalla.blit(titulo,(ANCHO//2-titulo.get_width()//2,38))

    actual = PLANET_DEFS[planet_selector_index % len(PLANET_DEFS)]
    desbloqueado = planeta_desbloqueado(actual["id"])

    centro_x, centro_y = ANCHO//2, 250
    ticks = pygame.time.get_ticks()

    for rel in [-2,-1,0,1,2]:
        idx = (planet_selector_index + rel) % len(PLANET_DEFS)
        p = PLANET_DEFS[idx]
        locked = not planeta_desbloqueado(p["id"])
        escala = 1.0 - abs(rel)*0.22
        tam = int(166*escala*HD_VISUAL_SCALE)
        x = int(centro_x + rel*145 - tam//2)
        y = int(centro_y - tam//2 + abs(rel)*18 + math.sin(ticks*0.002+idx)*4)
        planeta = crear_planeta_selector_surface(p, max(70,tam), locked)
        if rel != 0:
            planeta.set_alpha(150 if not locked else 90)
        else:
            crear_glow(pantalla, centro_x, centro_y, 118, p["palette"][1], 42)
        pantalla.blit(planeta,(x,y))

    pygame.draw.polygon(pantalla,(120,230,255),[(planet_left_btn.centerx-16,planet_left_btn.centery),(planet_left_btn.centerx+14,planet_left_btn.centery-20),(planet_left_btn.centerx+14,planet_left_btn.centery+20)])
    pygame.draw.polygon(pantalla,(120,230,255),[(planet_right_btn.centerx+16,planet_right_btn.centery),(planet_right_btn.centerx-14,planet_right_btn.centery-20),(planet_right_btn.centerx-14,planet_right_btn.centery+20)])

    panel = pygame.Rect(135,360,530,78)
    crear_rect_glow(pantalla,(panel.x,panel.y,panel.w,panel.h),actual["palette"][1],30,10)
    pygame.draw.rect(pantalla,(4,12,26),panel,border_radius=8)
    pygame.draw.rect(pantalla,actual["palette"][1],panel,2,border_radius=8)

    nombre = texto_planeta(actual,"name") if not actual.get("secret",False) else "SCALE-0"
    nombre_render = pygame.font.SysFont(None,34).render(nombre, True, BLANCO)
    pantalla.blit(nombre_render,(panel.centerx-nombre_render.get_width()//2,panel.y+10))

    if actual.get("secret",False) and not desbloqueado:
        desc = "Se abre al encontrar el orbe." if idioma_actual != "EN" else "Opens only after finding the orb."
    elif actual.get("secret",False):
        desc = "Acceso directo al santuario laberinto." if idioma_actual != "EN" else "Direct access to the labyrinth sanctuary."
    elif desbloqueado:
        desc = texto_planeta(actual,"desc")
    else:
        desc = ("Desbloquea: " + str(actual["unlock_score"]) + " puntos o " + str(actual["unlock_bosses"]) + " bosses") if idioma_actual != "EN" else ("Unlock: " + str(actual["unlock_score"]) + " score or " + str(actual["unlock_bosses"]) + " bosses")
    desc_render = pygame.font.SysFont(None,22).render(desc, True, (190,220,235) if desbloqueado else (255,210,120))
    pantalla.blit(desc_render,(panel.centerx-desc_render.get_width()//2,panel.y+48))

    seleccionado = actual["id"] == planeta_seleccionado
    puede_select = desbloqueado
    hover_select = planet_select_btn.collidepoint((mx,my)) and puede_select
    color_btn = actual["palette"][1] if puede_select else (70,85,100)
    if hover_select:
        crear_rect_glow(pantalla,(planet_select_btn.x,planet_select_btn.y,planet_select_btn.w,planet_select_btn.h),color_btn,60,10)
    pygame.draw.rect(pantalla,(10,25,42) if puede_select else (16,18,24),planet_select_btn,border_radius=8)
    pygame.draw.rect(pantalla,color_btn,planet_select_btn,2,border_radius=8)
    texto_btn = "ENTER" if actual.get("secret",False) and idioma_actual == "EN" else ("ENTRAR" if actual.get("secret",False) else ("SELECTED" if seleccionado and idioma_actual == "EN" else ("SELECCIONADO" if seleccionado else ("SELECT" if idioma_actual == "EN" else "SELECCIONAR"))))
    if not puede_select:
        texto_btn = "LOCKED" if idioma_actual == "EN" else "BLOQUEADO"
    dibujar_texto_centrado_auto(pantalla,texto_btn,planet_select_btn,BLANCO,26,13)

    hover_back = planet_back_btn.collidepoint((mx,my))
    if hover_back:
        crear_rect_glow(pantalla,(planet_back_btn.x,planet_back_btn.y,planet_back_btn.w,planet_back_btn.h),(80,220,255),60,10)
    pygame.draw.rect(pantalla,(12,28,50) if not hover_back else (28,65,95),planet_back_btn,border_radius=10)
    pygame.draw.rect(pantalla,(80,180,240),planet_back_btn,2,border_radius=10)
    volver = fuente.render(txt("back"), True, BLANCO)
    pantalla.blit(volver,(planet_back_btn.centerx-volver.get_width()//2,planet_back_btn.centery-volver.get_height()//2))

def dibujar_fondo_profundo(nivel, offset_x, offset_y):
    global meteoritos_fondo
    ticks = pygame.time.get_ticks()

    # Base espacial por nivel
    if nivel <= 1:
        pantalla.fill((0,0,12))
        color_nebula_base=(40,80,180)
    elif nivel == 2:
        pantalla.fill((4,0,18))
        color_nebula_base=(120,40,180)
    elif nivel == 3:
        pantalla.fill((8,0,20))
        color_nebula_base=(80,60,220)
    elif nivel == 4:
        pantalla.fill((16,0,10))
        color_nebula_base=(210,45,60)
    elif nivel == 5:
        pantalla.fill((5,0,18))
        color_nebula_base=(145,35,220)
    elif nivel == 6:
        pantalla.fill((4,0,0))
        color_nebula_base=(255,40,40)
    elif nivel == 7:
        pantalla.fill((1,6,16))
        color_nebula_base=(18,82,128)
    elif nivel == 8:
        pantalla.fill((18,5,0))
        color_nebula_base=(255,150,35)
    else:
        pantalla.fill((0,12,10))
        color_nebula_base=(70,230,170)

    # Tema elegido en el selector de planetas: cambia atmosfera sin tocar gameplay.
    intensidad_planeta = 0.34 if planeta_seleccionado == "ares_prime" else 0.62
    color_nebula_base = tintar_color_planeta(color_nebula_base, intensidad_planeta)
    fondo_tinte = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    c_planeta = color_tema_planeta()
    alpha_tinte = 8 if planeta_seleccionado == "ares_prime" else 14
    fondo_tinte.fill((c_planeta[0],c_planeta[1],c_planeta[2],alpha_tinte))
    pantalla.blit(fondo_tinte,(0,0))

    # V57: atmosfera cinematica por nivel, suave y barata de dibujar.
    capa_ambiente = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    centro_luz = (
        int(ANCHO*0.5 + math.sin(ticks*0.004)*140 + offset_x*0.05),
        int(ALTO*0.28 + math.cos(ticks*0.003)*70 + offset_y*0.05)
    )
    for i in range(7):
        radio = 80 + i*46
        alpha = max(1, 5 - i//2)
        pygame.draw.circle(
            capa_ambiente,
            (color_nebula_base[0], color_nebula_base[1], color_nebula_base[2], alpha),
            centro_luz,
            radio
        )
    for i in range(5):
        x = int((i*210 - ticks*0.035 + offset_x*0.08) % (ANCHO+220) - 110)
        y = int(75 + i*92 + math.sin(ticks*0.006+i)*22)
        pygame.draw.ellipse(
            capa_ambiente,
            (min(255,color_nebula_base[0]+35), min(255,color_nebula_base[1]+35), min(255,color_nebula_base[2]+35), 3),
            (x, y, 260, 46)
        )
    pantalla.blit(capa_ambiente,(0,0))

    # Nebulosas suaves con transparencias
    capa_nebulosa = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)

    for n in nebulosas:
        n["y"] += n["vel"] * slowmo

        if n["y"] > ALTO + 220:
            n["y"] = -220
            n["x"] = random.randint(-200,ANCHO)

        if n["tipo"]=="azul":
            color=(40,110,255,n["alpha"])
        elif n["tipo"]=="morado":
            color=(160,60,255,n["alpha"])
        else:
            color=(255,50,70,n["alpha"])

        # Mezcla el color con el nivel para que el fondo cambie de ambiente
        color=(
            min(255,(color[0]+color_nebula_base[0])//2),
            min(255,(color[1]+color_nebula_base[1])//2),
            min(255,(color[2]+color_nebula_base[2])//2),
            color[3]
        )

        pygame.draw.circle(
            capa_nebulosa,
            (color[0],color[1],color[2],max(2,color[3]//5)),
            (
                int(n["x"]+offset_x*0.15),
                int(n["y"]+offset_y*0.15)
            ),
            max(24,int(n["radio"]*0.58))
        )

    pantalla.blit(capa_nebulosa,(0,0))

    # Planetas y tormentas decorativas de fondo
    dibujar_planetas_fondo(nivel, offset_x, offset_y)
    dibujar_tormentas_fondo(nivel, offset_x, offset_y)
    dibujar_atmosfera_planeta(nivel, offset_x, offset_y)

    # Estrellas lejanas
    for e in estrellas_lejanas:
        e["y"] += e["vel"] * slowmo

        if e["y"] > ALTO:
            e["y"] = 0
            e["x"] = random.randint(0,ANCHO)

        pygame.draw.circle(
            pantalla,
            (120,120,150),
            (
                int(e["x"]+offset_x*0.15),
                int(e["y"]+offset_y*0.15)
            ),
            e["r"]
        )

    # Estrellas medias
    for e in estrellas_medias:
        e["y"] += e["vel"] * slowmo

        if e["y"] > ALTO:
            e["y"] = 0
            e["x"] = random.randint(0,ANCHO)

        pygame.draw.circle(
            pantalla,
            (190,190,220),
            (
                int(e["x"]+offset_x*0.35),
                int(e["y"]+offset_y*0.35)
            ),
            e["r"]
        )

    # Meteoritos decorativos de fondo
    if random.randint(1,260)==1 and len(meteoritos_fondo)<4:
        meteoritos_fondo.append([
            random.randint(-100,ANCHO),
            -40,
            random.uniform(2,5),
            random.uniform(3,6),
            random.randint(25,45)
        ])

    nuevos_meteoritos=[]
    for m in meteoritos_fondo:
        m[0]+=m[2]*slowmo
        m[1]+=m[3]*slowmo
        m[4]-=0.08

        pygame.draw.line(
            pantalla,
            (180,180,200),
            (
                int(m[0]+offset_x*0.25),
                int(m[1]+offset_y*0.25)
            ),
            (
                int(m[0]-25+offset_x*0.25),
                int(m[1]-25+offset_y*0.25)
            ),
            2
        )

        pygame.draw.circle(
            pantalla,
            (220,220,240),
            (
                int(m[0]+offset_x*0.25),
                int(m[1]+offset_y*0.25)
            ),
            3
        )

        if m[0] < ANCHO+100 and m[1] < ALTO+100 and m[4] > 0:
            nuevos_meteoritos.append(m)

    meteoritos_fondo=nuevos_meteoritos

    if nivel == 7:
        velo = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
        velo.fill((0,0,8,118))
        for i in range(9):
            cx = int((i*145 + ticks*0.25 + offset_x*0.1) % (ANCHO+220) - 110)
            cy = int(80 + math.sin(ticks*0.018+i)*180)
            pygame.draw.circle(velo,(5,32,62,72),(cx,cy),85+i*14,1)
            pygame.draw.circle(velo,(0,0,6,115),(cx+25,cy+15),42+i*3)
            pygame.draw.line(velo,(25,120,170,42),(cx,0),(cx-70,ALTO),1)
        for i in range(5):
            x = int((i*190 - ticks*0.12 + offset_x*0.08) % (ANCHO+160) - 80)
            pygame.draw.ellipse(velo,(0,0,0,150),(x,70+i*88,150,55))
            pygame.draw.ellipse(velo,(18,85,120,42),(x,70+i*88,150,55),1)
        pantalla.blit(velo,(0,0))

    elif nivel == 8:
        velo = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
        sol_x = ANCHO-120 + int(math.sin(ticks*0.01)*25)
        sol_y = 120
        for r,alpha in [(170,18),(110,34),(58,55)]:
            pygame.draw.circle(velo,(255,130,35,alpha),(sol_x,sol_y),r)
        for i in range(9):
            y = int((i*82 + ticks*0.55) % (ALTO+120) - 60)
            pygame.draw.line(velo,(255,190,65,28),(0,y),(ANCHO,y+35),2)
        pantalla.blit(velo,(0,0))

    elif nivel >= 9:
        velo = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
        for i in range(10):
            x = int((i*92 + math.sin(ticks*0.014+i)*24 + offset_x*0.08) % ANCHO)
            pygame.draw.line(velo,(70,255,190,32),(x,ALTO),(x+35,ALTO-170),2)
            pygame.draw.polygon(velo,(180,255,230,40),[(x+20,ALTO-175),(x+42,ALTO-135),(x,ALTO-135)])
        pantalla.blit(velo,(0,0))

    # Brillo ambiental superior segï¿½n nivel
    if 4 <= nivel <= 6:
        overlay = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
        pygame.draw.rect(overlay,(255,25,35,22),(0,0,ANCHO,ALTO))
        pantalla.blit(overlay,(0,0))

# =====================
# PUNTOS
# =====================
PUNTOS={
    "asteroide":500,
    "alien":1000,
    "drone":1300,
    "zigzag":900,
    "crucero":800,
    "phantom":1500,
    "orb":1700,
    "gravity":2000,

    # NUEVOS ENEMIGOS
    "sentinel":2200,
    "hunter":2500,
    "void_orb":2700,
    "laser_satellite":3000,

    # NIVEL 5 - THE VOID SWARM
    "parasite":3200,
    "hive":4500,
    "shadow_phantom":3800,
    "leech_drone":4200,

    # NIVEL 6 - QUANTUM RIFT
    "rift_splitter":5200,
    "quantum_shard":1800,
    "phase_reaper":6000,
    "chrono_mine":5500,

    # NIVEL 7 - THE SILENT ABYSS
    "abyss_wisp":6500,
    "null_seeker":7200,
    "void_lantern":7800,

    # NIVEL 8 - SOLAR GRAVEYARD
    "solar_mantis":8200,
    "flare_drone":7600,
    "helio_spire":9000,

    # NIVEL 9 - EDEN CORE
    "bloom_parasite":8400,
    "crystal_seraph":9200,
    "root_hydra":10500,
}

# =====================
# ESTADO
# =====================
nave_seleccionada = 1
planeta_seleccionado = "ares_prime"
planet_selector_index = 0

PLANET_IMAGE_FILES = {
    "ares_prime":"planet_ares_prime.png",
    "nebula_cryon":"planet_nebula_cryon.png",
    "vortice_umbra":"planet_vortice_umbra.png",
    "eden_9":"planet_eden_9.png",
    "scale_0":"planet_scale_0.png"
}

PLANET_DEFS = [
    {
        "id":"ares_prime",
        "name":"ARES PRIME",
        "name_en":"ARES PRIME",
        "desc":"Desierto rojo de tormentas termicas.",
        "desc_en":"Red desert world of thermal storms.",
        "unlock_score":0,
        "unlock_bosses":0,
        "palette":[(170,58,42),(220,105,48),(96,34,42),(255,170,80)]
    },
    {
        "id":"nebula_cryon",
        "name":"NEBULA CRYON",
        "name_en":"NEBULA CRYON",
        "desc":"Mundo helado con grietas cristalinas.",
        "desc_en":"Frozen world with crystalline cracks.",
        "unlock_score":150000,
        "unlock_bosses":1,
        "palette":[(80,150,210),(170,230,255),(35,75,130),(235,250,255)]
    },
    {
        "id":"vortice_umbra",
        "name":"VORTICE UMBRA",
        "name_en":"UMBRA VORTEX",
        "desc":"Gigante violeta de tormentas electricas.",
        "desc_en":"Violet giant of electric storms.",
        "unlock_score":500000,
        "unlock_bosses":3,
        "palette":[(92,45,160),(150,72,220),(35,18,70),(220,165,255)]
    },
    {
        "id":"eden_9",
        "name":"EDEN-9",
        "name_en":"EDEN-9",
        "desc":"Planeta alienigena de cristales vivos.",
        "desc_en":"Alien planet of living crystals.",
        "unlock_score":1000000,
        "unlock_bosses":5,
        "palette":[(40,150,105),(85,235,160),(15,70,55),(190,255,220)]
    },
    {
        "id":"scale_0",
        "name":"SCALE-0",
        "name_en":"SCALE-0",
        "desc":"???",
        "desc_en":"???",
        "unlock_score":99999999,
        "unlock_bosses":999,
        "secret":True,
        "palette":[(4,18,28),(20,135,150),(0,0,8),(140,255,240)]
    }
]

def indice_planeta(planeta_id):
    for i,p in enumerate(PLANET_DEFS):
        if p["id"] == planeta_id:
            return i
    return 0

def planeta_por_id(planeta_id):
    for p in PLANET_DEFS:
        if p["id"] == planeta_id:
            return p
    return PLANET_DEFS[0]

def planeta_desbloqueado(planeta_id):
    p = planeta_por_id(planeta_id)
    if p.get("secret",False):
        return stats.get("scale0_unlocked",0) > 0
    return (
        stats.get("best_score",0) >= p.get("unlock_score",0) or
        stats.get("bosses_defeated",0) >= p.get("unlock_bosses",0)
    )

def texto_planeta(p, clave):
    if clave == "name":
        return p.get("name_en",p["name"]) if idioma_actual == "EN" else p["name"]
    if clave == "desc":
        return p.get("desc_en",p["desc"]) if idioma_actual == "EN" else p["desc"]
    return ""

def datos_atmosfera_planeta(planeta_id=None):
    pid = planeta_id or planeta_seleccionado
    datos = {
        "ares_prime": {
            "temp":"+47 C",
            "estado":"POLVO TERMICO",
            "estado_en":"THERMAL DUST",
            "detalle":"VIENTOS ROJOS",
            "detalle_en":"RED WINDS"
        },
        "nebula_cryon": {
            "temp":"-82 C",
            "estado":"ESCARCHA ORBITAL",
            "estado_en":"ORBITAL FROST",
            "detalle":"AURORAS FRIAS",
            "detalle_en":"COLD AURORAS"
        },
        "vortice_umbra": {
            "temp":"?? C",
            "estado":"TORMENTA IONICA",
            "estado_en":"ION STORM",
            "detalle":"RAYOS VIOLETA",
            "detalle_en":"VIOLET STRIKES"
        },
        "eden_9": {
            "temp":"+19 C",
            "estado":"BIOBRILLO ACTIVO",
            "estado_en":"ACTIVE BIOGLOW",
            "detalle":"ESPORAS VIVAS",
            "detalle_en":"LIVING SPORES"
        },
        "scale_0": {
            "temp":"0.00 K",
            "estado":"SENAL DESCONOCIDA",
            "estado_en":"UNKNOWN SIGNAL",
            "detalle":"ECO IMPOSIBLE",
            "detalle_en":"IMPOSSIBLE ECHO"
        }
    }
    return datos.get(pid, datos["ares_prime"])

def color_tema_planeta():
    return planeta_por_id(planeta_seleccionado)["palette"][0]

def tintar_color_planeta(color_base, intensidad=0.28):
    p = planeta_por_id(planeta_seleccionado)
    color_planeta = p["palette"][0]
    return (
        int(color_base[0]*(1-intensidad)+color_planeta[0]*intensidad),
        int(color_base[1]*(1-intensidad)+color_planeta[1]*intensidad),
        int(color_base[2]*(1-intensidad)+color_planeta[2]*intensidad)
    )

def dibujar_marco_atmosferico(capa, color, intensidad=1.0):
    alpha = int(20 * intensidad)
    pygame.draw.rect(capa,(color[0],color[1],color[2],alpha),(0,0,ANCHO,ALTO),3)
    pygame.draw.line(capa,(color[0],color[1],color[2],alpha+12),(12,12),(92,12),2)
    pygame.draw.line(capa,(color[0],color[1],color[2],alpha+12),(12,12),(12,92),2)
    pygame.draw.line(capa,(color[0],color[1],color[2],alpha+12),(ANCHO-92,12),(ANCHO-12,12),2)
    pygame.draw.line(capa,(color[0],color[1],color[2],alpha+12),(ANCHO-12,12),(ANCHO-12,92),2)
    pygame.draw.line(capa,(color[0],color[1],color[2],alpha+8),(12,ALTO-12),(92,ALTO-12),2)
    pygame.draw.line(capa,(color[0],color[1],color[2],alpha+8),(12,ALTO-92),(12,ALTO-12),2)
    pygame.draw.line(capa,(color[0],color[1],color[2],alpha+8),(ANCHO-92,ALTO-12),(ANCHO-12,ALTO-12),2)
    pygame.draw.line(capa,(color[0],color[1],color[2],alpha+8),(ANCHO-12,ALTO-92),(ANCHO-12,ALTO-12),2)

def dibujar_detalles_planeta_beta(pid, ticks, offset_x, offset_y):
    capa = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    p = planeta_por_id(pid)
    tema = p["palette"][1]
    pulso = (math.sin(ticks*0.005) + 1) * 0.5
    dibujar_marco_atmosferico(capa, tema, 0.8 + pulso*0.35)

    if pid == "ares_prime":
        for i in range(7):
            x = int((i*155 - ticks*0.09 + offset_x*0.04) % (ANCHO+220) - 110)
            y = int(120 + i*64 + math.sin(ticks*0.004+i)*20)
            pygame.draw.ellipse(capa,(255,95,35,34),(x,y,250,34),1)
            pygame.draw.ellipse(capa,(255,165,70,22),(x+36,y+7,130,18),1)
        for i in range(11):
            x = int((i*77 + ticks*0.32) % ANCHO)
            y = int((i*53 + ticks*0.16) % ALTO)
            pygame.draw.polygon(capa,(255,215,120,58),[(x,y-3),(x+12,y),(x,y+3),(x-6,y)])
        for i in range(3):
            cx = int(ANCHO-95 + math.sin(ticks*0.002+i)*16)
            cy = int(92 + math.cos(ticks*0.003+i)*11)
            pygame.draw.circle(capa,(255,125,45,28),(cx,cy),112+i*18,1)

    elif pid == "nebula_cryon":
        for i in range(4):
            puntos = []
            base = 95 + i*42
            for x in range(-40, ANCHO+80, 55):
                y = int(base + math.sin(ticks*0.004 + x*0.02 + i)*28)
                puntos.append((x,y))
            pygame.draw.lines(capa,(135,240,255,32+i*5),False,puntos,4)
        for i in range(16):
            x = int((i*49 + math.sin(ticks*0.004+i)*30) % ANCHO)
            y = int((i*75 + ticks*0.11) % ALTO)
            r = 6 + (i % 4)
            pygame.draw.line(capa,(235,255,255,52),(x-r,y),(x+r,y),1)
            pygame.draw.line(capa,(235,255,255,52),(x,y-r),(x,y+r),1)
            pygame.draw.circle(capa,(150,230,255,22),(x,y),r+5,1)
        for i in range(8):
            x = int((i*118 - ticks*0.04) % ANCHO)
            pygame.draw.line(capa,(180,240,255,26),(x,ALTO),(x+22,ALTO-95),2)

    elif pid == "vortice_umbra":
        for i in range(5):
            cx = int(ANCHO//2 + math.sin(ticks*0.002+i)*310)
            cy = int(ALTO//2 + math.cos(ticks*0.003+i)*185)
            pygame.draw.circle(capa,(150,70,235,28),(cx,cy),55+i*12,1)
            pygame.draw.arc(capa,(220,170,255,35),(cx-70,cy-70,140,140),ticks*0.002+i,ticks*0.002+i+2.2,2)
        if ticks % 180 < 25:
            base_x = int((ticks*1.35) % ANCHO)
            puntos = [(base_x,0)]
            for j in range(1,7):
                puntos.append((base_x + int(math.sin(ticks*0.01+j)*65), int(j*ALTO/7)))
            pygame.draw.lines(capa,(230,185,255,88),False,puntos,2)
        for i in range(13):
            x = int((i*59 + ticks*0.18) % ANCHO)
            y = int((i*101 + math.sin(ticks*0.004+i)*80) % ALTO)
            pygame.draw.circle(capa,(195,120,255,42),(x,y),3)
            pygame.draw.circle(capa,(130,55,220,22),(x,y),13,1)

    elif pid == "eden_9":
        for i in range(10):
            x = int((i*86 + math.sin(ticks*0.002+i)*42) % ANCHO)
            base = ALTO - 4 - (i % 4) * 9
            alto = 46 + (i % 5) * 18
            pygame.draw.line(capa,(75,240,145,46),(x,base),(x+18,base-alto),2)
            pygame.draw.circle(capa,(185,255,215,46),(x+18,base-alto),5)
        for i in range(24):
            x = int((i*41 + math.sin(ticks*0.004+i)*70) % ANCHO)
            y = int((ALTO - ((ticks*0.09 + i*31) % (ALTO+60))) + 30)
            pygame.draw.circle(capa,(165,255,200,48),(x,y),2)
            if i % 5 == 0:
                pygame.draw.circle(capa,(90,255,160,24),(x,y),10,1)
        for i in range(4):
            y = int(100+i*95+math.sin(ticks*0.003+i)*17)
            pygame.draw.line(capa,(110,255,175,25),(0,y),(ANCHO,y+18),2)

    elif pid == "scale_0":
        for i in range(8):
            cx = int(ANCHO//2 + math.sin(ticks*0.002+i)*285)
            cy = int(ALTO//2 + math.cos(ticks*0.003+i)*210)
            pygame.draw.rect(capa,(120,255,240,28),(cx-20,cy-20,40,40),1)
            pygame.draw.line(capa,(120,255,240,22),(cx-32,cy),(cx+32,cy),1)
            pygame.draw.line(capa,(120,255,240,22),(cx,cy-32),(cx,cy+32),1)
        for i in range(10):
            y = int((i*63 + ticks*0.08) % ALTO)
            x = int((i*97 + math.sin(ticks*0.006+i)*90) % ANCHO)
            pygame.draw.rect(capa,(80,255,235,24),(x,y,46+(i%3)*22,2))
        for i in range(4):
            r = 82 + i*55 + int(math.sin(ticks*0.004+i)*12)
            pygame.draw.circle(capa,(70,255,235,20),(ANCHO//2,ALTO//2),r,1)

    pantalla.blit(capa,(0,0))

def limpiar_fondo_negro_planeta(img):
    """Convierte fondos casi negros en transparencia para assets de planeta."""
    img = img.convert_alpha()
    w,h = img.get_size()
    esquinas = [img.get_at((0,0)), img.get_at((w-1,0)), img.get_at((0,h-1)), img.get_at((w-1,h-1))]
    if sum(c.r + c.g + c.b for c in esquinas) / max(1,len(esquinas)) > 45:
        return img
    limpio = img.copy()
    for y in range(h):
        for x in range(w):
            c = limpio.get_at((x,y))
            if c.r < 24 and c.g < 24 and c.b < 30:
                limpio.set_at((x,y),(c.r,c.g,c.b,0))
            elif c.r < 42 and c.g < 42 and c.b < 50:
                limpio.set_at((x,y),(c.r,c.g,c.b,max(0,c.a-120)))
    return limpio

def dibujar_atmosfera_planeta(nivel, offset_x, offset_y):
    pid = planeta_seleccionado
    ticks = pygame.time.get_ticks()
    capa = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    pulso = (math.sin(ticks*0.006) + 1) * 0.5

    if pid == "ares_prime":
        pygame.draw.rect(capa,(115,30,8,34),(0,0,ANCHO,ALTO))
        pygame.draw.circle(capa,(255,95,25,30),(ANCHO-95,92),82)
        pygame.draw.circle(capa,(255,185,80,32),(ANCHO-95,92),38)
        for i in range(12):
            y = int((i*58 + ticks*0.16 + offset_y*0.06) % (ALTO+80) - 40)
            pygame.draw.line(capa,(255,128,45,44),(0,y),(ANCHO,y+15),2)
        for i in range(6):
            y = int(235 + i*62 + math.sin(ticks*0.004+i)*9)
            x = int(-90 + math.sin(ticks*0.003+i)*70)
            pygame.draw.ellipse(capa,(255,105,35,30),(x,y,ANCHO+180,28),1)
        for i in range(32):
            x = int((i*47 + ticks*0.28 + offset_x*0.1) % ANCHO)
            y = int((i*83 + ticks*0.09 + offset_y*0.08) % ALTO)
            radio = 1 + (i % 3 == 0)
            pygame.draw.circle(capa,(255,180,95,48),(x,y),radio)
        for i in range(8):
            x = int((i*137 - ticks*0.11) % (ANCHO+180) - 90)
            y = int(60 + i*68 + math.sin(ticks*0.005+i)*18)
            pygame.draw.line(capa,(190,70,25,42),(x,y),(x+80,y+10),3)
        for i in range(14):
            x = int((i*89 + ticks*0.44) % (ANCHO+50) - 25)
            y = int((i*41 + ticks*0.13) % ALTO)
            brillo = 45 + int(pulso*35)
            pygame.draw.circle(capa,(255,205,115,brillo),(x,y),2)
            pygame.draw.circle(capa,(255,95,30,28),(x,y),5,1)
        for i in range(4):
            cx = int((i*230 - ticks*0.05) % (ANCHO+160) - 80)
            cy = int(150 + i*100 + math.sin(ticks*0.004+i)*20)
            pygame.draw.arc(capa,(255,150,65,38),(cx,cy,180,42),0.15,2.9,2)
        for i in range(9):
            y = ALTO - 18 - i*13
            x = int(-80 + math.sin(ticks*0.002+i)*45)
            pygame.draw.ellipse(capa,(150,54,24,22),(x,y,ANCHO+160,28),1)
        for i in range(16):
            x = int((i*61 - ticks*0.52) % (ANCHO+120) - 60)
            y = int(95 + (i*37) % (ALTO-135))
            pygame.draw.line(capa,(255,205,120,55),(x,y),(x+18,y+4),2)

    elif pid == "nebula_cryon":
        pygame.draw.rect(capa,(28,95,155,30),(0,0,ANCHO,ALTO))
        for banda in range(3):
            puntos = []
            base_y = 78 + banda*46
            for i in range(0,ANCHO+70,70):
                y = int(base_y + math.sin(ticks*0.003 + i*0.018 + banda)*24)
                puntos.append((i,y))
            pygame.draw.lines(capa,(80,220,255,28+banda*8),False,puntos,3)
        for i in range(46):
            x = int((i*71 + math.sin(ticks*0.001+i)*35 + offset_x*0.12) % ANCHO)
            y = int((i*43 + ticks*0.07 + offset_y*0.12) % ALTO)
            pygame.draw.circle(capa,(215,248,255,58),(x,y),1 + (i%2))
        for i in range(7):
            x = int((i*145 - ticks*0.055 + offset_x*0.04) % (ANCHO+140) - 70)
            pygame.draw.line(capa,(130,230,255,38),(x,0),(x+95,ALTO),1)
        for i in range(4):
            y = int(115+i*118+math.sin(ticks*0.003+i)*18)
            pygame.draw.ellipse(capa,(185,245,255,28),(-60,y,ANCHO+120,26),1)
        for i in range(13):
            x = int((i*63 + ticks*0.035 + math.sin(i+ticks*0.002)*18) % ANCHO)
            y = int((i*86 + ticks*0.09) % ALTO)
            a = 42 + int(38*abs(math.sin(ticks*0.008+i)))
            pygame.draw.line(capa,(235,255,255,a),(x-5,y),(x+5,y),1)
            pygame.draw.line(capa,(235,255,255,a),(x,y-5),(x,y+5),1)
        for i in range(5):
            x = int((i*180 + ticks*0.018) % ANCHO)
            y = int(70 + i*92 + math.sin(ticks*0.003+i)*14)
            pygame.draw.polygon(capa,(170,235,255,34),[(x,y-15),(x+9,y+8),(x-8,y+10)])
        for i in range(10):
            x = int((i*88 - ticks*0.07) % (ANCHO+70) - 35)
            y = int(ALTO-35 - (i%4)*19 + math.sin(ticks*0.004+i)*8)
            pygame.draw.polygon(capa,(225,250,255,44),[(x,y-18),(x+12,y+8),(x-12,y+8)],1)
            pygame.draw.line(capa,(190,235,255,42),(x,y-18),(x,y+8),1)

    elif pid == "vortice_umbra":
        pygame.draw.rect(capa,(58,18,100,31),(0,0,ANCHO,ALTO))
        for i in range(5):
            x = int((i*190 - ticks*0.035) % (ANCHO+160) - 80)
            y = int(72 + i*87 + math.sin(ticks*0.004+i)*22)
            pygame.draw.ellipse(capa,(80,25,130,38),(x,y,250,52),1)
        for i in range(9):
            cx = int((i*143 + ticks*0.08) % (ANCHO+160) - 80)
            cy = int(95 + math.sin(ticks*0.002+i)*190)
            pygame.draw.circle(capa,(135,55,230,34),(cx,cy),70+i*9,1)
        if ticks % 260 < 18:
            x1 = int((ticks*1.7) % ANCHO)
            x2 = int((ANCHO - ticks*1.1) % ANCHO)
            pygame.draw.line(capa,(215,165,255,95),(x1,0),(x2,ALTO),2)
            pygame.draw.circle(capa,(180,90,255,42),(ANCHO//2,ALTO//2),210,2)
        for i in range(10):
            cx = int((i*79 + ticks*0.17 + math.sin(i)*45) % ANCHO)
            cy = int((i*57 + math.cos(ticks*0.004+i)*72 + ALTO//2) % ALTO)
            r = 4 + int(3*abs(math.sin(ticks*0.009+i)))
            pygame.draw.circle(capa,(190,110,255,38),(cx,cy),r,1)
            pygame.draw.line(capa,(230,190,255,55),(cx-r-3,cy),(cx+r+3,cy),1)
            pygame.draw.line(capa,(230,190,255,45),(cx,cy-r-3),(cx,cy+r+3),1)
        for i in range(3):
            x = int((i*260 + ticks*0.09) % ANCHO)
            y = int(110 + math.sin(ticks*0.006+i)*170)
            pygame.draw.arc(capa,(150,70,235,42),(x-80,y-40,160,80),0.2,5.6,2)
        for i in range(14):
            x = int((i*67 + ticks*0.1) % ANCHO)
            y = int((i*91 + math.sin(ticks*0.005+i)*45) % ALTO)
            tam = 5 + (i % 3)
            pygame.draw.polygon(capa,(205,150,255,44),[(x,y-tam),(x+tam,y),(x,y+tam),(x-tam,y)],1)
            if i % 4 == 0:
                pygame.draw.circle(capa,(120,55,220,28),(x,y),18,1)

    elif pid == "eden_9":
        pygame.draw.rect(capa,(8,70,42,29),(0,0,ANCHO,ALTO))
        for i in range(6):
            x = int((i*150 - ticks*0.02) % (ANCHO+90) - 45)
            y = int(90 + i*78 + math.sin(ticks*0.003+i)*18)
            pygame.draw.ellipse(capa,(40,160,95,34),(x,y,220,42),1)
        for i in range(12):
            x = int((i*91 + math.sin(ticks*0.002+i)*25 + offset_x*0.1) % ANCHO)
            pygame.draw.line(capa,(95,255,175,42),(x,ALTO),(x+32,ALTO-150),2)
            if i % 2 == 0:
                pygame.draw.polygon(capa,(180,255,225,40),[(x+28,ALTO-152),(x+44,ALTO-120),(x+10,ALTO-120)])
        for i in range(24):
            x = int((i*61 + ticks*0.05) % ANCHO)
            y = int((i*37 + math.sin(ticks*0.003+i)*26) % ALTO)
            pygame.draw.circle(capa,(100,255,180,43),(x,y),1)
        for i in range(18):
            x = int((i*73 + math.sin(ticks*0.003+i)*42) % ANCHO)
            y = int((ALTO - ((ticks*0.06 + i*59) % (ALTO+80))) + 40)
            a = 35 + int(45*abs(math.sin(ticks*0.007+i)))
            pygame.draw.circle(capa,(165,255,205,a),(x,y),2)
            if i % 3 == 0:
                pygame.draw.circle(capa,(80,255,160,24),(x,y),8,1)
        for i in range(5):
            x = int((i*160 + ticks*0.025) % ANCHO)
            y = int(120 + math.sin(ticks*0.004+i)*120)
            pygame.draw.line(capa,(210,255,230,50),(x-8,y),(x+8,y),1)
            pygame.draw.line(capa,(210,255,230,50),(x,y-8),(x,y+8),1)
        for i in range(8):
            x = int((i*112 + math.sin(ticks*0.002+i)*28) % ANCHO)
            base = ALTO - 18 - (i % 3) * 11
            pygame.draw.line(capa,(70,220,130,38),(x,base),(x+22,base-52),2)
            pygame.draw.circle(capa,(165,255,200,42),(x+22,base-52),5)
            pygame.draw.circle(capa,(90,255,160,24),(x+22,base-52),14,1)

    elif pid == "scale_0":
        pygame.draw.rect(capa,(0,8,12,38),(0,0,ANCHO,ALTO))
        for i in range(10):
            x = int((i*83 + math.sin(ticks*0.004+i)*35 + offset_x*0.2) % ANCHO)
            pygame.draw.line(capa,(80,255,235,24),(x,0),(x-45,ALTO),1)
        for i in range(5):
            r = 50 + i*42 + int(math.sin(ticks*0.004+i)*8)
            pygame.draw.circle(capa,(80,255,235,22),(ANCHO//2,ALTO//2),r,1)
        for i in range(12):
            x = int((i*97 + ticks*0.12) % ANCHO)
            y = int((i*71 + math.sin(ticks*0.005+i)*52 + ALTO//2) % ALTO)
            pygame.draw.rect(capa,(105,255,235,36),(x,y,10,2),1)
            pygame.draw.rect(capa,(105,255,235,24),(x+4,y-4,2,10),1)
        for i in range(7):
            y = int((i*89 + ticks*0.06) % ALTO)
            ancho_barra = 38 + (i % 4) * 18
            x = int((i*131 + math.sin(ticks*0.007+i)*70) % ANCHO)
            pygame.draw.rect(capa,(80,255,235,20),(x,y,ancho_barra,2))
            pygame.draw.rect(capa,(170,255,245,15),(x+12,y+5,ancho_barra//2,1))
        for i in range(6):
            cx = int(ANCHO//2 + math.sin(ticks*0.003+i)*230)
            cy = int(ALTO//2 + math.cos(ticks*0.004+i)*170)
            pygame.draw.arc(capa,(120,255,240,32),(cx-35,cy-35,70,70),0.6,4.4,1)

    pantalla.blit(capa,(0,0))

def crear_peligro_planeta(nivel):
    if estado.get("boss_intro",0) > 0 or estado.get("estado") != "JUGANDO":
        return
    pid = planeta_seleccionado
    if pid == "ares_prime":
        estado["planet_hazards"].append({
            "tipo":"heat_wave",
            "x":random.randint(-80,ANCHO-120),
            "y":random.randint(260,ALTO-70),
            "timer":150,
            "hit":False
        })
    elif pid == "nebula_cryon":
        estado["planet_hazards"].append({
            "tipo":"ice_shard",
            "x":random.randint(40,ANCHO-70),
            "y":-36,
            "vy":random.uniform(1.8,2.9),
            "rot":random.uniform(0,math.pi),
            "timer":360,
            "hit":False
        })
    elif pid == "vortice_umbra":
        estado["planet_hazards"].append({
            "tipo":"ion_strike",
            "x":random.randint(55,ANCHO-55),
            "timer":105,
            "hit":False
        })
    elif pid == "eden_9":
        estado["planet_hazards"].append({
            "tipo":"spore_bloom",
            "x":random.randint(50,ANCHO-50),
            "y":random.randint(265,ALTO-65),
            "r":12,
            "timer":210,
            "hit":False
        })
    elif pid == "scale_0":
        estado["planet_hazards"].append({
            "tipo":"zero_echo",
            "x":random.randint(70,ANCHO-70),
            "y":random.randint(270,ALTO-75),
            "timer":170,
            "hit":False
        })

def actualizar_planeta_gameplay(nivel):
    global flash, shake
    if estado.get("estado") != "JUGANDO" or hay_boss_activo():
        if estado.get("planet_hazards"):
            estado["planet_hazards"] = [h for h in estado["planet_hazards"] if h.get("timer",0) > 0]
        return

    pid = planeta_seleccionado
    if pid == "ares_prime":
        intervalo = 250
    elif pid == "nebula_cryon":
        intervalo = 210
    elif pid == "vortice_umbra":
        intervalo = 280
    elif pid == "eden_9":
        intervalo = 240
    else:
        intervalo = 300
    if nivel >= 6:
        intervalo = max(130, intervalo - 38)

    estado["planet_fx_timer"] = estado.get("planet_fx_timer",0) + 1
    if estado["planet_fx_timer"] >= intervalo:
        estado["planet_fx_timer"] = 0
        crear_peligro_planeta(nivel)

    nuevos = []
    nave_rect = rect_jugador_principal()
    nave2_rect = rect_jugador_2()
    for h in estado.get("planet_hazards",[]):
        h["timer"] -= 1
        tipo = h.get("tipo")
        rect = None
        peligro_activo = True

        if tipo == "heat_wave":
            rect = pygame.Rect(h["x"], h["y"], 230, 34)
            peligro_activo = h["timer"] < 105
        elif tipo == "ice_shard":
            h["y"] += h.get("vy",2.2) * slowmo
            h["rot"] += 0.04
            rect = pygame.Rect(h["x"]-12, h["y"]-18, 24, 38)
            if h["y"] > ALTO + 50:
                h["timer"] = 0
        elif tipo == "ion_strike":
            rect = pygame.Rect(h["x"]-22, 0, 44, ALTO)
            peligro_activo = h["timer"] < 42
        elif tipo == "spore_bloom":
            h["r"] = min(58, h.get("r",12) + 0.42)
            rect = pygame.Rect(h["x"]-h["r"], h["y"]-h["r"], h["r"]*2, h["r"]*2)
            peligro_activo = h["timer"] < 150
        elif tipo == "zero_echo":
            rect = pygame.Rect(h["x"]-28, h["y"]-28, 56, 56)
            peligro_activo = h["timer"] < 120

        toca = rect is not None and (rect.colliderect(nave_rect) or (nave2_rect is not None and rect.colliderect(nave2_rect)))
        if toca and peligro_activo and not h.get("hit",False) and estado.get("inv",0) <= 0:
            h["hit"] = True
            if tipo == "ice_shard":
                estado["slow_effect"] = max(estado.get("slow_effect",0), 95)
                aplicar_dano_jugador(0.35)
            elif tipo == "spore_bloom":
                estado["slow_effect"] = max(estado.get("slow_effect",0), 60)
                aplicar_dano_jugador(0.25)
            elif tipo == "zero_echo":
                estado["score"] += 3500
                ganar_monedas(350)
                estado["ultimate_message"] = 80
                estado["ultimate_message_text"] = "ECO SCALE-0 +" + str(3500) if idioma_actual != "EN" else "SCALE-0 ECHO +" + str(3500)
            else:
                aplicar_dano_jugador(0.5)
            estado["inv"] = max(estado.get("inv",0), 44)
            flash = max(flash,9)
            shake = max(shake,10)

        if h.get("timer",0) > 0:
            nuevos.append(h)
    estado["planet_hazards"] = nuevos[-12:]

def dibujar_planeta_gameplay_v69(offset_x, offset_y):
    ticks = pygame.time.get_ticks()
    pid = planeta_seleccionado
    pulso = (math.sin(ticks*0.006) + 1) * 0.5
    for h in estado.get("planet_hazards",[]):
        tipo = h.get("tipo")
        if tipo == "heat_wave":
            alpha = 42 if h["timer"] > 105 else 92
            x = int(h["x"]+offset_x)
            y = int(h["y"]+offset_y)
            img = asset_xfondo(ASSET_HAZARDS["heat_wave"], (112,112))
            crear_glow(pantalla,x+115,y+17,58,(255,140,55),50 if h["timer"] <= 105 else 25)
            if not blit_asset_centrado(pantalla,img,x+115,y+17,(112,112),alpha=max(alpha,120 if h["timer"] <= 105 else 70)):
                pygame.draw.ellipse(pantalla,(255,150,55,alpha),(x,y,230,34),2)
                for i in range(5):
                    pygame.draw.line(pantalla,(255,205,110,alpha),(x+18+i*38,y+8),(x+48+i*38,y+24),2)
        elif tipo == "ice_shard":
            x = int(h["x"]+offset_x)
            y = int(h["y"]+offset_y)
            img = asset_xfondo(ASSET_HAZARDS["ice_shard"], (72,92))
            crear_glow(pantalla,x,y,38,(170,235,255),42)
            if not blit_asset_centrado(pantalla,img,x,y,(72,92),rotacion=math.degrees(h.get("rot",0))*0.15):
                pts = [(x,y-22),(x+14,y+8),(x+3,y+24),(x-13,y+7)]
                pygame.draw.polygon(pantalla,(215,250,255),pts)
                pygame.draw.polygon(pantalla,(115,210,255),pts,2)
        elif tipo == "ion_strike":
            x = int(h["x"]+offset_x)
            aviso = h["timer"] > 42
            color = (190,100,255) if aviso else (235,210,255)
            ancho = 2 if aviso else 9
            img = asset_xfondo(ASSET_HAZARDS["ion_strike"], (92,170))
            if aviso:
                pygame.draw.line(pantalla,color,(x,0),(x+int(math.sin(ticks*0.02)*22),ALTO),ancho)
            else:
                for yy in range(70, ALTO, 135):
                    blit_asset_centrado(pantalla,img,x+int(math.sin(ticks*0.02+yy)*18),yy,(92,170),alpha=210)
            if not aviso:
                crear_glow(pantalla,x,ALTO//2,90,(180,90,255),65)
        elif tipo == "spore_bloom":
            x = int(h["x"]+offset_x)
            y = int(h["y"]+offset_y)
            r = int(h.get("r",20))
            img = asset_xfondo(ASSET_HAZARDS["spore_bloom"], (int(r*2.0), int(r*2.0)))
            crear_glow(pantalla,x,y,r+22,(105,255,170),42)
            if not blit_asset_centrado(pantalla,img,x,y,(int(r*2.0), int(r*2.0))):
                pygame.draw.circle(pantalla,(95,245,160),(x,y),r,2)
                for i in range(7):
                    ang = ticks*0.004+i*math.pi*2/7
                    pygame.draw.circle(pantalla,(190,255,220),(int(x+math.cos(ang)*r),int(y+math.sin(ang)*r)),3)
        elif tipo == "zero_echo":
            x = int(h["x"]+offset_x)
            y = int(h["y"]+offset_y)
            img = asset_xfondo(ASSET_HAZARDS["zero_echo"], (78,78))
            crear_glow(pantalla,x,y,42,(120,255,240),55)
            if not blit_asset_centrado(pantalla,img,x,y,(78,78),rotacion=ticks*0.025):
                pygame.draw.rect(pantalla,(120,255,240),(x-18,y-18,36,36),1)
                pygame.draw.circle(pantalla,(220,255,250),(x,y),12,1)
                pygame.draw.line(pantalla,(120,255,240),(x-28,y),(x+28,y),1)
                pygame.draw.line(pantalla,(120,255,240),(x,y-28),(x,y+28),1)
    dibujar_detalles_planeta_beta(pid, ticks, offset_x, offset_y)
    info = datos_atmosfera_planeta(pid)
    p = planeta_por_id(pid)
    nombre = texto_planeta(p,"name")
    estado_txt = info["estado_en"] if idioma_actual == "EN" else info["estado"]
    detalle_txt = info["detalle_en"] if idioma_actual == "EN" else info["detalle"]
    panel = pygame.Surface((228,82), pygame.SRCALPHA)
    tema = p["palette"][1]
    panel.fill((5,12,22,128))
    pygame.draw.rect(panel,(tema[0],tema[1],tema[2],115),(0,0,228,82),1,border_radius=8)
    pygame.draw.rect(panel,(tema[0],tema[1],tema[2],35),(4,4,220,74),border_radius=8)
    pygame.draw.circle(panel,(tema[0],tema[1],tema[2],65 + int(pulso*60)),(18,25),9)
    pygame.draw.circle(panel,(tema[0],tema[1],tema[2],32 + int(pulso*34)),(18,25),18,1)
    for i in range(5):
        x = 38 + i*34
        alto = 5 + int((math.sin(pygame.time.get_ticks()*0.006+i)+1)*7)
        pygame.draw.rect(panel,(tema[0],tema[1],tema[2],55),(x,70-alto,20,alto),border_radius=2)
    linea1 = fuente_peq.render(nombre[:18], True, (235,245,255))
    linea2 = pygame.font.SysFont(None,19).render(info["temp"] + "  " + estado_txt[:17], True, (190,230,240))
    linea3 = pygame.font.SysFont(None,18).render(detalle_txt[:22], True, (160,205,220))
    panel.blit(linea1,(34,7))
    panel.blit(linea2,(34,29))
    panel.blit(linea3,(34,49))
    pantalla.blit(panel,(ANCHO-242,14))
    dibujar_firma_planeta_v65(pid, ticks, offset_x, offset_y)

def dibujar_firma_planeta_v65(pid, ticks, offset_x, offset_y):
    capa = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
    p = planeta_por_id(pid)
    pal = p["palette"]
    pulso = 0.5 + 0.5 * math.sin(ticks*0.005)

    if pid == "ares_prime":
        for i in range(10):
            y = int((i*64 + ticks*0.21) % (ALTO+90) - 45)
            pygame.draw.line(capa,(255,130,55,38),(0,y),(ANCHO,y+22),2)
            pygame.draw.line(capa,(255,210,120,20),(0,y+8),(ANCHO,y+30),1)
        for i in range(8):
            x = int((i*121 - ticks*0.36) % (ANCHO+140) - 70)
            y = int(80 + (i*53) % 440 + math.sin(ticks*0.006+i)*18)
            pygame.draw.polygon(capa,(255,195,95,58),[(x,y),(x+28,y+5),(x+6,y+12)])
        term = "+47 C" if idioma_actual != "EN" else "+47 C"
        estado_corto = "VIENTO TERMICO" if idioma_actual != "EN" else "THERMAL WIND"
        color_ui = (255,155,70)

    elif pid == "nebula_cryon":
        for i in range(18):
            x = int((i*67 + math.sin(ticks*0.004+i)*38) % ANCHO)
            y = int((i*39 + ticks*0.12) % ALTO)
            pygame.draw.line(capa,(220,250,255,62),(x-6,y),(x+6,y),1)
            pygame.draw.line(capa,(220,250,255,62),(x,y-6),(x,y+6),1)
            pygame.draw.circle(capa,(140,230,255,24),(x,y),12,1)
        for i in range(5):
            x = int((i*174 - ticks*0.045) % (ANCHO+120) - 60)
            pygame.draw.polygon(capa,(190,245,255,34),[(x,ALTO),(x+28,ALTO-130),(x+56,ALTO)],1)
        term = "-82 C"
        estado_corto = "ESCARCHA ORBITAL" if idioma_actual != "EN" else "ORBITAL FROST"
        color_ui = (170,235,255)

    elif pid == "vortice_umbra":
        for i in range(6):
            cx = int(ANCHO//2 + math.sin(ticks*0.002+i)*320)
            cy = int(ALTO//2 + math.cos(ticks*0.003+i)*210)
            pygame.draw.arc(capa,(185,95,255,45),(cx-80,cy-45,160,90),ticks*0.003+i,ticks*0.003+i+3.7,2)
            pygame.draw.circle(capa,(120,45,210,20),(cx,cy),70+i*9,1)
        if ticks % 210 < 16:
            base_x = int((ticks*1.4) % ANCHO)
            puntos = [(base_x,0)]
            for j in range(1,8):
                puntos.append((base_x + int(math.sin(ticks*0.02+j)*75), int(j*ALTO/8)))
            pygame.draw.lines(capa,(230,190,255,105),False,puntos,2)
        term = "?? C"
        estado_corto = "TORMENTA IONICA" if idioma_actual != "EN" else "ION STORM"
        color_ui = (190,105,255)

    elif pid == "eden_9":
        for i in range(28):
            x = int((i*43 + math.sin(ticks*0.003+i)*58) % ANCHO)
            y = int((ALTO - ((ticks*0.09+i*31) % (ALTO+70))) + 35)
            pygame.draw.circle(capa,(150,255,205,50),(x,y),2)
            if i % 4 == 0:
                pygame.draw.circle(capa,(70,255,160,25),(x,y),11,1)
        for i in range(12):
            x = int((i*94 + math.sin(ticks*0.002+i)*28) % ANCHO)
            base = ALTO - 10 - (i % 4) * 14
            pygame.draw.line(capa,(80,235,145,48),(x,base),(x+24,base-64),2)
            pygame.draw.circle(capa,(180,255,220,46),(x+24,base-64),5)
        term = "+19 C"
        estado_corto = "BIOBRILLO" if idioma_actual != "EN" else "BIOGLOW"
        color_ui = (105,255,175)

    else:
        for i in range(12):
            x = int((i*83 + ticks*0.18 + math.sin(i)*40) % ANCHO)
            y = int((i*57 + math.sin(ticks*0.006+i)*85 + ALTO//2) % ALTO)
            pygame.draw.rect(capa,(105,255,240,34),(x-12,y-12,24,24),1)
            pygame.draw.line(capa,(105,255,240,24),(x-24,y),(x+24,y),1)
            pygame.draw.line(capa,(105,255,240,24),(x,y-24),(x,y+24),1)
        for i in range(5):
            y = int((i*96 + ticks*0.11) % ALTO)
            pygame.draw.rect(capa,(80,255,235,24),(0,y,ANCHO,2))
        term = "0.00 K"
        estado_corto = "SENAL ROTA" if idioma_actual != "EN" else "BROKEN SIGNAL"
        color_ui = (120,255,235)

    pygame.draw.rect(capa,(color_ui[0],color_ui[1],color_ui[2],18 + int(pulso*10)),(0,0,ANCHO,ALTO),2)
    etiqueta = pygame.Surface((210,42), pygame.SRCALPHA)
    etiqueta.fill((2,8,18,118))
    pygame.draw.rect(etiqueta,(color_ui[0],color_ui[1],color_ui[2],95),(0,0,210,42),1,border_radius=7)
    texto1 = pygame.font.SysFont(None,18).render(estado_corto[:20], True, (230,245,255))
    texto2 = pygame.font.SysFont(None,18).render(term, True, color_ui)
    etiqueta.blit(texto1,(12,7))
    etiqueta.blit(texto2,(12,24))
    pantalla.blit(capa,(0,0))
    pantalla.blit(etiqueta,(12,96))

def crear_planeta_selector_surface(p, tam=156, bloqueado=False):
    archivo = PLANET_IMAGE_FILES.get(p["id"],"")
    ruta_planeta = ruta_recurso(archivo)
    if archivo and os.path.exists(ruta_planeta):
        try:
            img = pygame.image.load(ruta_planeta).convert_alpha()
            img = pygame.transform.smoothscale(img,(tam,tam))
            if bloqueado:
                capa = pygame.Surface((tam,tam), pygame.SRCALPHA)
                capa.fill((0,0,0,145))
                img.blit(capa,(0,0))
            return img
        except:
            pass

    surf = pygame.Surface((tam,tam), pygame.SRCALPHA)
    pal = p["palette"]
    cx = cy = tam//2
    radio = tam//2 - 8
    for y in range(-radio, radio+1, 4):
        ancho = int(math.sqrt(max(0, radio*radio-y*y)))
        for x in range(-ancho, ancho+1, 4):
            ruido = int(18*math.sin((x*0.09)+(y*0.05)+len(p["id"])))
            base = pal[0] if (x+y+ruido) % 17 < 9 else pal[1]
            if p["id"] == "vortice_umbra":
                base = pal[(abs(y)//18 + abs(x)//55) % 3]
            elif p["id"] == "nebula_cryon" and (x-y+ruido) % 31 < 4:
                base = pal[3]
            elif p["id"] == "eden_9" and (x*y+ruido) % 43 < 5:
                base = pal[3]
            elif p["id"] == "scale_0":
                base = pal[2] if (x*x+y*y) < radio*radio*0.55 else pal[1]
            shade = 1.0 - max(0,(x+y)/(radio*2))*0.35
            col = (int(base[0]*shade), int(base[1]*shade), int(base[2]*shade), 235)
            pygame.draw.rect(surf, col, (cx+x, cy+y, 5, 5))
    pygame.draw.circle(surf, (255,255,255,28), (cx-radio//3,cy-radio//3), max(8,radio//5))
    pygame.draw.circle(surf, pal[3], (cx,cy), radio, 2)
    crear_glow(surf, cx, cy, radio+6, pal[1], 30)
    if bloqueado:
        lock = pygame.Surface((tam,tam), pygame.SRCALPHA)
        lock.fill((0,0,0,150))
        surf.blit(lock,(0,0))
        pygame.draw.circle(surf,(110,130,150),(cx,cy),radio,2)
        pygame.draw.rect(surf,(190,210,220),(cx-16,cy-2,32,26),2,border_radius=4)
        pygame.draw.arc(surf,(190,210,220),(cx-18,cy-25,36,38),math.pi,math.pi*2,3)
    return surf

def reiniciar():
    return {
        "estado":"JUGANDO",
        "nave_x":ANCHO//2 - (80 if coop_activo() else 0),
        "nave_y":ALTO-105,
        "nave_tipo":nave_seleccionada,

        # coop local
        "coop":coop_activo(),
        "nave2_x":ANCHO//2 + 80,
        "nave2_y":ALTO-105,
        "nave2_tipo":2 if 2 in owned_ships else nave_seleccionada,
        "cooldown2":0,
        "inv2":0,
        "dash2_cd":0,
        "dash2_timer":0,
        "dash2_dir":1,
        "player_laser2_cd":0,
        "player_laser2":0,
        "pulse2_cd":0,
        "pulse2_timer":0,
        "pulse2_radius":0,
        "balas":[],
        "balas_enemigas":[],
        "enemigos":[],
        "powerups":[],
        "score":0,
        "planet_mission_kills":0,
        "planet_mission_claimed":False,
        "planet_hazards":[],
        "planet_fx_timer":0,
        "planet_heat":0,
        "micro_anomalias":[],
        "cooldown":0,
        "vidas":hp_maximo_jugador(),
        "hp":hp_maximo_jugador(),
        "max_hp":hp_maximo_jugador(),
        "inv":0,
        "rapid":0,
        "double":0,
        "shield":0,

        "combo":0,
        "combo_timer":0,

        "boss":None,
        "boss_spawned":False,

        "boss_final":None,
        "boss_final_spawned":False,

        # laser vertical del boss final actual
        "laser":0,
        "laser_x":0,

        # habilidades especiales del jugador
        "dash_cd":0,
        "dash_timer":0,
        "dash_dir":1,

        "player_laser_cd":0,
        "player_laser":0,

        "pulse_cd":0,
        "pulse_timer":0,
        "pulse_radius":0,

        # cinematicas de bosses
        "boss_intro":0,
        "boss_intro_tipo":"",
        "boss_intro_nombre":"",
        "cockpit_scan":None,
        "cockpit_bonus":None,
        "cockpit_bonus_timer":0,
        "cockpit_damage_boost":0,

        # ultimate attacks - solo durante boss fights
        "ultimate_overdrive_cd":0,
        "ultimate_overdrive":0,
        "ultimate_overdrive_tick":0,

        "ultimate_blackhole_cd":0,
        "ultimate_blackhole":0,
        "ultimate_blackhole_x":0,
        "ultimate_blackhole_y":0,

        "ultimate_orbital_cd":0,
        "ultimate_orbital":0,
        "ultimate_orbital_x":0,

        "ultimate_message":0,
        "ultimate_message_text":"",
        "boss_loot_pending":False,
        "boss_loot_tipo":"",
        "boss_loot_choices":[],
        "boss_loot_anim":0,

        # nuevo boss laser
        "boss_laser":None,
        "boss_laser_spawned":False,

        # nivel 5 - boss overmind
        "boss_overmind":None,
        "boss_overmind_spawned":False,

        # nivel 6 - Quantum Rift
        "boss_rift":None,
        "boss_rift_spawned":False,
        "rift_attacks":[],
        "quantum_fields":[],

        # niveles 7-9 - expansion cosmica
        "boss_hollow":None,
        "boss_hollow_spawned":False,
        "abyss_zones":[],
        "silence_rings":[],

        "boss_sun_eater":None,
        "boss_sun_eater_spawned":False,
        "solar_waves":[],
        "solar_plates":[],

        "boss_eden":None,
        "boss_eden_spawned":False,
        "eden_roots":[],
        "crystal_rain":[],
        "life_pulses":[],

        # evento secreto beta nivel -0
        "wormhole_event":None,
        "wormhole_cd":random.randint(4200,7200),
        "wormhole_forced":False,
        "scale0_timer":0,
        "scale0_seed":0,
        "scale0_reward":0,
        "scale0_reward_given":False,
        "scale0_orb_collected":False,
        "scale0_player_x":0.0,
        "scale0_player_z":0.0,
        "scale0_walk_hint":0,
        "scale0_lore_page":0,

        "void_zones":[],
        "tentacles":[],
        "corruption_timer":0,
        "slow_effect":0,
        "revive_used":False,

        # lasers del nuevo boss
        "laser_horizontal":0,
        "laser_y":0,

        "laser_cross":0,
        "laser_cross_x":0,
        "laser_cross_y":0,

        "laser_sweep":0,
        "laser_sweep_x":0,
        "laser_sweep_y":0,
        "laser_sweep_dir":1,
        "laser_sweep_tipo":"vertical"
    }

cargar_progreso()
if AUDIO_OK:
    pygame.mixer.music.set_volume(musica_volumen)

estado = reiniciar()
estado["estado"] = "MENU"

nivel_anterior_visual = 1
level_banner = 0
level_banner_text = ""

# =====================
# PANEL ADMIN DE MONEDAS
# =====================
ADMIN_USER = "dculebrasscaletale"

admin_panel = False
admin_stage = "user"
admin_input = ""
admin_user_input = ""
admin_message = ""
admin_message_timer = 0

# Opciones especiales preparadas desde el panel admin para la siguiente partida.
admin_next_mode = "normal"
admin_next_score = 0
admin_next_message = ""

ADMIN_RUN_OPTIONS = {
    "A":("normal",0,"NEXT RUN: NORMAL"),
    "B":("level4",70000,"NEXT RUN: LEVEL 4 ENEMIES"),
    "C":("boss1",30000,"NEXT RUN: BOSS 1"),
    "D":("boss2",60000,"NEXT RUN: BOSS 2"),
    "E":("boss_laser",120000,"NEXT RUN: LASER BOSS"),
    "F":("all_new_enemies",70000,"NEXT RUN: NEW ENEMY TEST"),
    "G":("level5",220000,"NEXT RUN: LEVEL 5 VOID SWARM"),
    "H":("overmind",430000,"NEXT RUN: OVERMIND"),
    "I":("level6",520000,"NEXT RUN: LEVEL 6 QUANTUM RIFT"),
    "J":("rift_boss",720000,"NEXT RUN: RIFT MONARCH"),
    "K":("level7",760000,"NEXT RUN: LEVEL 7 SILENT ABYSS"),
    "L":("hollow_boss",1040000,"NEXT RUN: HOLLOW SAINT"),
    "M":("level8",1050000,"NEXT RUN: LEVEL 8 SOLAR GRAVEYARD"),
    "N":("sun_boss",1380000,"NEXT RUN: SUN EATER"),
    "O":("level9",1400000,"NEXT RUN: LEVEL 9 EDEN CORE"),
    "P":("eden_boss",1750000,"NEXT RUN: EDEN PRIME"),
    "Q":("scale0_event",300000,"NEXT RUN: FORCE SCALE-0 EVENT"),
    "R":("scale0_direct",0,"NEXT RUN: DIRECT SCALE-0 LABYRINTH")
}

def seleccionar_admin_run(codigo):
    global admin_next_mode, admin_next_score, admin_next_message, admin_message, admin_message_timer
    opcion = ADMIN_RUN_OPTIONS.get(codigo.strip().upper())
    if not opcion:
        admin_message = "INVALID ADMIN LETTER"
        admin_message_timer = 120
        return
    admin_next_mode, admin_next_score, admin_next_message = opcion
    admin_message = admin_next_message
    admin_message_timer = 120

game_over_score = 0
game_over_coins = 0

# =====================
# LOOP PRINCIPAL
# =====================
while True:

    # HITSTOP
    if hitstop > 0:
        hitstop -= 1
        presentar_frame()
        continue

    actualizar_musica_dinamica()

    # SLOWMO
    if slowmo_timer > 0:
        slowmo_timer = max(0, slowmo_timer - 2)
        slowmo = max(slowmo, 0.55)
    else:
        slowmo = 1

    # PLAYLIST AUTOMATICA
    if AUDIO_OK and not scale0_music_active and not pygame.mixer.music.get_busy():
        reproducir_siguiente()

    # =====================
    # EVENTOS
    # =====================
    for e in pygame.event.get():

        if e.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if e.type == pygame.VIDEORESIZE and not fullscreen:
            ventana = pygame.display.set_mode(e.size, pygame.RESIZABLE)
            actualizar_escalado()

        if e.type == pygame.KEYDOWN:

            if e.key == pygame.K_F11:
                alternar_pantalla_completa()
                continue

            if estado["estado"] == "MENU":
                if e.key in [pygame.K_1, pygame.K_KP1]:
                    seleccionar_build_por_indice(0)
                    continue
                if e.key in [pygame.K_2, pygame.K_KP2]:
                    seleccionar_build_por_indice(1)
                    continue
                if e.key in [pygame.K_3, pygame.K_KP3]:
                    seleccionar_build_por_indice(2)
                    continue
                if e.key in [pygame.K_4, pygame.K_KP4]:
                    seleccionar_build_por_indice(3)
                    continue

            if estado["estado"] == "JUGANDO" and estado.get("boss_intro",0) > 0 and estado.get("cockpit_scan",{}).get("active",False):
                if e.key in [pygame.K_1, pygame.K_KP1]:
                    seleccionar_sistema_cabina("weapons")
                    continue
                if e.key in [pygame.K_2, pygame.K_KP2]:
                    seleccionar_sistema_cabina("shield")
                    continue
                if e.key in [pygame.K_3, pygame.K_KP3]:
                    seleccionar_sistema_cabina("reactor")
                    continue
                if e.key == pygame.K_RETURN:
                    confirmar_sistema_cabina()
                    continue

            if estado["estado"] == "GAME_OVER":
                if e.key in [pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE]:
                    estado["estado"] = "MENU"
                continue

            if estado["estado"] == "BOSS_LOOT":
                opciones = estado.get("boss_loot_choices",[])
                if e.key in [pygame.K_1, pygame.K_KP1] and len(opciones) >= 1:
                    aplicar_loot_boss(opciones[0])
                elif e.key in [pygame.K_2, pygame.K_KP2] and len(opciones) >= 2:
                    aplicar_loot_boss(opciones[1])
                elif e.key in [pygame.K_3, pygame.K_KP3] and len(opciones) >= 3:
                    aplicar_loot_boss(opciones[2])
                continue

            if estado["estado"] == "PAUSA":
                if e.key in [pygame.K_p, pygame.K_ESCAPE, pygame.K_RETURN]:
                    estado["estado"] = "JUGANDO"
                elif e.key in [pygame.K_MINUS, pygame.K_KP_MINUS]:
                    musica_volumen = max(0.0, round(musica_volumen - 0.1, 2))
                    if AUDIO_OK:
                        pygame.mixer.music.set_volume(musica_volumen)
                    guardar_progreso()
                elif e.key in [pygame.K_EQUALS, pygame.K_KP_PLUS]:
                    musica_volumen = min(1.0, round(musica_volumen + 0.1, 2))
                    if AUDIO_OK:
                        pygame.mixer.music.set_volume(musica_volumen)
                    guardar_progreso()
                elif e.key == pygame.K_q:
                    finalizar_partida_y_guardar(estado.get("score",0))
                    estado = reiniciar()
                    estado["estado"] = "MENU"
                continue

            if estado["estado"] == "JUGANDO" and e.key == pygame.K_p:
                estado["estado"] = "PAUSA"
                continue

            if estado["estado"] == "PLANETAS":
                if e.key in [pygame.K_ESCAPE, pygame.K_BACKSPACE]:
                    estado["estado"] = "MENU"
                    continue
                if e.key in [pygame.K_LEFT, pygame.K_a]:
                    planet_selector_index = (planet_selector_index - 1) % len(PLANET_DEFS)
                    continue
                if e.key in [pygame.K_RIGHT, pygame.K_d]:
                    planet_selector_index = (planet_selector_index + 1) % len(PLANET_DEFS)
                    continue
                if e.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    p = PLANET_DEFS[planet_selector_index]
                    if planeta_desbloqueado(p["id"]):
                        if p.get("secret",False):
                            iniciar_scale0_directo()
                        else:
                            planeta_seleccionado = p["id"]
                            guardar_progreso()
                    continue

            if estado["estado"] in ["SCALE0_MAZE","SCALE0_DIRECT_INTRO"] and e.key == pygame.K_ESCAPE:
                restaurar_musica_normal()
                estado["estado"] = "MENU"
                continue

            if estado["estado"] == "SCALE0_REWARD" and e.key in [pygame.K_RETURN, pygame.K_SPACE]:
                finalizar_scale0_evento()
                continue

            if estado["estado"] == "SCALE0_LORE" and e.key in [pygame.K_RETURN, pygame.K_SPACE]:
                avanzar_lore_scale0()
                continue

            # =====================
            # PANEL ADMIN OCULTO
            # =====================
            if e.key == pygame.K_t and (pygame.key.get_mods() & pygame.KMOD_CTRL) and (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                admin_panel = True
                admin_stage = "user"
                admin_input = ""
                admin_user_input = ""
                admin_message = ""
                admin_message_timer = 0
                continue

            if admin_panel:

                if e.key == pygame.K_ESCAPE:
                    admin_panel = False
                    admin_stage = "user"
                    admin_input = ""
                    admin_user_input = ""
                    admin_message = ""
                    continue

                elif e.key == pygame.K_BACKSPACE:
                    if admin_stage == "admin" and admin_input == "":
                        admin_stage = "menu"
                        admin_message = ""
                    else:
                        admin_input = admin_input[:-1]
                    continue

                elif e.key == pygame.K_RETURN:

                    if admin_stage == "user":

                        if admin_input.strip() == ADMIN_USER:
                            admin_user_input = admin_input.strip()
                            admin_stage = "menu"
                            admin_input = ""
                            admin_message = "ACCESS GRANTED"
                            admin_message_timer = 90
                        else:
                            admin_input = ""
                            admin_user_input = ""
                            admin_message = "ACCESS DENIED"
                            admin_message_timer = 120

                    elif admin_stage == "coins":

                        try:
                            cantidad_admin = int(admin_input.strip())

                            if cantidad_admin != 0:
                                monedas = max(0, monedas + cantidad_admin)
                                guardar_progreso()

                                if cantidad_admin > 0:
                                    admin_message = f"+{cantidad_admin} COINS"
                                else:
                                    admin_message = f"{cantidad_admin} COINS"

                                admin_message_timer = 150
                                admin_stage = "menu"
                                admin_input = ""
                            else:
                                admin_input = ""
                                admin_message = "INVALID AMOUNT"
                                admin_message_timer = 120

                        except:
                            admin_input = ""
                            admin_message = "INVALID NUMBER"
                            admin_message_timer = 120

                    elif admin_stage == "admin":

                        seleccionar_admin_run(admin_input.strip())
                        admin_input = ""

                    continue

                elif e.key == pygame.K_a and admin_stage == "menu":
                    admin_stage = "coins"
                    admin_input = ""
                    admin_message = ""
                    continue

                elif e.key == pygame.K_b and admin_stage == "menu":
                    admin_stage = "admin"
                    admin_input = ""
                    admin_message = ""
                    continue

                elif admin_stage == "admin":

                    if e.unicode and e.unicode.upper() in ADMIN_RUN_OPTIONS and len(admin_input) < 1:
                        admin_input += e.unicode.upper()

                    continue

                else:
                    if e.unicode and len(admin_input) < 28:
                        admin_input += e.unicode
                    continue

            # Lobby del host: la partida no empieza hasta que el cliente se conecte.
            if estado["estado"] == "ONLINE_HOST_LOBBY":

                if e.key == pygame.K_RETURN:
                    if net_connected:
                        estado = reiniciar()
                        registrar_partida_si_necesario()

                        if habilidad_comprada("auto_shield"):
                            estado["shield"] = 300

                        aplicar_admin_next_run()

                elif e.key == pygame.K_ESCAPE:
                    cerrar_red_lan()
                    estado["estado"] = "MENU"

                continue

            # Pantalla para introducir IP del host LAN.
            if estado["estado"] == "ONLINE_JOIN":

                if e.key == pygame.K_RETURN:
                    if len(net_join_ip.strip()) > 0:
                        iniciar_cliente_lan(net_join_ip.strip())
                        estado["estado"] = "ONLINE_CLIENT"

                elif e.key == pygame.K_BACKSPACE:
                    net_join_ip = net_join_ip[:-1]

                elif e.key == pygame.K_ESCAPE:
                    estado["estado"] = "MENU"

                else:
                    if e.unicode and len(net_join_ip) < 32:
                        if e.unicode.isdigit() or e.unicode == ".":
                            net_join_ip += e.unicode

                continue

            # Si estamos reasignando una tecla, la siguiente tecla pulsada se guarda.
            if estado["estado"] == "CONTROLES" and accion_reasignando is not None:

                controles[accion_reasignando] = e.key
                mensaje_controles = 90
                mensaje_controles_texto = nombre_tecla(e.key)
                accion_reasignando = None
                guardar_progreso()

                continue

            if e.key == pygame.K_ESCAPE:
                estado["estado"] = "MENU"

            # Debug pï¿½blico desactivado. Usar panel admin oculto.

            # =====================
            # HABILIDADES ESPECIALES DEL JUGADOR
            # =====================

            # DASH ENERGETICO - SHIFT
            if e.key == pygame.K_LSHIFT or e.key == pygame.K_RSHIFT:
                if estado["dash_cd"] <= 0 and estado["dash_timer"] <= 0:

                    if tecla_pulsada(teclas, "move_left"):
                        estado["dash_dir"] = -1
                    elif tecla_pulsada(teclas, "move_right"):
                        estado["dash_dir"] = 1

                    estado["dash_timer"] = 14
                    estado["dash_cd"] = int((510 if habilidad_comprada("energy_core") else 600) * factor_cooldown())
                    estado["inv"] = max(estado["inv"], 18)
                    shake = 10
                    flash = 4
                    particulas_dash(estado["nave_x"], estado["nave_y"], estado["dash_dir"])
                    reproducir_sfx("dash")

            # SUPERLASER DEL JUGADOR - ESPACIO
            if e.key == controles["special_laser"]:
                if estado["player_laser_cd"] <= 0 and estado["player_laser"] <= 0:

                    estado["player_laser"] = 50
                    estado["player_laser_cd"] = int((935 if habilidad_comprada("energy_core") else 1100) * factor_cooldown())
                    shake = 18
                    flash = 8
                    slowmo = 1
                    slowmo_timer = 0
                    reproducir_sfx("laser_charge", force=True)

            # BOMBA DE PULSO - E
            if e.key == controles["pulse"]:
                if estado["pulse_cd"] <= 0 and estado["pulse_timer"] <= 0:

                    estado["pulse_timer"] = 55
                    estado["pulse_radius"] = 0
                    estado["pulse_cd"] = int((1275 if habilidad_comprada("energy_core") else 1500) * factor_cooldown())
                    centro_x = estado["nave_x"] + 25
                    centro_y = estado["nave_y"] + 25
                    activar_pulso_jugador(centro_x, centro_y)

            # =====================
            # HABILIDADES ESPECIALES DEL JUGADOR 2
            # =====================
            if estado.get("coop",False):

                if e.key == controles["p2_dash"]:
                    if estado["dash2_cd"] <= 0 and estado["dash2_timer"] <= 0:

                        if input_p2_activo("p2_move_left", teclas):
                            estado["dash2_dir"] = -1
                        elif input_p2_activo("p2_move_right", teclas):
                            estado["dash2_dir"] = 1

                        estado["dash2_timer"] = 14
                        estado["dash2_cd"] = int((510 if habilidad_comprada("energy_core") else 600) * factor_cooldown())
                        estado["inv2"] = max(estado["inv2"], 18)
                        reproducir_sfx("dash")
                        shake = 10
                        flash = 4
                        particulas_dash(estado["nave2_x"], estado["nave2_y"], estado["dash2_dir"])

                if e.key == controles["p2_special_laser"]:
                    if estado["player_laser2_cd"] <= 0 and estado["player_laser2"] <= 0:

                        estado["player_laser2"] = 50
                        estado["player_laser2_cd"] = int((935 if habilidad_comprada("energy_core") else 1100) * factor_cooldown())
                        shake = 18
                        flash = 8
                        slowmo = 1
                        slowmo_timer = 0
                        reproducir_sfx("laser_charge", force=True)

                if e.key == controles["p2_pulse"]:
                    if estado["pulse2_cd"] <= 0 and estado["pulse2_timer"] <= 0:

                        estado["pulse2_timer"] = 55
                        estado["pulse2_radius"] = 0
                        estado["pulse2_cd"] = int((1275 if habilidad_comprada("energy_core") else 1500) * factor_cooldown())
                        activar_pulso_jugador(estado["nave2_x"]+21, estado["nave2_y"]+21)

                if e.key == controles["p2_ultimate_overdrive"]:
                    if not overdrive_permitido():
                        estado["ultimate_message"] = 90
                        estado["ultimate_message_text"] = txt("ultimate_boss_only")
                    elif hay_boss_activo() and estado["ultimate_overdrive_cd"] <= 0 and estado["ultimate_overdrive"] <= 0:
                        estado["ultimate_overdrive"] = 480
                        estado["ultimate_overdrive_tick"] = 0
                        estado["ultimate_overdrive_cd"] = int((1920 if habilidad_comprada("ultimate_core") else 2400) * factor_cooldown())
                        estado["ultimate_message"] = 90
                        estado["ultimate_message_text"] = txt("overdrive_activated")
                        estado["inv2"] = max(estado["inv2"], 90)
                        shake = 30
                        flash = 18
                        slowmo = 1
                        slowmo_timer = 0
                    elif not hay_boss_activo():
                        estado["ultimate_message"] = 90
                        estado["ultimate_message_text"] = txt("ultimate_boss_only")

                if e.key == controles["p2_ultimate_blackhole"]:
                    if not ultimates_boss_permitidas():
                        estado["ultimate_message"] = 90
                        estado["ultimate_message_text"] = txt("ultimate_boss_only")
                    elif hay_boss_activo() and estado["ultimate_blackhole_cd"] <= 0 and estado["ultimate_blackhole"] <= 0:
                        cx, cy = centro_boss_activo()
                        estado["ultimate_blackhole"] = 360
                        estado["ultimate_blackhole_cd"] = int((2400 if habilidad_comprada("ultimate_core") else 3000) * factor_cooldown())
                        estado["ultimate_blackhole_x"] = cx
                        estado["ultimate_blackhole_y"] = cy
                        estado["ultimate_message"] = 90
                        estado["ultimate_message_text"] = txt("black_hole")
                        shake = 35
                        flash = 20
                        slowmo = 1
                        slowmo_timer = 0
                    elif not hay_boss_activo():
                        estado["ultimate_message"] = 90
                        estado["ultimate_message_text"] = txt("ultimate_boss_only")

                if e.key == controles["p2_ultimate_orbital"]:
                    if not ultimates_boss_permitidas():
                        estado["ultimate_message"] = 90
                        estado["ultimate_message_text"] = txt("ultimate_boss_only")
                    elif hay_boss_activo() and estado["ultimate_orbital_cd"] <= 0 and estado["ultimate_orbital"] <= 0:
                        cx, cy = centro_boss_activo()
                        estado["ultimate_orbital"] = 150
                        estado["ultimate_orbital_cd"] = int((2880 if habilidad_comprada("ultimate_core") else 3600) * factor_cooldown())
                        estado["ultimate_orbital_x"] = cx
                        estado["ultimate_message"] = 90
                        estado["ultimate_message_text"] = txt("orbital_strike")
                        shake = 40
                        flash = 22
                        slowmo = 1
                        slowmo_timer = 0
                    elif not hay_boss_activo():
                        estado["ultimate_message"] = 90
                        estado["ultimate_message_text"] = txt("ultimate_boss_only")

            # =====================
            # ULTIMATE ATTACKS - SOLO DURANTE BOSS FIGHTS
            # =====================

            # Q - OVERDRIVE MODE
            if e.key == controles["ultimate_overdrive"]:
                if not overdrive_permitido():
                    estado["ultimate_message"] = 90
                    estado["ultimate_message_text"] = txt("ultimate_boss_only")

                elif hay_boss_activo() and estado["ultimate_overdrive_cd"] <= 0 and estado["ultimate_overdrive"] <= 0:

                    estado["ultimate_overdrive"] = 480
                    estado["ultimate_overdrive_tick"] = 0
                    estado["ultimate_overdrive_cd"] = int((1920 if habilidad_comprada("ultimate_core") else 2400) * factor_cooldown())
                    estado["ultimate_message"] = 90
                    estado["ultimate_message_text"] = txt("overdrive_activated")

                    # Tras el nerf, Overdrive mantiene defensa y visuales,
                    # pero ya no multiplica el disparo principal.
                    estado["inv"] = max(estado["inv"], 90)

                    shake = 30
                    flash = 18
                    slowmo = 1
                    slowmo_timer = 0

                elif not hay_boss_activo():
                    estado["ultimate_message"] = 90
                    estado["ultimate_message_text"] = txt("ultimate_boss_only")

            # R - BLACK HOLE
            if e.key == controles["ultimate_blackhole"]:
                if not ultimates_boss_permitidas():
                    estado["ultimate_message"] = 90
                    estado["ultimate_message_text"] = txt("ultimate_boss_only")

                elif hay_boss_activo() and estado["ultimate_blackhole_cd"] <= 0 and estado["ultimate_blackhole"] <= 0:

                    cx, cy = centro_boss_activo()

                    estado["ultimate_blackhole"] = 360
                    estado["ultimate_blackhole_cd"] = int((2400 if habilidad_comprada("ultimate_core") else 3000) * factor_cooldown())
                    estado["ultimate_blackhole_x"] = cx
                    estado["ultimate_blackhole_y"] = cy
                    estado["ultimate_message"] = 90
                    estado["ultimate_message_text"] = txt("black_hole")

                    shake = 35
                    flash = 20
                    slowmo = 1
                    slowmo_timer = 0

                elif not hay_boss_activo():
                    estado["ultimate_message"] = 90
                    estado["ultimate_message_text"] = txt("ultimate_boss_only")

            # T - ORBITAL STRIKE
            if e.key == controles["ultimate_orbital"]:
                if not ultimates_boss_permitidas():
                    estado["ultimate_message"] = 90
                    estado["ultimate_message_text"] = txt("ultimate_boss_only")

                elif hay_boss_activo() and estado["ultimate_orbital_cd"] <= 0 and estado["ultimate_orbital"] <= 0:

                    cx, cy = centro_boss_activo()

                    estado["ultimate_orbital"] = 150
                    estado["ultimate_orbital_cd"] = int((2880 if habilidad_comprada("ultimate_core") else 3600) * factor_cooldown())
                    estado["ultimate_orbital_x"] = cx
                    estado["ultimate_message"] = 90
                    estado["ultimate_message_text"] = txt("orbital_strike")

                    shake = 40
                    flash = 22
                    slowmo = 1
                    slowmo_timer = 0

                elif not hay_boss_activo():
                    estado["ultimate_message"] = 90
                    estado["ultimate_message_text"] = txt("ultimate_boss_only")

            # SPAWN NUEVOS ENEMIGOS NIVEL 4 SIN BOSS
            if False and e.key == pygame.K_n:
                estado["score"] = 70000
                estado["boss"] = None
                estado["boss_final"] = None
                estado["boss_laser"] = None
                estado["boss_spawned"] = True
                estado["boss_final_spawned"] = True
                estado["boss_laser_spawned"] = False
                estado["enemigos"].clear()
                estado["balas_enemigas"].clear()

                enemigos_prueba = [
                    ("sentinel", 90, -70, 12),
                    ("hunter", 240, -120, 10),
                    ("void_orb", 410, -90, 14),
                    ("laser_satellite", 570, -100, 16),
                ]

                for tipo_enemigo, x_enemigo, y_enemigo, vida_enemigo in enemigos_prueba:
                    estado["enemigos"].append({
                        "tipo":tipo_enemigo,
                        "x":x_enemigo,
                        "y":y_enemigo,
                        "vida":vida_enemigo
                    })

                shake = 18
                flash = 6

            # SPAWN BOSS NORMAL
            if False and e.key == pygame.K_b:
                if estado["boss"] is None:
                    estado["boss"] = {
                        "x":300,
                        "y":50,
                        "vida":200,
                        "dir":1,
                        "cool":0
                    }
                    estado["boss_spawned"] = True
                    activar_intro_boss("normal", "ASTEROID COMMANDER", 90)
                    shake = 20

            # SPAWN BOSS FINAL
            if False and e.key == pygame.K_f:
                estado["boss_final"] = {
                    "x":250,
                    "y":50,
                    "vida":400,
                    "dir":1,
                    "cool":0
                }
                estado["boss_final_spawned"] = True
                activar_intro_boss("final", "OMEGA DESTROYER", 120)
                shake = 25

            # SPAWN NUEVO BOSS LASER
            if False and e.key == pygame.K_l:
                estado["boss_laser"] = {
                    "x":250,
                    "y":35,
                    "vida":650,
                    "dir":1,
                    "cool":0
                }
                estado["boss_laser_spawned"] = True
                estado["boss"] = None
                estado["boss_final"] = None
                estado["enemigos"].clear()
                estado["balas_enemigas"].clear()
                activar_intro_boss("laser", "LASER OVERLORD", 150)
                shake = 35
                flash = 12

        if e.type == pygame.MOUSEWHEEL:
            if estado["estado"] == "CODEX":
                codex_v64_scroll = max(0, min(276, codex_v64_scroll - e.y * 32))
                continue

        if e.type == pygame.MOUSEBUTTONDOWN:

            if estado["estado"] == "GAME_OVER":
                estado["estado"] = "MENU"

            if estado["estado"] == "BOSS_LOOT":
                mx,my = convertir_pos_mouse(e.pos)
                opciones = estado.get("boss_loot_choices",[])
                xs = [155,400,645]
                for idx,op in enumerate(opciones):
                    if pygame.Rect(xs[idx]-94,185,188,285).collidepoint((mx,my)):
                        aplicar_loot_boss(op)
                        break
                continue

            if estado["estado"] == "MENU":

                if start_btn.collidepoint(convertir_pos_mouse(e.pos)):

                    if multijugador_actual == "online_join":
                        estado["estado"] = "ONLINE_JOIN"
                        net_join_ip = ""
                        net_status = txt("online_join_prompt")
                    else:
                        if multijugador_actual == "online_host":
                            iniciar_host_lan()
                            estado["estado"] = "ONLINE_HOST_LOBBY"
                        else:
                            estado = reiniciar()
                            registrar_partida_si_necesario()

                            if habilidad_comprada("auto_shield"):
                                estado["shield"] = 300
                            if build_seleccionada == "guardian":
                                estado["shield"] = max(estado.get("shield",0),420)
                                estado["inv"] = max(estado.get("inv",0),90)
                            aplicar_admin_next_run()

                elif options_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "OPCIONES"

                elif shop_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "TIENDA"

                elif controls_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "CONTROLES"

                elif language_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "IDIOMA"

                elif info_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "INFO"

                elif difficulty_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "DIFICULTAD"

                elif planet_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    planet_selector_index = indice_planeta(planeta_seleccionado)
                    estado["estado"] = "PLANETAS"

                elif profile_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "PERFIL"

                elif missions_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "MISIONES"

                elif codex_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "CODEX"

                elif achievements_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "LOGROS"

                elif upgrades_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "MEJORAS"

                elif daily_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    asegurar_diarias()
                    estado["estado"] = "DIARIAS"

                elif quit_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    pygame.quit()
                    sys.exit()

            elif estado["estado"] == "OPCIONES":

                if ship1_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    nave_seleccionada = 1
                    estado["nave_tipo"] = 1
                    flash = 5
                    shake = 8

                elif ship2_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    nave_seleccionada = 2
                    estado["nave_tipo"] = 2
                    flash = 5
                    shake = 8

                elif options_back_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "MENU"

            elif estado["estado"] == "TIENDA":

                if shop_back_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "MENU"

                else:
                    for id_nave, rect_shop in shop_ship_buttons.items():
                        if rect_shop.collidepoint(convertir_pos_mouse(e.pos)):
                            comprar_nave(id_nave)
                            estado["nave_tipo"] = nave_seleccionada
                            break

                    for habilidad, rect_shop in shop_ability_buttons.items():
                        if rect_shop.collidepoint(convertir_pos_mouse(e.pos)):
                            comprar_habilidad(habilidad)
                            break

            elif estado["estado"] == "CONTROLES":

                if controls_back_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    accion_reasignando = None
                    estado["estado"] = "MENU"

                elif reset_keys_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    controles = controles_por_defecto()
                    accion_reasignando = None
                    mensaje_controles = 90
                    mensaje_controles_texto = txt("keys_reset")
                    guardar_progreso()

                else:
                    for accion, rect_accion in control_action_buttons.items():
                        if rect_accion.collidepoint(convertir_pos_mouse(e.pos)):
                            accion_reasignando = accion
                            mensaje_controles = 0
                            break

            elif estado["estado"] == "INFO":

                if info_back_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "MENU"

            elif estado["estado"] == "PERFIL":

                if profile_back_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "MENU"

            elif estado["estado"] == "MISIONES":

                if missions_back_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "MENU"
                else:
                    for mid, rect_mid in mission_buttons.items():
                        if rect_mid.collidepoint(convertir_pos_mouse(e.pos)):
                            reclamar_mision(mid)
                            break

            elif estado["estado"] == "CODEX":

                if codex_back_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "MENU"
                else:
                    pos_codex = convertir_pos_mouse(e.pos)
                    for idx, rect_codex in enumerate(codex_v64_buttons):
                        if rect_codex.collidepoint(pos_codex):
                            codex_v64_selected = idx
                            codex_v64_scroll = 0
                            flash = max(flash,4)
                            break

            elif estado["estado"] == "LOGROS":

                if codex_back_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "MENU"
                else:
                    for aid, rect_a in achievement_buttons.items():
                        if rect_a.collidepoint(convertir_pos_mouse(e.pos)):
                            reclamar_logro(aid)
                            break

            elif estado["estado"] == "MEJORAS":

                if codex_back_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "MENU"
                else:
                    for uid, rect_u in upgrade_buttons.items():
                        if rect_u.collidepoint(convertir_pos_mouse(e.pos)):
                            comprar_mejora(uid)
                            break

            elif estado["estado"] == "DIARIAS":

                if codex_back_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "MENU"
                else:
                    for did, rect_d in daily_buttons.items():
                        if rect_d.collidepoint(convertir_pos_mouse(e.pos)):
                            reclamar_diaria(did)
                            break

            elif estado["estado"] == "PLANETAS":

                pos_mouse = convertir_pos_mouse(e.pos)
                if planet_back_btn.collidepoint(pos_mouse):
                    estado["estado"] = "MENU"
                elif planet_left_btn.collidepoint(pos_mouse):
                    planet_selector_index = (planet_selector_index - 1) % len(PLANET_DEFS)
                elif planet_right_btn.collidepoint(pos_mouse):
                    planet_selector_index = (planet_selector_index + 1) % len(PLANET_DEFS)
                elif planet_select_btn.collidepoint(pos_mouse):
                    p = PLANET_DEFS[planet_selector_index]
                    if planeta_desbloqueado(p["id"]):
                        if p.get("secret",False):
                            iniciar_scale0_directo()
                        else:
                            planeta_seleccionado = p["id"]
                            guardar_progreso()

            elif estado["estado"] == "DIFICULTAD":

                if difficulty_back_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "MENU"
                else:
                    for dif, rect_dif in difficulty_buttons.items():
                        if rect_dif.collidepoint(convertir_pos_mouse(e.pos)):
                            dificultad_actual = dif
                            guardar_progreso()
                            break

                    for modo, rect_modo in game_mode_buttons.items():
                        if rect_modo.collidepoint(convertir_pos_mouse(e.pos)):
                            multijugador_actual = modo
                            guardar_progreso()
                            break

            elif estado["estado"] == "IDIOMA":

                if spanish_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    idioma_actual = "ES"
                    flash = 5
                    shake = 6
                    guardar_progreso()

                elif english_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    idioma_actual = "EN"
                    flash = 5
                    shake = 6
                    guardar_progreso()

                elif language_back_btn.collidepoint(convertir_pos_mouse(e.pos)):
                    estado["estado"] = "MENU"

    teclas = pygame.key.get_pressed()

    if mensaje_controles > 0:
        mensaje_controles -= 1

    if shop_message > 0:
        shop_message -= 1

    if admin_message_timer > 0:
        admin_message_timer -= 1

    if progreso_pendiente and pygame.time.get_ticks() - ultimo_autoguardado > 10000:
        guardar_progreso()

    # =====================
    # MENU
    # =====================
    if estado["estado"]=="MENU":
        dibujar_menu_cinematico()
        dibujar_admin_panel()
        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="PLANETAS":
        dibujar_selector_planetas()
        dibujar_admin_panel()
        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="OPCIONES":
        # Selector de naves animado, sin imagen estï¿½tica.
        pantalla.fill((0,0,14))

        tiempo_op = pygame.time.get_ticks()/1000
        mx,my = convertir_pos_mouse(pygame.mouse.get_pos())

        capa_neb = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)

        for n in menu_nebulosas:
            n["y"] += n["vel"] * 0.75

            if n["y"] > ALTO + 220:
                n["y"] = -220
                n["x"] = random.randint(-150,ANCHO)

            pulso = int(6*math.sin(tiempo_op*1.4 + n["x"]))
            color = n["color"]

            pygame.draw.circle(
                capa_neb,
                (color[0],color[1],color[2],max(5,n["alpha"]+pulso)),
                (
                    int(n["x"]),
                    int(n["y"])
                ),
                n["radio"]
            )

        pantalla.blit(capa_neb,(0,0))

        for e in menu_estrellas:
            e["y"] += e["vel"] * 0.85

            if e["y"] > ALTO:
                e["y"] = 0
                e["x"] = random.randint(0,ANCHO)

            pygame.draw.circle(
                pantalla,
                (180,180,220),
                (
                    int(e["x"]),
                    int(e["y"])
                ),
                e["r"]
            )

        for i in range(8):
            x_line = int((i*120 + tiempo_op*18) % (ANCHO+160)) - 80
            pygame.draw.line(
                pantalla,
                (20,90,140),
                (x_line,0),
                (x_line-120,ALTO),
                1
            )

        titulo_op = pygame.font.SysFont(None,64).render(txt("select_ship"), True, BLANCO)
        pantalla.blit(
            titulo_op,
            (
                ANCHO//2 - titulo_op.get_width()//2,
                68
            )
        )

        subtitulo_op = fuente.render(txt("choose_fighter"), True, (170,210,255))
        pantalla.blit(
            subtitulo_op,
            (
                ANCHO//2 - subtitulo_op.get_width()//2,
                125
            )
        )

        flotacion1 = int(math.sin(tiempo_op*2.1)*10)
        flotacion2 = int(math.cos(tiempo_op*2.1)*10)

        ship1_hover = ship1_btn.collidepoint((mx,my))
        ship2_hover = ship2_btn.collidepoint((mx,my))

        nave1_scale = 185 if ship1_hover else 170
        nave2_scale = 185 if ship2_hover else 170

        nave1_render = pygame.transform.smoothscale(nave_img,(nave1_scale,nave1_scale))
        nave2_render = pygame.transform.smoothscale(nave2_img,(nave2_scale,nave2_scale))

        nave1_cx = ship1_btn.centerx
        nave1_cy = ship1_btn.y + 135
        nave2_cx = ship2_btn.centerx
        nave2_cy = ship2_btn.y + 135

        nave1_x = nave1_cx - nave1_scale//2
        nave1_y = nave1_cy - nave1_scale//2 + flotacion1

        nave2_x = nave2_cx - nave2_scale//2
        nave2_y = nave2_cy - nave2_scale//2 + flotacion2

        crear_glow(
            pantalla,
            nave1_cx,
            nave1_cy+flotacion1,
            85 if nave_seleccionada==1 else 60,
            (40,180,255),
            70 if nave_seleccionada==1 else 42
        )

        crear_glow(
            pantalla,
            nave2_cx,
            nave2_cy+flotacion2,
            85 if nave_seleccionada==2 else 60,
            (255,220,120),
            70 if nave_seleccionada==2 else 42
        )

        pantalla.blit(nave1_render,(nave1_x,nave1_y))
        pantalla.blit(nave2_render,(nave2_x,nave2_y))

        if nave_seleccionada == 1:
            pygame.draw.circle(pantalla,(0,220,255),(nave1_cx,ship1_btn.y+250),8)
            pygame.draw.line(pantalla,(0,220,255),(nave1_cx-70,ship1_btn.y+272),(nave1_cx+70,ship1_btn.y+272),3)
            seleccionado_render = fuente_peq.render(txt("selected"), True, BLANCO)
            pantalla.blit(seleccionado_render,(nave1_cx-seleccionado_render.get_width()//2,ship1_btn.y+292))
        else:
            pygame.draw.circle(pantalla,(255,220,120),(nave2_cx,ship2_btn.y+250),8)
            pygame.draw.line(pantalla,(255,220,120),(nave2_cx-70,ship2_btn.y+272),(nave2_cx+70,ship2_btn.y+272),3)
            seleccionado_render = fuente_peq.render(txt("selected"), True, BLANCO)
            pantalla.blit(seleccionado_render,(nave2_cx-seleccionado_render.get_width()//2,ship2_btn.y+292))

        if ship1_hover:
            pygame.draw.circle(pantalla,(255,255,255),(nave1_cx,ship1_btn.y+250),12,1)
            hover_render = fuente_peq.render("SHIP 1", True, BLANCO)
            pantalla.blit(hover_render,(nave1_cx-hover_render.get_width()//2,ship1_btn.y+318))

        if ship2_hover:
            pygame.draw.circle(pantalla,(255,255,255),(nave2_cx,ship2_btn.y+250),12,1)
            hover_render = fuente_peq.render("SHIP 2", True, BLANCO)
            pantalla.blit(hover_render,(nave2_cx-hover_render.get_width()//2,ship2_btn.y+318))

        volver_hover = options_back_btn.collidepoint((mx,my))

        if volver_hover:
            crear_rect_glow(
                pantalla,
                (options_back_btn.x,options_back_btn.y,options_back_btn.w,options_back_btn.h),
                (80,220,255),
                65,
                12
            )

        pygame.draw.rect(
            pantalla,
            (12,28,50) if not volver_hover else (28,65,95),
            options_back_btn,
            border_radius=10
        )

        pygame.draw.rect(
            pantalla,
            (80,180,240) if not volver_hover else (120,240,255),
            options_back_btn,
            2,
            border_radius=10
        )

        volver_render = fuente.render(txt("back"), True, BLANCO)
        pantalla.blit(
            volver_render,
            (
                options_back_btn.centerx-volver_render.get_width()//2,
                options_back_btn.centery-volver_render.get_height()//2
            )
        )

        dibujar_admin_panel()
        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="PERFIL":
        dibujar_fondo_menu_animado(0.75)

        mx,my = convertir_pos_mouse(pygame.mouse.get_pos())

        titulo = pygame.font.SysFont(None,58).render(txt("profile_title"), True, BLANCO)
        pantalla.blit(titulo,(ANCHO//2 - titulo.get_width()//2,50))

        panel = pygame.Rect(ANCHO//2-360,120,720,380)
        crear_rect_glow(pantalla,(panel.x,panel.y,panel.w,panel.h),(80,180,255),45,16)
        pygame.draw.rect(pantalla,(4,12,28),panel,border_radius=14)
        pygame.draw.rect(pantalla,(80,180,255),panel,2,border_radius=14)

        datos_perfil = [
            (txt("best_score"), stats["best_score"]),
            (txt("games_played"), stats["games_played"]),
            (txt("enemies_destroyed"), stats["enemies_destroyed"]),
            (txt("bosses_defeated"), stats["bosses_defeated"]),
            (txt("coins_earned"), stats["coins_earned"]),
            (txt("ships_owned"), len(owned_ships)),
            (txt("abilities_owned"), len(owned_abilities)),
            (txt("current_difficulty"), nombre_dificultad()),
            (txt("game_mode"), nombre_modo_juego())
        ]

        y = 145
        for nombre, valor in datos_perfil:
            fila = pygame.Rect(panel.x+45,y-4,panel.w-90,30)
            pygame.draw.rect(pantalla,(8,22,42),fila,border_radius=6)
            nombre_render = fuente_peq.render(str(nombre), True, (180,220,255))
            valor_render = fuente_peq.render(str(valor), True, BLANCO)
            pantalla.blit(nombre_render,(fila.x+16,y+2))
            pantalla.blit(valor_render,(fila.right-20-valor_render.get_width(),y+2))
            y += 40

        hover_back = profile_back_btn.collidepoint((mx,my))

        if hover_back:
            crear_rect_glow(pantalla,(profile_back_btn.x,profile_back_btn.y,profile_back_btn.w,profile_back_btn.h),(80,220,255),70,12)

        pygame.draw.rect(pantalla,(12,28,50) if not hover_back else (28,65,95),profile_back_btn,border_radius=10)
        pygame.draw.rect(pantalla,(80,180,240) if not hover_back else (120,240,255),profile_back_btn,2,border_radius=10)
        volver_render = fuente.render(txt("back"), True, BLANCO)
        pantalla.blit(volver_render,(profile_back_btn.centerx-volver_render.get_width()//2,profile_back_btn.centery-volver_render.get_height()//2))

        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="MISIONES":
        dibujar_fondo_menu_animado(0.75)

        mx,my = convertir_pos_mouse(pygame.mouse.get_pos())

        titulo = pygame.font.SysFont(None,58).render(txt("missions_title"), True, BLANCO)
        pantalla.blit(titulo,(ANCHO//2 - titulo.get_width()//2,45))

        misiones = ["destroy_50","score_100k","boss_1","coins_25k"]
        y = 120

        for mid in misiones:
            datos = estado_mision(mid)
            rect = pygame.Rect(ANCHO//2-470,y,720,62)
            pygame.draw.rect(pantalla,(4,12,28),rect,border_radius=12)
            pygame.draw.rect(pantalla,(80,180,255),rect,2,border_radius=12)

            dibujar_texto_centrado_auto(pantalla, datos["texto"], pygame.Rect(rect.x+18,y+7,300,26), BLANCO, 26, 14)

            progreso_txt = f"{txt('progress')}: {datos['progreso']} / {datos['objetivo']}"
            recompensa_txt = f"{txt('reward')}: {datos['recompensa']}"

            dibujar_texto_centrado_auto(pantalla, progreso_txt, pygame.Rect(rect.x+20,y+36,300,20), (180,220,255), 20, 12)
            dibujar_texto_centrado_auto(pantalla, recompensa_txt, pygame.Rect(rect.x+345,y+36,240,20), (255,220,120), 20, 12)

            btn = mission_buttons[mid]
            hover = btn.collidepoint((mx,my))

            if datos["reclamada"]:
                texto_btn = txt("claimed")
                color = (100,100,120)
            elif datos["completada"]:
                texto_btn = txt("claim")
                color = (80,255,160)
            else:
                texto_btn = txt("completed") if datos["completada"] else "..."
                color = (90,130,170)

            if hover and datos["completada"] and not datos["reclamada"]:
                crear_rect_glow(pantalla,(btn.x,btn.y,btn.w,btn.h),color,55,10)

            pygame.draw.rect(pantalla,(12,28,50),btn,border_radius=8)
            pygame.draw.rect(pantalla,color,btn,2,border_radius=8)

            dibujar_texto_centrado_auto(pantalla, texto_btn, btn, BLANCO, 20, 12)

            y += 80

        if shop_message > 0:
            msg = fuente.render(shop_message_text, True, BLANCO)
            pantalla.blit(msg,(ANCHO//2-msg.get_width()//2,485))

        hover_back = missions_back_btn.collidepoint((mx,my))

        if hover_back:
            crear_rect_glow(pantalla,(missions_back_btn.x,missions_back_btn.y,missions_back_btn.w,missions_back_btn.h),(80,220,255),70,12)

        pygame.draw.rect(pantalla,(12,28,50) if not hover_back else (28,65,95),missions_back_btn,border_radius=10)
        pygame.draw.rect(pantalla,(80,180,240) if not hover_back else (120,240,255),missions_back_btn,2,border_radius=10)
        dibujar_texto_centrado_auto(pantalla, txt("back"), missions_back_btn, BLANCO, 30, 14)

        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="CODEX":
        dibujar_fondo_menu_animado(0.75)

        mx,my = convertir_pos_mouse(pygame.mouse.get_pos())

        titulo_txt = "SCALETALE CODEX" if idioma_actual == "EN" else "CODEX SCALETALE"
        titulo = pygame.font.SysFont(None,54).render(titulo_txt, True, BLANCO)
        pantalla.blit(titulo,(ANCHO//2 - titulo.get_width()//2,30))

        subtitulo_txt = "Pilot database / systems archive" if idioma_actual == "EN" else "Base de datos del piloto / archivo de sistemas"
        dibujar_texto_centrado_auto(pantalla, subtitulo_txt, pygame.Rect(ANCHO//2-360,74,720,24), (180,220,255), 22, 12)

        entradas = entradas_codex_v64()
        seleccionado_idx = max(0,min(codex_v64_selected,len(entradas)-1))
        entrada = entradas[seleccionado_idx]

        lista_panel = pygame.Rect(ANCHO//2-555,130,330,430)
        ficha_panel = pygame.Rect(ANCHO//2-200,130,760,430)
        crear_rect_glow(pantalla,(ficha_panel.x,ficha_panel.y,ficha_panel.w,ficha_panel.h),entrada["color"],34,14)
        pygame.draw.rect(pantalla,(3,10,22),lista_panel,border_radius=12)
        pygame.draw.rect(pantalla,(70,130,170),lista_panel,2,border_radius=12)
        pygame.draw.rect(pantalla,(4,12,26),ficha_panel,border_radius=12)
        pygame.draw.rect(pantalla,entrada["color"],ficha_panel,2,border_radius=12)

        etiqueta_lista = "ENTRIES" if idioma_actual == "EN" else "ENTRADAS"
        dibujar_texto_centrado_auto(pantalla, etiqueta_lista, pygame.Rect(lista_panel.x+10,lista_panel.y+10,lista_panel.w-20,24), (255,220,120), 22, 12)

        for idx,item in enumerate(entradas):
            rect = codex_v64_buttons[idx]
            hover = rect.collidepoint((mx,my))
            activo = idx == seleccionado_idx
            color_item = item["color"]
            if hover or activo:
                crear_rect_glow(pantalla,(rect.x,rect.y,rect.w,rect.h),color_item,36 if activo else 24,8)
            pygame.draw.rect(pantalla,(8,28,44) if activo else ((8,20,34) if hover else (4,13,25)),rect,border_radius=8)
            pygame.draw.rect(pantalla,color_item if activo else (70,115,145),rect,2,border_radius=8)
            dibujar_icono_codex(item["icon"], rect.x+24, rect.centery, color_item)
            nombre = pygame.font.SysFont(None,21).render(item["title"][:24], True, (240,248,255))
            sub = pygame.font.SysFont(None,16).render(item["short"][:28], True, (150,200,220))
            pantalla.blit(nombre,(rect.x+52,rect.y+8))
            pantalla.blit(sub,(rect.x+52,rect.y+29))

        dibujar_icono_codex(entrada["icon"], ficha_panel.x+66, ficha_panel.y+72, entrada["color"])
        titulo_ficha = pygame.font.SysFont(None,38).render(entrada["title"], True, BLANCO)
        pantalla.blit(titulo_ficha,(ficha_panel.x+115,ficha_panel.y+38))
        subtitulo_ficha = pygame.font.SysFont(None,22).render(entrada["short"], True, entrada["color"])
        pantalla.blit(subtitulo_ficha,(ficha_panel.x+116,ficha_panel.y+76))

        view_rect = pygame.Rect(ficha_panel.x+24, ficha_panel.y+116, ficha_panel.w-48, ficha_panel.h-138)
        contenido_h = 520
        max_scroll = max(0, contenido_h - view_rect.h)
        codex_v64_scroll = max(0, min(max_scroll, codex_v64_scroll))
        contenido = pygame.Surface((view_rect.w, contenido_h), pygame.SRCALPHA)

        secciones = [
            ("LORE" if idioma_actual == "EN" else "HISTORIA", entrada["story"]),
            ("HOW IT WORKS" if idioma_actual == "EN" else "COMO FUNCIONA", entrada["how"]),
            ("GAME EFFECT" if idioma_actual == "EN" else "EFECTO EN JUEGO", entrada["effect"])
        ]
        y_contenido = 6
        for label, cuerpo in secciones:
            label_render = pygame.font.SysFont(None,21).render(label, True, (255,220,120))
            contenido.blit(label_render,(4,y_contenido))
            pygame.draw.line(contenido,entrada["color"],(4,y_contenido+23),(view_rect.w-18,y_contenido+23),1)
            dibujar_texto_multilinea_auto(
                contenido,
                cuerpo,
                pygame.Rect(6,y_contenido+34,view_rect.w-26,100),
                (190,225,238),
                19,
                12,
                2
            )
            y_contenido += 158

        pygame.draw.rect(pantalla,(2,8,18),view_rect,border_radius=8)
        pygame.draw.rect(pantalla,(38,88,120),view_rect,1,border_radius=8)
        pantalla.blit(contenido.subsurface(pygame.Rect(0,codex_v64_scroll,view_rect.w,view_rect.h)), view_rect)
        if max_scroll > 0:
            barra_x = view_rect.right - 8
            pygame.draw.line(pantalla,(30,70,95),(barra_x,view_rect.y+8),(barra_x,view_rect.bottom-8),3)
            knob_h = max(34, int((view_rect.h / contenido_h) * (view_rect.h-16)))
            knob_y = view_rect.y + 8 + int((codex_v64_scroll / max_scroll) * (view_rect.h-16-knob_h))
            pygame.draw.rect(pantalla,entrada["color"],pygame.Rect(barra_x-3,knob_y,6,knob_h),border_radius=4)

        nota = ""
        dibujar_texto_centrado_auto(pantalla, nota, pygame.Rect(ANCHO//2-360,570,720,18), (145,200,220), 18, 12)

        hover_back = codex_back_btn.collidepoint((mx,my))

        if hover_back:
            crear_rect_glow(pantalla,(codex_back_btn.x,codex_back_btn.y,codex_back_btn.w,codex_back_btn.h),(80,220,255),70,12)

        pygame.draw.rect(pantalla,(12,28,50) if not hover_back else (28,65,95),codex_back_btn,border_radius=10)
        pygame.draw.rect(pantalla,(80,180,240) if not hover_back else (120,240,255),codex_back_btn,2,border_radius=10)
        dibujar_texto_centrado_auto(pantalla, txt("back"), codex_back_btn, BLANCO, 30, 14)

        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="LOGROS":
        dibujar_fondo_menu_animado(0.75)
        mx,my = convertir_pos_mouse(pygame.mouse.get_pos())

        titulo = pygame.font.SysFont(None,58).render(txt("achievements_title"), True, BLANCO)
        pantalla.blit(titulo,(ANCHO//2 - titulo.get_width()//2,45))

        y = 105
        for aid, logro in ACHIEVEMENTS.items():
            progreso = progreso_logro(aid)
            completado = progreso >= logro["goal"]
            reclamado = aid in achievement_claimed
            rect = pygame.Rect(ANCHO//2-470,y,720,54)
            color = (80,255,160) if completado and not reclamado else ((100,100,120) if reclamado else (80,180,255))
            pygame.draw.rect(pantalla,(4,12,28),rect,border_radius=12)
            pygame.draw.rect(pantalla,color,rect,2,border_radius=12)
            dibujar_texto_centrado_auto(pantalla, logro["name"], pygame.Rect(rect.x+18,y+5,300,24), BLANCO, 28, 15)
            detalle = f"{logro['desc']}  {progreso}/{logro['goal']}   +{logro['reward']} {txt('coins')}"
            dibujar_texto_multilinea_auto(pantalla, detalle, pygame.Rect(rect.x+22,y+29,560,22), (190,225,245), 20, 13, 1)

            btn = achievement_buttons[aid]
            hover = btn.collidepoint((mx,my))
            if hover and completado and not reclamado:
                crear_rect_glow(pantalla,(btn.x,btn.y,btn.w,btn.h),color,45,8)
            texto_btn = txt("claimed") if reclamado else (txt("claim") if completado else "...")
            pygame.draw.rect(pantalla,(12,28,50),btn,border_radius=8)
            pygame.draw.rect(pantalla,color,btn,2,border_radius=8)
            dibujar_texto_centrado_auto(pantalla, texto_btn, btn, BLANCO, 20, 12)
            y += 70

        if shop_message > 0:
            msg = fuente.render(shop_message_text, True, BLANCO)
            pantalla.blit(msg,(ANCHO//2-msg.get_width()//2,470))

        hover_back = codex_back_btn.collidepoint((mx,my))
        pygame.draw.rect(pantalla,(12,28,50) if not hover_back else (28,65,95),codex_back_btn,border_radius=10)
        pygame.draw.rect(pantalla,(80,180,240),codex_back_btn,2,border_radius=10)
        dibujar_texto_centrado_auto(pantalla, txt("back"), codex_back_btn, BLANCO, 30, 14)
        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="MEJORAS":
        dibujar_fondo_menu_animado(0.75)
        mx,my = convertir_pos_mouse(pygame.mouse.get_pos())

        titulo = pygame.font.SysFont(None,58).render(txt("upgrades_title"), True, BLANCO)
        pantalla.blit(titulo,(ANCHO//2 - titulo.get_width()//2,45))

        y = 145
        for uid, info in UPGRADE_DEFS.items():
            nivel_u = permanent_upgrades.get(uid,0)
            max_u = info["max"]
            rect = pygame.Rect(ANCHO//2-470,y,720,74)
            color = (80,220,255) if uid != "coin" else (255,220,80)
            pygame.draw.rect(pantalla,(4,12,28),rect,border_radius=12)
            pygame.draw.rect(pantalla,color,rect,2,border_radius=12)
            nombre = txt(info["name_key"])
            dibujar_texto_centrado_auto(pantalla, nombre, pygame.Rect(rect.x+18,y+8,300,28), BLANCO, 28, 15)
            dibujar_texto_multilinea_auto(pantalla, info["desc"], pygame.Rect(rect.x+22,y+36,360,30), (190,225,245), 20, 13, 1)
            nivel_txt = f"{txt('level_label')}: {nivel_u}/{max_u}"
            dibujar_texto_centrado_auto(pantalla, nivel_txt, pygame.Rect(rect.x+390,y+14,140,24), (255,220,120), 20, 12)

            btn = upgrade_buttons[uid]
            hover = btn.collidepoint((mx,my))
            if hover:
                crear_rect_glow(pantalla,(btn.x,btn.y,btn.w,btn.h),color,45,8)
            pygame.draw.rect(pantalla,(12,28,50),btn,border_radius=8)
            pygame.draw.rect(pantalla,color,btn,2,border_radius=8)
            texto_btn = txt("maxed") if nivel_u >= max_u else str(coste_mejora(uid))
            dibujar_texto_centrado_auto(pantalla, texto_btn, btn, BLANCO, 20, 12)
            y += 100

        if shop_message > 0:
            msg = fuente.render(shop_message_text, True, BLANCO)
            pantalla.blit(msg,(ANCHO//2-msg.get_width()//2,470))

        hover_back = codex_back_btn.collidepoint((mx,my))
        pygame.draw.rect(pantalla,(12,28,50) if not hover_back else (28,65,95),codex_back_btn,border_radius=10)
        pygame.draw.rect(pantalla,(80,180,240),codex_back_btn,2,border_radius=10)
        dibujar_texto_centrado_auto(pantalla, txt("back"), codex_back_btn, BLANCO, 30, 14)
        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="DIARIAS":
        asegurar_diarias()
        dibujar_fondo_menu_animado(0.75)
        mx,my = convertir_pos_mouse(pygame.mouse.get_pos())

        titulo = pygame.font.SysFont(None,58).render(txt("daily_title"), True, BLANCO)
        pantalla.blit(titulo,(ANCHO//2 - titulo.get_width()//2,45))
        dibujar_texto_centrado_auto(pantalla, txt("daily_reset") + "  |  " + texto_tiempo_diarias(), pygame.Rect(ANCHO//2-360,86,720,24), (180,220,255), 21, 12)

        y = 120
        for did, mision in DAILY_MISSION_POOL.items():
            progreso = progreso_diaria(did)
            completada = progreso >= mision["goal"]
            reclamada = daily_state.get("claimed",{}).get(did, False)
            rect = pygame.Rect(ANCHO//2-470,y,720,62)
            color = (80,255,160) if completada and not reclamada else ((100,100,120) if reclamada else (80,180,255))
            pygame.draw.rect(pantalla,(4,12,28),rect,border_radius=12)
            pygame.draw.rect(pantalla,color,rect,2,border_radius=12)
            dibujar_texto_centrado_auto(pantalla, mision["name"], pygame.Rect(rect.x+18,y+7,300,26), BLANCO, 28, 15)
            detalle = f"{txt('progress')}: {progreso}/{mision['goal']}   {txt('reward')}: {mision['reward']}"
            dibujar_texto_multilinea_auto(pantalla, detalle, pygame.Rect(rect.x+22,y+35,560,22), (190,225,245), 20, 13, 1)

            btn = daily_buttons[did]
            hover = btn.collidepoint((mx,my))
            if hover and completada and not reclamada:
                crear_rect_glow(pantalla,(btn.x,btn.y,btn.w,btn.h),color,45,8)
            texto_btn = txt("claimed") if reclamada else (txt("claim") if completada else "...")
            pygame.draw.rect(pantalla,(12,28,50),btn,border_radius=8)
            pygame.draw.rect(pantalla,color,btn,2,border_radius=8)
            dibujar_texto_centrado_auto(pantalla, texto_btn, btn, BLANCO, 20, 12)
            y += 80

        if shop_message > 0:
            msg = fuente.render(shop_message_text, True, BLANCO)
            pantalla.blit(msg,(ANCHO//2-msg.get_width()//2,485))

        hover_back = codex_back_btn.collidepoint((mx,my))
        pygame.draw.rect(pantalla,(12,28,50) if not hover_back else (28,65,95),codex_back_btn,border_radius=10)
        pygame.draw.rect(pantalla,(80,180,240),codex_back_btn,2,border_radius=10)
        dibujar_texto_centrado_auto(pantalla, txt("back"), codex_back_btn, BLANCO, 30, 14)
        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="DIFICULTAD":
        dibujar_fondo_menu_animado(0.85)

        mx,my = convertir_pos_mouse(pygame.mouse.get_pos())

        titulo_dif = pygame.font.SysFont(None,58).render(txt("difficulty_title"), True, BLANCO)
        pantalla.blit(titulo_dif,(ANCHO//2 - titulo_dif.get_width()//2,50))

        actual = fuente.render(txt("current_difficulty") + ": " + nombre_dificultad(), True, (255,220,120))
        pantalla.blit(actual,(ANCHO//2 - actual.get_width()//2,105))

        dif_data = [
            ("facil", txt("easy"), txt("easy_desc"), (80,220,255)),
            ("normal", txt("normal_mode"), txt("normal_desc"), (120,255,180)),
            ("dificil", txt("hard"), txt("hard_desc"), (255,170,70)),
            ("muy_dificil", txt("very_hard"), txt("very_hard_desc"), (255,70,70)),
        ]

        for dif_id, nombre, descripcion, color in dif_data:
            rect = difficulty_buttons[dif_id]
            hover = rect.collidepoint((mx,my))
            selected = dificultad_actual == dif_id

            if hover or selected:
                crear_rect_glow(
                    pantalla,
                    (rect.x,rect.y,rect.w,rect.h),
                    color,
                    70 if selected else 45,
                    14
                )

            pygame.draw.rect(
                pantalla,
                (8,20,38) if not hover else (18,42,70),
                rect,
                border_radius=14
            )
            pygame.draw.rect(
                pantalla,
                color if selected else (90,130,170),
                rect,
                3 if selected else 2,
                border_radius=14
            )

            dibujar_texto_centrado_auto(
                pantalla,
                nombre,
                pygame.Rect(rect.x+16, rect.y+10, rect.w-32, 24),
                BLANCO,
                28,
                15
            )

            dibujar_texto_multilinea_auto(
                pantalla,
                descripcion,
                pygame.Rect(rect.x+16, rect.y+38, rect.w-32, rect.h-44),
                (210,225,245),
                19,
                12,
                1
            )

        # Selector de modo de juego
        modo_title = fuente.render(txt("game_mode"), True, (255,220,120))
        pantalla.blit(modo_title,(ANCHO//2 - modo_title.get_width()//2,430))

        mode_data = [
            ("solo", txt("solo"), txt("solo_desc"), (80,220,255)),
            ("coop", txt("local_coop"), txt("coop_desc"), (190,90,255)),
            ("online_host", txt("online_host"), txt("host_desc"), (80,255,160)),
            ("online_join", txt("online_join"), txt("join_desc"), (255,190,80))
        ]

        for modo_id, nombre, descripcion, color in mode_data:
            rect = game_mode_buttons[modo_id]
            hover = rect.collidepoint((mx,my))
            selected = multijugador_actual == modo_id

            if hover or selected:
                crear_rect_glow(
                    pantalla,
                    (rect.x,rect.y,rect.w,rect.h),
                    color,
                    65 if selected else 40,
                    12
                )

            pygame.draw.rect(
                pantalla,
                (8,20,38) if not hover else (18,42,70),
                rect,
                border_radius=14
            )
            pygame.draw.rect(
                pantalla,
                color if selected else (90,130,170),
                rect,
                3 if selected else 2,
                border_radius=14
            )

            dibujar_texto_centrado_auto(
                pantalla,
                nombre,
                pygame.Rect(rect.x+10, rect.y+8, rect.w-20, 24),
                BLANCO,
                26,
                14
            )

            dibujar_texto_multilinea_auto(
                pantalla,
                descripcion,
                pygame.Rect(rect.x+10, rect.y+34, rect.w-20, rect.h-40),
                (210,225,245),
                17,
                11,
                1
            )

        if multijugador_actual == "coop":
            dibujar_texto_centrado_auto(
                pantalla,
                txt("p2_controls"),
                pygame.Rect(ANCHO//2-360,552,720,22),
                (220,220,255),
                19,
                11
            )

        hover_back = difficulty_back_btn.collidepoint((mx,my))

        if hover_back:
            crear_rect_glow(pantalla,(difficulty_back_btn.x,difficulty_back_btn.y,difficulty_back_btn.w,difficulty_back_btn.h),(80,220,255),70,12)

        pygame.draw.rect(
            pantalla,
            (12,28,50) if not hover_back else (28,65,95),
            difficulty_back_btn,
            border_radius=10
        )
        pygame.draw.rect(
            pantalla,
            (80,180,240) if not hover_back else (120,240,255),
            difficulty_back_btn,
            2,
            border_radius=10
        )

        volver_render = fuente.render(txt("back"), True, BLANCO)
        pantalla.blit(
            volver_render,
            (
                difficulty_back_btn.centerx-volver_render.get_width()//2,
                difficulty_back_btn.centery-volver_render.get_height()//2
            )
        )

        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="INFO":
        dibujar_fondo_menu_animado(0.75)

        mx,my = convertir_pos_mouse(pygame.mouse.get_pos())

        titulo_info = pygame.font.SysFont(None,56).render(txt("privacy_updates"), True, BLANCO)
        pantalla.blit(titulo_info,(ANCHO//2 - titulo_info.get_width()//2,42))

        panel = pygame.Rect(ANCHO//2-440,115,880,410)
        crear_rect_glow(pantalla,(panel.x,panel.y,panel.w,panel.h),(80,180,255),45,16)
        pygame.draw.rect(pantalla,(4,12,28),panel,border_radius=14)
        pygame.draw.rect(pantalla,(80,180,255),panel,2,border_radius=14)

        privacidad_titulo = fuente.render(txt("privacy"), True, (180,220,255))
        updates_titulo = fuente.render(txt("updates"), True, (180,220,255))
        pantalla.blit(privacidad_titulo,(panel.x+35,panel.y+25))

        privacidad_texto = txt("privacy_text")

        y = dibujar_texto_multilinea(
            pantalla,
            privacidad_texto,
            panel.x+35,
            panel.y+58,
            panel.w-70,
            fuente_peq,
            (210,225,245),
            21
        )

        pantalla.blit(updates_titulo,(panel.x+35,panel.y+225))

        updates_texto = txt("updates_text")

        dibujar_texto_multilinea(
            pantalla,
            updates_texto,
            panel.x+35,
            panel.y+258,
            panel.w-70,
            fuente_peq,
            (210,225,245),
            18
        )

        hover_back = info_back_btn.collidepoint((mx,my))

        if hover_back:
            crear_rect_glow(pantalla,(info_back_btn.x,info_back_btn.y,info_back_btn.w,info_back_btn.h),(80,220,255),70,12)

        pygame.draw.rect(
            pantalla,
            (12,28,50) if not hover_back else (28,65,95),
            info_back_btn,
            border_radius=10
        )
        pygame.draw.rect(
            pantalla,
            (80,180,240) if not hover_back else (120,240,255),
            info_back_btn,
            2,
            border_radius=10
        )

        volver_render = fuente.render(txt("back"), True, BLANCO)
        pantalla.blit(
            volver_render,
            (
                info_back_btn.centerx-volver_render.get_width()//2,
                info_back_btn.centery-volver_render.get_height()//2
            )
        )

        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="TIENDA":
        dibujar_fondo_menu_animado(0.9)

        mx,my = convertir_pos_mouse(pygame.mouse.get_pos())

        titulo_shop = pygame.font.SysFont(None,64).render(txt("shop"), True, BLANCO)
        pantalla.blit(titulo_shop,(ANCHO//2 - titulo_shop.get_width()//2,35))

        # Coins panel
        coin_panel = pygame.Rect(ANCHO//2+315,35,255,46)
        crear_rect_glow(pantalla,(coin_panel.x,coin_panel.y,coin_panel.w,coin_panel.h),(255,220,80),45,10)
        pygame.draw.rect(pantalla,(25,18,5),coin_panel,border_radius=10)
        pygame.draw.rect(pantalla,(255,220,80),coin_panel,2,border_radius=10)
        pantalla.blit(moneda_img,(coin_panel.x+12,coin_panel.y+9))
        coin_txt = fuente.render(numero_compacto(monedas), True, BLANCO)
        pantalla.blit(coin_txt,(coin_panel.right-18-coin_txt.get_width(),coin_panel.y+12))

        skins_txt = fuente.render(txt("skins"), True, (180,220,255))
        abilities_txt = fuente.render(txt("abilities"), True, (180,220,255))
        pantalla.blit(skins_txt,(ANCHO//2-495,112))
        pantalla.blit(abilities_txt,(ANCHO//2-495,382))

        # Ship cards
        ship_items = [
            (3, txt("crimson")),
            (4, txt("nova")),
            (5, txt("phantom")),
            (6, txt("eclipse")),
            (7, txt("aurora")),
            (8, txt("quantum")),
        ]

        for id_nave,nombre in ship_items:
            rect = shop_ship_buttons[id_nave]
            hover = rect.collidepoint((mx,my))
            owned = id_nave in owned_ships
            equipped = nave_seleccionada == id_nave
            color = color_nave_por_tipo(id_nave)
            img = preview_nave_por_tipo(id_nave)

            if hover or equipped:
                crear_rect_glow(pantalla,(rect.x,rect.y,rect.w,rect.h),color,55 if equipped else 36,10)

            pygame.draw.rect(pantalla,(5,15,32) if not hover else (12,32,60),rect,border_radius=12)
            pygame.draw.rect(pantalla,color if equipped else (90,130,170),rect,3 if equipped else 1,border_radius=12)

            img_x = rect.centerx - img.get_width()//2
            img_y = rect.y + 12
            crear_glow(pantalla,rect.centerx,img_y+45,36,color,38)
            pantalla.blit(img,(img_x,img_y))

            dibujar_texto_centrado_auto(pantalla, nombre, pygame.Rect(rect.x+4,rect.y+90,rect.w-8,22), BLANCO, 19, 11)

            if equipped:
                estado_texto = txt("equipped")
                estado_color = (120,255,180)
            elif owned:
                estado_texto = txt("equip")
                estado_color = (180,230,255)
            else:
                estado_texto = str(SHIP_PRICES[id_nave])
                estado_color = (255,220,80)

            dibujar_texto_centrado_auto(pantalla, estado_texto, pygame.Rect(rect.x+4,rect.y+118,rect.w-8,22), estado_color, 18, 11)

        # Ability cards
        ability_items = [
            ("triple_shot", txt("triple_shot"), "3 SHOTS", (80,220,255)),
            ("auto_shield", txt("auto_shield"), "START SHIELD", (80,255,160)),
            ("energy_core", txt("energy_core"), "COOLDOWN -15%", (255,220,80)),
            ("coin_booster", txt("coin_booster"), "+25% COINS", (255,200,60)),
            ("revive_core", txt("revive_core"), "1 REVIVE/RUN", (120,255,180)),
            ("ultimate_core", txt("ultimate_core"), "ULT CD -20%", (190,90,255)),
        ]

        for habilidad,nombre,desc,color in ability_items:
            rect = shop_ability_buttons[habilidad]
            hover = rect.collidepoint((mx,my))
            owned = habilidad in owned_abilities

            if hover or owned:
                crear_rect_glow(pantalla,(rect.x,rect.y,rect.w,rect.h),color,48 if owned else 32,8)

            pygame.draw.rect(pantalla,(5,15,32) if not hover else (12,32,60),rect,border_radius=12)
            pygame.draw.rect(pantalla,color if owned else (90,130,170),rect,2 if owned else 1,border_radius=12)

            dibujar_texto_centrado_auto(pantalla, nombre, pygame.Rect(rect.x+5,rect.y+8,rect.w-10,22), BLANCO, 19, 11)
            dibujar_texto_centrado_auto(pantalla, desc, pygame.Rect(rect.x+5,rect.y+32,rect.w-10,20), (180,220,255), 17, 10)

            if owned:
                price_render = fuente_peq.render(txt("owned"), True, (120,255,180))
            else:
                price_render = fuente_peq.render(str(ABILITY_PRICES[habilidad]), True, (255,220,80))

            dibujar_texto_centrado_auto(pantalla, txt("owned") if owned else str(ABILITY_PRICES[habilidad]), pygame.Rect(rect.x+5,rect.y+61,rect.w-10,22), (120,255,180) if owned else (255,220,80), 18, 11)

        if shop_message > 0:
            msg = fuente.render(shop_message_text, True, BLANCO)
            pygame.draw.rect(pantalla,(0,0,0),(ANCHO//2-msg.get_width()//2-18,475,msg.get_width()+36,32),border_radius=8)
            pygame.draw.rect(pantalla,(80,220,255),(ANCHO//2-msg.get_width()//2-18,475,msg.get_width()+36,32),2,border_radius=8)
            pantalla.blit(msg,(ANCHO//2-msg.get_width()//2,480))

        hover_back = shop_back_btn.collidepoint((mx,my))

        if hover_back:
            crear_rect_glow(pantalla,(shop_back_btn.x,shop_back_btn.y,shop_back_btn.w,shop_back_btn.h),(80,220,255),70,12)

        pygame.draw.rect(
            pantalla,
            (12,28,50) if not hover_back else (28,65,95),
            shop_back_btn,
            border_radius=10
        )
        pygame.draw.rect(
            pantalla,
            (80,180,240) if not hover_back else (120,240,255),
            shop_back_btn,
            2,
            border_radius=10
        )

        volver_render = fuente.render(txt("back"), True, BLANCO)
        pantalla.blit(
            volver_render,
            (
                shop_back_btn.centerx-volver_render.get_width()//2,
                shop_back_btn.centery-volver_render.get_height()//2
            )
        )

        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="CONTROLES":
        dibujar_fondo_menu_animado(0.9)

        mx,my = convertir_pos_mouse(pygame.mouse.get_pos())

        titulo_ctrl = pygame.font.SysFont(None,68).render(txt("controls_title"), True, BLANCO)
        pantalla.blit(titulo_ctrl,(ANCHO//2 - titulo_ctrl.get_width()//2,48))

        ayuda_ctrl = fuente_peq.render(txt("click_to_change"), True, (180,220,255))
        pantalla.blit(ayuda_ctrl,(ANCHO//2 - ayuda_ctrl.get_width()//2,105))

        panel = pygame.Rect(ANCHO//2-505,128,1010,390)
        crear_rect_glow(pantalla,(panel.x,panel.y,panel.w,panel.h),(80,180,255),45,16)
        pygame.draw.rect(pantalla,(4,12,28),panel,border_radius=14)
        pygame.draw.rect(pantalla,(80,180,255),panel,2,border_radius=14)

        p1_title = fuente_peq.render(txt("player1"), True, (255,220,120))
        p2_title = fuente_peq.render(txt("player2"), True, (255,220,120))
        pantalla.blit(p1_title,(ANCHO//2-430,138))
        pantalla.blit(p2_title,(ANCHO//2+95,138))

        acciones = [
            ("move_up", txt("move") + " UP"),
            ("move_left", txt("move") + " LEFT"),
            ("move_down", txt("move") + " DOWN"),
            ("move_right", txt("move") + " RIGHT"),
            ("shoot", txt("shoot")),
            ("dash", txt("dash")),
            ("special_laser", txt("laser")),
            ("pulse", txt("pulse")),
            ("ultimate_overdrive", txt("overdrive")),
            ("ultimate_blackhole", txt("blackhole")),
            ("ultimate_orbital", txt("orbital")),
            ("p2_move_up", txt("move") + " UP"),
            ("p2_move_left", txt("move") + " LEFT"),
            ("p2_move_down", txt("move") + " DOWN"),
            ("p2_move_right", txt("move") + " RIGHT"),
            ("p2_shoot", txt("shoot")),
            ("p2_dash", txt("p2_dash")),
            ("p2_special_laser", txt("p2_laser")),
            ("p2_pulse", txt("p2_pulse")),
            ("p2_ultimate_overdrive", txt("p2_overdrive")),
            ("p2_ultimate_blackhole", txt("p2_blackhole")),
            ("p2_ultimate_orbital", txt("p2_orbital"))
        ]

        for accion, descripcion in acciones:
            rect_accion = control_action_buttons[accion]
            hover = rect_accion.collidepoint((mx,my))
            seleccionando = accion_reasignando == accion

            if hover or seleccionando:
                crear_rect_glow(
                    pantalla,
                    (rect_accion.x,rect_accion.y,rect_accion.w,rect_accion.h),
                    (80,220,255),
                    65 if seleccionando else 38,
                    10
                )

            pygame.draw.rect(
                pantalla,
                (12,34,58) if not hover else (25,60,95),
                rect_accion,
                border_radius=7
            )

            pygame.draw.rect(
                pantalla,
                (255,220,80) if seleccionando else (80,180,240),
                rect_accion,
                2 if seleccionando else 1,
                border_radius=7
            )

            desc_render = fuente_peq.render(descripcion, True, BLANCO)
            tecla_render = fuente_peq.render(nombre_tecla(controles[accion]), True, (180,230,255))

            pantalla.blit(desc_render,(rect_accion.x+8,rect_accion.y+6))
            pantalla.blit(
                tecla_render,
                (
                    rect_accion.right-tecla_render.get_width()-10,
                    rect_accion.y+6
                )
            )

        if accion_reasignando is not None:
            esperando = fuente.render(
                txt("press_new_key") + " " + nombre_tecla(controles[accion_reasignando]),
                True,
                (255,230,120)
            )
            pantalla.blit(esperando,(ANCHO//2-esperando.get_width()//2,530))

        elif mensaje_controles > 0:
            msg = fuente.render(mensaje_controles_texto, True, (160,240,255))
            pantalla.blit(msg,(ANCHO//2-msg.get_width()//2,530))

        hover_reset = reset_keys_btn.collidepoint((mx,my))

        if hover_reset:
            crear_rect_glow(pantalla,(reset_keys_btn.x,reset_keys_btn.y,reset_keys_btn.w,reset_keys_btn.h),(255,180,80),60,12)

        pygame.draw.rect(
            pantalla,
            (50,30,12) if not hover_reset else (90,55,22),
            reset_keys_btn,
            border_radius=10
        )
        pygame.draw.rect(
            pantalla,
            (255,180,80),
            reset_keys_btn,
            2,
            border_radius=10
        )

        reset_render = fuente.render(txt("reset_keys"), True, BLANCO)
        pantalla.blit(
            reset_render,
            (
                reset_keys_btn.centerx-reset_render.get_width()//2,
                reset_keys_btn.centery-reset_render.get_height()//2
            )
        )

        hover_back = controls_back_btn.collidepoint((mx,my))

        if hover_back:
            crear_rect_glow(pantalla,(controls_back_btn.x,controls_back_btn.y,controls_back_btn.w,controls_back_btn.h),(80,220,255),70,12)

        pygame.draw.rect(
            pantalla,
            (12,28,50) if not hover_back else (28,65,95),
            controls_back_btn,
            border_radius=10
        )
        pygame.draw.rect(
            pantalla,
            (80,180,240) if not hover_back else (120,240,255),
            controls_back_btn,
            2,
            border_radius=10
        )

        volver_render = fuente.render(txt("back"), True, BLANCO)
        pantalla.blit(
            volver_render,
            (
                controls_back_btn.centerx-volver_render.get_width()//2,
                controls_back_btn.centery-volver_render.get_height()//2
            )
        )

        dibujar_admin_panel()
        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="IDIOMA":
        dibujar_fondo_menu_animado(0.9)

        mx,my = convertir_pos_mouse(pygame.mouse.get_pos())

        titulo_lang = pygame.font.SysFont(None,68).render(txt("language_title"), True, BLANCO)
        pantalla.blit(titulo_lang,(ANCHO//2 - titulo_lang.get_width()//2,80))

        opciones_idioma = [
            (spanish_btn, "ES", txt("spanish"), (255,220,80)),
            (english_btn, "EN", txt("english"), (80,190,255))
        ]

        for rect,codigo,nombre,color in opciones_idioma:
            hover = rect.collidepoint((mx,my))
            seleccionado = idioma_actual == codigo

            if hover or seleccionado:
                crear_rect_glow(pantalla,(rect.x,rect.y,rect.w,rect.h),color,70 if seleccionado else 45,14)

            pygame.draw.rect(
                pantalla,
                (12,28,50) if not hover else (28,65,95),
                rect,
                border_radius=14
            )

            pygame.draw.rect(
                pantalla,
                color if seleccionado else (90,130,170),
                rect,
                3 if seleccionado else 2,
                border_radius=14
            )

            codigo_render = pygame.font.SysFont(None,42).render(codigo, True, BLANCO)
            nombre_render = fuente.render(nombre, True, (210,230,255))

            pantalla.blit(
                codigo_render,
                (
                    rect.centerx-codigo_render.get_width()//2,
                    rect.y+18
                )
            )

            pantalla.blit(
                nombre_render,
                (
                    rect.centerx-nombre_render.get_width()//2,
                    rect.y+55
                )
            )

        hover_back = language_back_btn.collidepoint((mx,my))

        if hover_back:
            crear_rect_glow(pantalla,(language_back_btn.x,language_back_btn.y,language_back_btn.w,language_back_btn.h),(80,220,255),70,12)

        pygame.draw.rect(
            pantalla,
            (12,28,50) if not hover_back else (28,65,95),
            language_back_btn,
            border_radius=10
        )
        pygame.draw.rect(
            pantalla,
            (80,180,240) if not hover_back else (120,240,255),
            language_back_btn,
            2,
            border_radius=10
        )

        volver_render = fuente.render(txt("back"), True, BLANCO)
        pantalla.blit(
            volver_render,
            (
                language_back_btn.centerx-volver_render.get_width()//2,
                language_back_btn.centery-volver_render.get_height()//2
            )
        )

        dibujar_admin_panel()
        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="ONLINE_HOST_LOBBY":
        dibujar_fondo_menu_animado(0.8)

        titulo_online = pygame.font.SysFont(None,64).render(txt("host_lobby"), True, BLANCO)
        pantalla.blit(titulo_online,(ANCHO//2 - titulo_online.get_width()//2,65))

        panel = pygame.Rect(105,150,590,300)
        crear_rect_glow(pantalla,(panel.x,panel.y,panel.w,panel.h),(80,180,255),45,16)
        pygame.draw.rect(pantalla,(4,12,28),panel,border_radius=14)
        pygame.draw.rect(pantalla,(80,180,255),panel,2,border_radius=14)

        ip_texto = obtener_ip_local() + ":" + str(NET_PORT)
        ip_render = pygame.font.SysFont(None,56).render(ip_texto, True, (255,230,120))
        pantalla.blit(ip_render,(ANCHO//2 - ip_render.get_width()//2,185))

        if net_connected:
            estado_lobby = txt("host_lobby_ready")
            color_estado = (120,255,180)
        else:
            estado_lobby = txt("host_lobby_wait")
            color_estado = (180,220,255)

        y_texto = dibujar_texto_multilinea(
            pantalla,
            estado_lobby,
            140,
            260,
            520,
            fuente,
            color_estado,
            30
        )

        status_render = fuente_peq.render(net_status if net_status else txt("online_waiting"), True, (210,225,245))
        pantalla.blit(status_render,(ANCHO//2 - status_render.get_width()//2,360))

        hint = fuente_peq.render("ENTER = START WHEN READY | ESC = " + txt("cancel"), True, (255,220,120))
        pantalla.blit(hint,(ANCHO//2 - hint.get_width()//2,410))

        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="ONLINE_JOIN":
        dibujar_fondo_menu_animado(0.8)

        titulo_online = pygame.font.SysFont(None,64).render(txt("online_title"), True, BLANCO)
        pantalla.blit(titulo_online,(ANCHO//2 - titulo_online.get_width()//2,70))

        panel = pygame.Rect(130,180,540,190)
        crear_rect_glow(pantalla,(panel.x,panel.y,panel.w,panel.h),(80,180,255),45,16)
        pygame.draw.rect(pantalla,(4,12,28),panel,border_radius=14)
        pygame.draw.rect(pantalla,(80,180,255),panel,2,border_radius=14)

        prompt = fuente.render(txt("online_join_prompt"), True, (180,220,255))
        pantalla.blit(prompt,(ANCHO//2 - prompt.get_width()//2,210))

        ip_render = pygame.font.SysFont(None,48).render(net_join_ip if net_join_ip else "192.168.x.x", True, BLANCO)
        pantalla.blit(ip_render,(ANCHO//2 - ip_render.get_width()//2,270))

        hint = fuente_peq.render("ENTER = OK | ESC = BACK", True, (255,220,120))
        pantalla.blit(hint,(ANCHO//2 - hint.get_width()//2,335))

        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="ONLINE_CLIENT":
        teclas_cliente = pygame.key.get_pressed()
        enviar_inputs_cliente(teclas_cliente)

        with net_lock:
            frame_raw_local = net_client_frame_raw
            snap = net_client_snapshot

        if frame_raw_local is not None:
            try:
                frame_surface = pygame.image.fromstring(frame_raw_local, (ANCHO, ALTO), "RGB")
                pantalla.blit(frame_surface,(0,0))

                hud_cliente = fuente_peq.render(txt("online_client") + "  |  WASD + ? + habilidades", True, (180,220,255))
                pygame.draw.rect(
                    pantalla,
                    (0,0,0),
                    (
                        ANCHO//2 - hud_cliente.get_width()//2 - 12,
                        8,
                        hud_cliente.get_width()+24,
                        25
                    ),
                    border_radius=8
                )
                pantalla.blit(hud_cliente,(ANCHO//2-hud_cliente.get_width()//2,12))

            except:
                pantalla.fill(NEGRO)
                err = fuente.render(txt("online_joining"), True, BLANCO)
                pantalla.blit(err,(ANCHO//2-err.get_width()//2,260))

        elif snap is None:
            dibujar_fondo_menu_animado(0.55)
            titulo_online = pygame.font.SysFont(None,52).render(net_status if net_status else txt("online_joining"), True, BLANCO)
            pantalla.blit(titulo_online,(ANCHO//2 - titulo_online.get_width()//2,250))

        else:
            # Fallback de emergencia si todavï¿½a no llegan frames.
            pantalla.fill(NEGRO)
            dibujar_fondo_profundo(4,0,0)

            nave1 = pygame.transform.scale(imagen_nave_por_tipo(snap.get("nave_tipo",1)),(50,50))
            nave2 = pygame.transform.scale(imagen_nave_por_tipo(snap.get("nave2_tipo",2)),(50,50))
            pantalla.blit(nave1,(snap.get("nave_x",0),snap.get("nave_y",0)))
            pantalla.blit(nave2,(snap.get("nave2_x",0),snap.get("nave2_y",0)))

            score_render = fuente.render(f"{txt('score')}: {snap.get('score',0)}", True, BLANCO)
            pantalla.blit(score_render,(15,15))

        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"] in WORMHOLE_STATES:
        dibujar_escena_scale0()
        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="BOSS_LOOT":
        dibujar_botin_boss()
        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="PAUSA":
        dibujar_fondo_profundo(nivel_anterior_visual,0,0)
        overlay = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
        overlay.fill((0,0,0,170))
        pantalla.blit(overlay,(0,0))

        titulo_pausa = pygame.font.SysFont(None,76).render("PAUSA", True, BLANCO)
        pantalla.blit(titulo_pausa,(ANCHO//2-titulo_pausa.get_width()//2,205))

        pausa_hint = fuente.render("P / ENTER / ESC = CONTINUAR   |   Q = MENU", True, (200,230,255))
        volumen_hint = fuente.render(f"MUSICA: {int(musica_volumen*100)}%   - / +", True, (255,220,120))
        pantalla.blit(pausa_hint,(ANCHO//2-pausa_hint.get_width()//2,295))
        pantalla.blit(volumen_hint,(ANCHO//2-volumen_hint.get_width()//2,335))

        presentar_frame()
        clock.tick(60)
        continue

    if estado["estado"]=="GAME_OVER":
        dibujar_fondo_menu_animado(0.75)
        overlay = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
        overlay.fill((0,0,0,120))
        pantalla.blit(overlay,(0,0))

        titulo_fin = pygame.font.SysFont(None,76).render("GAME OVER", True, (255,90,90))
        pantalla.blit(titulo_fin,(ANCHO//2-titulo_fin.get_width()//2,150))

        score_fin = fuente.render(f"{txt('score')}: {game_over_score}", True, BLANCO)
        coins_fin = fuente.render(f"+{game_over_coins} {txt('coins')}", True, (255,220,80))
        best_fin = fuente.render(f"{txt('best_score')}: {stats['best_score']}", True, (180,220,255))
        hint_fin = fuente.render("ENTER / SPACE / CLICK", True, (200,230,255))

        pantalla.blit(score_fin,(ANCHO//2-score_fin.get_width()//2,255))
        pantalla.blit(coins_fin,(ANCHO//2-coins_fin.get_width()//2,292))
        pantalla.blit(best_fin,(ANCHO//2-best_fin.get_width()//2,329))
        pantalla.blit(hint_fin,(ANCHO//2-hint_fin.get_width()//2,395))

        presentar_frame()
        clock.tick(60)
        continue

    # =====================
    # LOGICA BASE
    # =====================
    if estado["inv"]>0:
        estado["inv"]-=1

    if estado["rapid"]>0:
        estado["rapid"]-=1

    if estado["double"]>0:
        estado["double"]-=1

    # =====================
    # HABILIDADES DEL JUGADOR - TEMPORIZADORES
    # =====================
    if estado["dash_cd"] > 0:
        estado["dash_cd"] -= 1

    if estado["player_laser_cd"] > 0:
        estado["player_laser_cd"] -= 1

    if estado["pulse_cd"] > 0:
        estado["pulse_cd"] -= 1

    if estado["dash_timer"] > 0:
        estado["dash_timer"] -= 1
        estado["nave_x"] += estado["dash_dir"] * 14
        estado["inv"] = max(estado["inv"], 2)
        particulas_dash(estado["nave_x"], estado["nave_y"], estado["dash_dir"])

    if estado["player_laser"] > 0:
        estado["player_laser"] -= 1
        particulas_laser_jugador(estado["nave_x"]+25, estado["nave_y"])

    if estado["pulse_timer"] > 0:
        estado["pulse_timer"] -= 1
        estado["pulse_radius"] = int((55 - estado["pulse_timer"]) * 4)
        if estado["pulse_timer"] % 4 == 0:
            particulas_pulso(estado["nave_x"]+25, estado["nave_y"]+25, estado["pulse_radius"])

    if estado.get("coop",False):
        if estado["inv2"] > 0:
            estado["inv2"] -= 1

        if estado["dash2_cd"] > 0:
            estado["dash2_cd"] -= 1

        if estado["player_laser2_cd"] > 0:
            estado["player_laser2_cd"] -= 1

        if estado["pulse2_cd"] > 0:
            estado["pulse2_cd"] -= 1

        if estado["dash2_timer"] > 0:
            estado["dash2_timer"] -= 1
            estado["nave2_x"] += estado["dash2_dir"] * 14
            estado["inv2"] = max(estado["inv2"], 2)
            particulas_dash(estado["nave2_x"], estado["nave2_y"], estado["dash2_dir"])

        if estado["player_laser2"] > 0:
            estado["player_laser2"] -= 1
            particulas_laser_jugador(estado["nave2_x"]+21, estado["nave2_y"])

        if estado["pulse2_timer"] > 0:
            estado["pulse2_timer"] -= 1
            estado["pulse2_radius"] = int((55 - estado["pulse2_timer"]) * 4)
            if estado["pulse2_timer"] % 4 == 0:
                particulas_pulso(estado["nave2_x"]+21, estado["nave2_y"]+21, estado["pulse2_radius"])

    # Habilidades del Jugador 2 por red o teclado continuo.
    if estado.get("coop",False):
        if input_p2_activo("p2_dash", teclas):
            if estado["dash2_cd"] <= 0 and estado["dash2_timer"] <= 0:
                if input_p2_activo("p2_move_left", teclas):
                    estado["dash2_dir"] = -1
                elif input_p2_activo("p2_move_right", teclas):
                    estado["dash2_dir"] = 1
                estado["dash2_timer"] = 14
                estado["dash2_cd"] = int((510 if habilidad_comprada("energy_core") else 600) * factor_cooldown())
                estado["inv2"] = max(estado["inv2"], 18)
                shake = 10
                flash = 4
                particulas_dash(estado["nave2_x"], estado["nave2_y"], estado["dash2_dir"])
                reproducir_sfx("dash")

        if input_p2_activo("p2_special_laser", teclas):
            if estado["player_laser2_cd"] <= 0 and estado["player_laser2"] <= 0:
                estado["player_laser2"] = 50
                estado["player_laser2_cd"] = int((935 if habilidad_comprada("energy_core") else 1100) * factor_cooldown())
                shake = 18
                flash = 8
                slowmo = 1
                slowmo_timer = 0
                reproducir_sfx("laser_charge", force=True)

        if input_p2_activo("p2_pulse", teclas):
            if estado["pulse2_cd"] <= 0 and estado["pulse2_timer"] <= 0:
                estado["pulse2_timer"] = 55
                estado["pulse2_radius"] = 0
                estado["pulse2_cd"] = int((1275 if habilidad_comprada("energy_core") else 1500) * factor_cooldown())
                activar_pulso_jugador(estado["nave2_x"]+21, estado["nave2_y"]+21)

        if input_p2_activo("p2_ultimate_overdrive", teclas):
            if overdrive_permitido() and hay_boss_activo() and estado["ultimate_overdrive_cd"] <= 0 and estado["ultimate_overdrive"] <= 0:
                estado["ultimate_overdrive"] = 480
                estado["ultimate_overdrive_tick"] = 0
                estado["ultimate_overdrive_cd"] = int((1920 if habilidad_comprada("ultimate_core") else 2400) * factor_cooldown())
                estado["ultimate_message"] = 90
                estado["ultimate_message_text"] = txt("overdrive_activated")
                estado["inv2"] = max(estado["inv2"], 90)

        if input_p2_activo("p2_ultimate_blackhole", teclas):
            if ultimates_boss_permitidas() and hay_boss_activo() and estado["ultimate_blackhole_cd"] <= 0 and estado["ultimate_blackhole"] <= 0:
                cx, cy = centro_boss_activo()
                estado["ultimate_blackhole"] = 360
                estado["ultimate_blackhole_cd"] = int((2400 if habilidad_comprada("ultimate_core") else 3000) * factor_cooldown())
                estado["ultimate_blackhole_x"] = cx
                estado["ultimate_blackhole_y"] = cy
                estado["ultimate_message"] = 90
                estado["ultimate_message_text"] = txt("black_hole")

        if input_p2_activo("p2_ultimate_orbital", teclas):
            if ultimates_boss_permitidas() and hay_boss_activo() and estado["ultimate_orbital_cd"] <= 0 and estado["ultimate_orbital"] <= 0:
                cx, cy = centro_boss_activo()
                estado["ultimate_orbital"] = 150
                estado["ultimate_orbital_cd"] = int((2880 if habilidad_comprada("ultimate_core") else 3600) * factor_cooldown())
                estado["ultimate_orbital_x"] = cx
                estado["ultimate_message"] = 90
                estado["ultimate_message_text"] = txt("orbital_strike")

    if estado["boss_intro"] > 0:
        cockpit_activa = estado.get("cockpit_scan",{}).get("active",False)
        actualizar_cabina_jugable_boss()
        congelar_ataques_durante_intro_boss()

        if cockpit_activa:
            if pygame.time.get_ticks() % 34 == 0:
                shake = max(shake, 3)
        else:
            estado["boss_intro"] -= 1

            if estado["boss_intro"] % 8 == 0:
                shake = max(shake, 12)

            if estado["boss_intro"] in [120, 80, 40]:
                flash = max(flash, 6)

    # =====================
    # ULTIMATE ATTACKS - TEMPORIZADORES
    # =====================
    if estado["ultimate_overdrive_cd"] > 0:
        estado["ultimate_overdrive_cd"] -= 1

    if estado["ultimate_blackhole_cd"] > 0:
        estado["ultimate_blackhole_cd"] -= 1

    if estado["ultimate_orbital_cd"] > 0:
        estado["ultimate_orbital_cd"] -= 1

    if estado["ultimate_message"] > 0:
        estado["ultimate_message"] -= 1

    if estado.get("cockpit_bonus_timer",0) > 0:
        estado["cockpit_bonus_timer"] -= 1

    if estado.get("cockpit_damage_boost",0) > 0:
        estado["cockpit_damage_boost"] -= 1

    if estado["ultimate_overdrive"] > 0:
        estado["ultimate_overdrive"] -= 1
        estado["ultimate_overdrive_tick"] += 1

        # NERF OVERDRIVE:
        # Mantiene duraciï¿½n y efecto visual, pero ya no activa rapid/double permanente.
        # Hace poco daï¿½o directo al boss, menos que un triple shot normal sostenido.
        if estado["ultimate_overdrive_tick"] % 18 == 0:
            boss_od, tipo_od = obtener_boss_activo()
            if boss_od is not None:
                boss_od["vida"] -= 1

        if estado["ultimate_overdrive"] % 6 == 0:
            particulas_overdrive(estado["nave_x"], estado["nave_y"])

    if estado["ultimate_blackhole"] > 0:
        estado["ultimate_blackhole"] -= 1

        if estado["ultimate_blackhole"] % 3 == 0:
            particulas_black_hole(estado["ultimate_blackhole_x"], estado["ultimate_blackhole_y"])

    if estado["ultimate_orbital"] > 0:
        estado["ultimate_orbital"] -= 1

        if estado["ultimate_orbital"] % 2 == 0:
            particulas_orbital(estado["ultimate_orbital_x"])

    if estado["shield"]>0:
        estado["shield"]-=1

    # combo
    if estado["combo_timer"]>0:
        estado["combo_timer"]-=1
    else:
        estado["combo"]=0

    # =====================
    # NIVELES
    # =====================
    if estado["score"]<15000:
        nivel=1

    elif estado["score"]<45000:
        nivel=2

    elif estado["score"]<85000:
        nivel=3

    elif estado["score"]<280000:
        nivel=4

    elif estado["score"]<520000 or not estado.get("boss_overmind_spawned"):
        if not estado.get("boss_laser_spawned"):
            nivel=4
        else:
            nivel=5

    elif estado["score"]<760000 or not estado.get("boss_rift_spawned"):
        nivel=6

    elif estado["score"]<1050000 or not estado.get("boss_hollow_spawned"):
        nivel=7

    elif estado["score"]<1400000 or not estado.get("boss_sun_eater_spawned"):
        nivel=8

    else:
        nivel=9

    # =====================
    # TRANSICION VISUAL DE NIVEL
    # =====================
    if nivel != nivel_anterior_visual:
        nivel_anterior_visual = nivel
        level_banner = 130
        level_banner_text = f"{txt('level')} {nivel}"
        flash = max(flash, 10)
        shake = max(shake, 14)

        for _ in range(45):
            particulas.append([
                random.randint(0,ANCHO),
                random.randint(0,ALTO),
                random.uniform(-2.5,2.5),
                random.uniform(-2.5,2.5),
                random.randint(18,38)
            ])

    if level_banner > 0:
        level_banner -= 1

    actualizar_wormhole_evento(nivel)
    actualizar_micro_anomalias(nivel)
    actualizar_mision_planeta()
    actualizar_planeta_gameplay(nivel)

    # =====================
    # SPAWN BOSS NORMAL
    # =====================
    if nivel==3 and estado["score"]>=65000 and not estado["boss_spawned"] and estado["boss"] is None:

        estado["boss"]={
            "x":300,
            "y":50,
            "vida":200,
            "dir":1,
            "cool":0
        }

        estado["boss_spawned"]=True
        activar_intro_boss("normal", "ASTEROID COMMANDER", 90)
        slowmo = 1
        slowmo_timer = 0

    # =====================
    # SPAWN BOSS FINAL ACTUAL
    # =====================
    if nivel==4 and not estado["boss_final_spawned"] and estado["boss"] is None and estado["boss_laser"] is None and estado.get("boss_overmind") is None:

        estado["boss_final"]={
            "x":250,
            "y":50,
            "vida":400,
            "dir":1,
            "cool":0
        }

        estado["boss_final_spawned"]=True
        activar_intro_boss("final", "OMEGA DESTROYER", 120)
        shake=25

    # =====================
    # SPAWN NUEVO BOSS LASER
    # =====================
    if nivel==4 and estado["score"]>=200000 and not estado["boss_laser_spawned"] and estado["boss"] is None and estado["boss_final"] is None:

        estado["boss_laser"]={
            "x":250,
            "y":35,
            "vida":650,
            "dir":1,
            "cool":0
        }

        estado["boss_laser_spawned"]=True
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        activar_intro_boss("laser", "LASER OVERLORD", 150)
        shake=35
        flash=12
        slowmo = 1
        slowmo_timer = 0

    # =====================
    # SPAWN BOSS NIVEL 5 - THE OVERMIND
    # =====================
    if nivel==5 and estado["score"]>=430000 and not estado["boss_overmind_spawned"] and estado["boss"] is None and estado["boss_final"] is None and estado["boss_laser"] is None:

        estado["boss_overmind"]={
            "x":295,
            "y":35,
            "vida":750,
            "dir":1,
            "cool":0
        }

        estado["boss_overmind_spawned"]=True
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        estado["void_zones"].clear()
        estado["tentacles"].clear()
        activar_intro_boss("final", "THE OVERMIND", 160)
        shake=40
        flash=18
        slowmo = 1
        slowmo_timer = 0

    # =====================
    # SPAWN BOSS NIVEL 6 - THE RIFT MONARCH
    # =====================
    if nivel==6 and estado["score"]>=720000 and not estado["boss_rift_spawned"] and estado["boss"] is None and estado["boss_final"] is None and estado["boss_laser"] is None and estado.get("boss_overmind") is None:

        estado["boss_rift"]={
            "x":290,
            "y":25,
            "vida":950,
            "dir":1,
            "cool":0,
            "teleport":0
        }

        estado["boss_rift_spawned"]=True
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        estado["rift_attacks"].clear()
        estado["quantum_fields"].clear()
        activar_intro_boss("final", "THE RIFT MONARCH", 170)
        shake=45
        flash=20
        slowmo = 1
        slowmo_timer = 0

    # =====================
    # SPAWN BOSS NIVEL 7 - THE HOLLOW SAINT
    # =====================
    if nivel==7 and estado["score"]>=1040000 and not estado["boss_hollow_spawned"] and not hay_boss_activo():
        estado["boss_hollow"]={"x":285,"y":22,"vida":1150,"dir":1,"cool":0}
        estado["boss_hollow_spawned"]=True
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        estado["abyss_zones"].clear()
        estado["silence_rings"].clear()
        activar_intro_boss("final", "THE HOLLOW SAINT", 175)
        shake=42
        flash=16
        slowmo = 1
        slowmo_timer = 0

    # =====================
    # SPAWN BOSS NIVEL 8 - THE SUN EATER
    # =====================
    if nivel==8 and estado["score"]>=1380000 and not estado["boss_sun_eater_spawned"] and not hay_boss_activo():
        estado["boss_sun_eater"]={"x":285,"y":24,"vida":1300,"dir":1,"cool":0,"angle":0}
        estado["boss_sun_eater_spawned"]=True
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        estado["solar_waves"].clear()
        estado["solar_plates"].clear()
        activar_intro_boss("laser", "THE SUN EATER", 180)
        shake=48
        flash=22
        slowmo = 1
        slowmo_timer = 0

    # =====================
    # SPAWN BOSS NIVEL 9 - EDEN PRIME
    # =====================
    if nivel==9 and estado["score"]>=1750000 and not estado["boss_eden_spawned"] and not hay_boss_activo():
        estado["boss_eden"]={"x":285,"y":20,"vida":1500,"dir":1,"cool":0}
        estado["boss_eden_spawned"]=True
        estado["enemigos"].clear()
        estado["balas_enemigas"].clear()
        estado["eden_roots"].clear()
        estado["crystal_rain"].clear()
        estado["life_pulses"].clear()
        activar_intro_boss("final", "EDEN PRIME", 190)
        shake=52
        flash=24
        slowmo = 1
        slowmo_timer = 0

    # =====================
    # MOVIMIENTO
    # =====================
    # Movimiento completo con WASD
    velocidad_nave = PLAYER_SPEED_SLOWED if estado.get("slow_effect",0)>0 else PLAYER_SPEED_NORMAL

    if estado.get("slow_effect",0)>0:
        estado["slow_effect"]-=1

    if tecla_pulsada(teclas, "move_left"):
        estado["nave_x"]-=velocidad_nave

    if tecla_pulsada(teclas, "move_right"):
        estado["nave_x"]+=velocidad_nave

    if tecla_pulsada(teclas, "move_up"):
        estado["nave_y"]-=velocidad_nave

    if tecla_pulsada(teclas, "move_down"):
        estado["nave_y"]+=velocidad_nave

    if estado["nave_x"] < 0:
        estado["nave_x"] = 0

    limite_nave = ANCHO-int((50 if estado.get("coop",False) else 60)*HD_VISUAL_SCALE)

    if estado["nave_x"] > limite_nave:
        estado["nave_x"] = limite_nave

    # Limites verticales para que la nave no salga de la pantalla
    if estado["nave_y"] < 250:
        estado["nave_y"] = 250

    if estado["nave_y"] > ALTO-int(70*HD_VISUAL_SCALE):
        estado["nave_y"] = ALTO-int(70*HD_VISUAL_SCALE)

    # =====================
    # MOVIMIENTO JUGADOR 2 - COOP LOCAL
    # =====================
    if estado.get("coop",False):
        if input_p2_activo("p2_move_left", teclas):
            estado["nave2_x"]-=velocidad_nave

        if input_p2_activo("p2_move_right", teclas):
            estado["nave2_x"]+=velocidad_nave

        if input_p2_activo("p2_move_up", teclas):
            estado["nave2_y"]-=velocidad_nave

        if input_p2_activo("p2_move_down", teclas):
            estado["nave2_y"]+=velocidad_nave

        if estado["nave2_x"] < 0:
            estado["nave2_x"] = 0

        if estado["nave2_x"] > ANCHO-int(60*HD_VISUAL_SCALE):
            estado["nave2_x"] = ANCHO-int(60*HD_VISUAL_SCALE)

        if estado["nave2_y"] < 250:
            estado["nave2_y"] = 250

        if estado["nave2_y"] > ALTO-int(70*HD_VISUAL_SCALE):
            estado["nave2_y"] = ALTO-int(70*HD_VISUAL_SCALE)

    # =====================
    # ESTELA DE NAVE
    # =====================
    color_estela = color_nave_por_tipo(estado.get("nave_tipo",1))

    intensidad_estela = 18
    if estado.get("dash_timer",0) > 0:
        intensidad_estela = 32
    if estado.get("ultimate_overdrive",0) > 0:
        intensidad_estela = 42

    estelas_nave.append({
        "x":estado["nave_x"]+30,
        "y":estado["nave_y"]+50,
        "vida":intensidad_estela,
        "max":intensidad_estela,
        "color":color_estela,
        "r":18 if intensidad_estela < 30 else 26
    })
    if pygame.time.get_ticks() % 3 == 0:
        emitir_particulas_energia(
            estado["nave_x"]+30,
            estado["nave_y"]+54,
            color_estela,
            2 if estado.get("dash_timer",0) <= 0 else 5,
            2.6 if estado.get("dash_timer",0) <= 0 else 5.5,
            (12,24),
            2
        )
        if estado.get("dash_timer",0) > 0:
            emitir_trazo_luz(
                estado["nave_x"]+30,
                estado["nave_y"]+38,
                estado["nave_x"]+30,
                estado["nave_y"]+62,
                color_estela,
                6,
                2
            )

    if estado.get("coop",False):
        color_estela_2 = color_nave_por_tipo(estado.get("nave2_tipo",2))
        estelas_nave.append({
            "x":estado["nave2_x"]+25,
            "y":estado["nave2_y"]+43,
            "vida":16,
            "max":16,
            "color":color_estela_2,
            "r":15
        })
        if pygame.time.get_ticks() % 4 == 0:
            emitir_particulas_energia(
                estado["nave2_x"]+25,
                estado["nave2_y"]+47,
                color_estela_2,
                2,
                2.2,
                (12,22),
                2
            )
            if estado.get("dash2_timer",0) > 0:
                emitir_trazo_luz(estado["nave2_x"]+25, estado["nave2_y"]+32, estado["nave2_x"]+25, estado["nave2_y"]+55, color_estela_2, 6, 2)

    if len(estelas_nave) > 75:
        estelas_nave.pop(0)

    # =====================
    # DISPARO
    # =====================
    estado["cooldown"]-=1

    cd = int((5 if estado["rapid"]>0 else 10) * factor_cooldown())

    if tecla_pulsada(teclas, "shoot") and estado["cooldown"]<=0:

        estado["balas"].append([
            estado["nave_x"]+25,
            estado["nave_y"]
        ])
        reproducir_sfx("player_shot")
        emitir_particulas_energia(estado["nave_x"]+30, estado["nave_y"]+8, (90,210,255), 5, 2.8, (10,20), 2)
        emitir_chispas_cineticas(estado["nave_x"]+30, estado["nave_y"]+8, (90,190,220), 2, 1.5, (6,10), 1)

        if estado["double"]>0 or habilidad_comprada("triple_shot"):

            estado["balas"].append([
                estado["nave_x"]+10,
                estado["nave_y"]
            ])

            estado["balas"].append([
                estado["nave_x"]+40,
                estado["nave_y"]
            ])

        estado["cooldown"]=cd

    if estado.get("coop",False):
        estado["cooldown2"]-=1

        if input_p2_activo("p2_shoot", teclas) and estado["cooldown2"]<=0:

            estado["balas"].append([
                estado["nave2_x"]+21,
                estado["nave2_y"]
            ])
            reproducir_sfx("player_shot", volumen_extra=0.85)
            emitir_chispas_cineticas(estado["nave2_x"]+25, estado["nave2_y"]+8, (150,100,220), 2, 1.5, (6,10), 1)
            emitir_particulas_energia(estado["nave2_x"]+25, estado["nave2_y"]+8, (150,100,220), 2, 1.8, (8,14), 1)

            if estado["double"]>0 or habilidad_comprada("triple_shot"):
                estado["balas"].append([
                    estado["nave2_x"]+8,
                    estado["nave2_y"]
                ])

                estado["balas"].append([
                    estado["nave2_x"]+34,
                    estado["nave2_y"]
                ])

            estado["cooldown2"]=cd

    for b in estado["balas"]:
        b[1]-=PLAYER_BULLET_SPEED

    estado["balas"]=[
        b for b in estado["balas"]
        if b[1]>0
    ]

    nave_rect = rect_jugador_principal()
    nave2_rect = rect_jugador_2()

    # =====================
    # ENEMIGOS
    # =====================
    if not hay_boss_activo():

        # Control de aparicion por nivel.
        # Cuanto menor es spawn_chance, mï¿½s enemigos aparecen.
        # Los niveles 1-3 ahora tienen mï¿½s ritmo para evitar pausas largas.
        if nivel == 1:
            spawn_chance = 32
            max_enemigos_en_pantalla = 7

        elif nivel == 2:
            spawn_chance = 28
            max_enemigos_en_pantalla = 8

        elif nivel == 3:
            spawn_chance = 34
            max_enemigos_en_pantalla = 7

        elif nivel == 4:
            # Nivel 4: enemigos de lï¿½ser, controlados porque son fuertes.
            spawn_chance = 70
            max_enemigos_en_pantalla = 5

        elif nivel == 5:
            # Nivel 5: The Void Swarm. Enemigos orgï¿½nicos mï¿½s peligrosos.
            spawn_chance = 52
            max_enemigos_en_pantalla = 6

        elif nivel == 6:
            # Nivel 6: Quantum Rift. Menos enemigos, pero controlan mucho el espacio.
            spawn_chance = 48
            max_enemigos_en_pantalla = 6

        elif nivel == 7:
            spawn_chance = 46
            max_enemigos_en_pantalla = 6

        elif nivel == 8:
            spawn_chance = 42
            max_enemigos_en_pantalla = 7

        else:
            spawn_chance = 44
            max_enemigos_en_pantalla = 7

        # Sistema anti-vacï¿½o:
        # Si no hay enemigos en pantalla, aumenta mucho la probabilidad de apariciï¿½n.
        if len(estado["enemigos"]) == 0:
            spawn_chance = max(12, spawn_chance // 3)

        if random.randint(1,spawn_chance)==1 and len(estado["enemigos"]) < max_enemigos_en_pantalla:

            if nivel==1:
                tipo="asteroide"

            elif nivel==2:
                tipo=random.choice([
                    "asteroide",
                    "alien",
                    "zigzag"
                ])

            elif nivel==3:
                tipo=random.choice([
                    "asteroide",
                    "alien",
                    "drone",
                    "zigzag",
                    "crucero",
                    "phantom",
                    "orb",
                    "gravity"
                ])

            elif nivel==4:
                # Nivel 4: enemigos de lï¿½ser.
                tipo=random.choice([
                    "sentinel",
                    "hunter",
                    "void_orb",
                    "laser_satellite"
                ])

            elif nivel==5:
                # Nivel 5: The Void Swarm.
                tipo=random.choice([
                    "parasite",
                    "parasite",
                    "parasite",
                    "hive",
                    "leech_drone"
                ])

            elif nivel==6:
                tipo=random.choice([
                    "rift_splitter",
                    "rift_splitter",
                    "phase_reaper",
                    "chrono_mine"
                ])

            elif nivel==7:
                tipo=random.choice([
                    "abyss_wisp",
                    "abyss_wisp",
                    "null_seeker",
                    "void_lantern"
                ])

            elif nivel==8:
                tipo=random.choice([
                    "solar_mantis",
                    "solar_mantis",
                    "flare_drone",
                    "helio_spire"
                ])

            else:
                tipo=random.choice([
                    "bloom_parasite",
                    "bloom_parasite",
                    "crystal_seraph",
                    "root_hydra"
                ])

            vida=2

            if tipo=="phantom":
                vida=7

            elif tipo=="orb":
                vida=9

            elif tipo=="gravity":
                vida=11

            elif tipo=="sentinel":
                vida=12

            elif tipo=="hunter":
                vida=10

            elif tipo=="void_orb":
                vida=14

            elif tipo=="laser_satellite":
                vida=16

            elif tipo=="parasite":
                vida=5

            elif tipo=="hive":
                vida=22

            elif tipo=="shadow_phantom":
                vida=13

            elif tipo=="leech_drone":
                vida=15

            elif tipo=="rift_splitter":
                vida=18

            elif tipo=="quantum_shard":
                vida=5

            elif tipo=="phase_reaper":
                vida=20

            elif tipo=="chrono_mine":
                vida=16

            elif tipo=="abyss_wisp":
                vida=12

            elif tipo=="null_seeker":
                vida=18

            elif tipo=="void_lantern":
                vida=24

            elif tipo=="solar_mantis":
                vida=16

            elif tipo=="flare_drone":
                vida=17

            elif tipo=="helio_spire":
                vida=28

            elif tipo=="bloom_parasite":
                vida=6

            elif tipo=="crystal_seraph":
                vida=22

            elif tipo=="root_hydra":
                vida=30

            estado["enemigos"].append({
                "tipo":tipo,
                "x":random.randint(0,ANCHO-80),
                "y":-50,
                "vida":vida
            })

    nuevos=[]

    for en in estado["enemigos"]:

        if en.get("hit_flash",0) > 0:
            en["hit_flash"] -= 1

        if en["tipo"]=="asteroide":
            en["y"]+=2

        elif en["tipo"]=="alien":

            en["y"]+=1

            if random.randint(1,80)==1:
                estado["balas_enemigas"].append([
                    en["x"]+25,
                    en["y"]+50
                ])

        elif en["tipo"]=="drone":

            en["y"]+=2
            en["x"]+=(estado["nave_x"]-en["x"])/40

        elif en["tipo"]=="zigzag":

            en["y"]+=2
            en["x"]+=math.sin(en["y"]/20)*4

        elif en["tipo"]=="crucero":
            en["y"]+=1

        elif en["tipo"]=="phantom":

            en["y"]+=3
            en["x"]+=math.sin(en["y"]/10)*5

        elif en["tipo"]=="orb":

            en["y"]+=2

            if random.randint(1,60)==1:
                estado["balas_enemigas"].append([
                    en["x"],
                    en["y"]
                ])

        elif en["tipo"]=="gravity":

            en["y"]+=1
            en["x"]+=(estado["nave_x"]-en["x"])/50

        elif en["tipo"]=="sentinel":

            en.setdefault("cool", 0)
            en.setdefault("laser", 0)

            if en["y"] < 80:
                en["y"] += 1
            else:
                en["cool"] += 1

                if en["cool"] % 150 == 0:
                    en["laser"] = 90
                    shake = 12
                    flash = 4

                if en["laser"] > 0:
                    en["laser"] -= 1

                    if en["laser"] < 45:
                        laser_rect = pygame.Rect(en["x"]+25, en["y"]+55, 18, ALTO-(en["y"]+55))

                        if colisiona_con_jugador(laser_rect) and estado["inv"] <= 0:
                            if estado["shield"] > 0:
                                estado["shield"] = 0
                                reproducir_sfx("shield_hit")
                            else:
                                aplicar_dano_jugador(1)
                                estado["inv"] = 60
                                flash = 10
                                shake = 15

        elif en["tipo"]=="hunter":

            en.setdefault("cool", 0)
            en["cool"] += 1

            en["y"] += 2
            en["x"] += (estado["nave_x"] - en["x"]) / 25

            if en["cool"] % 90 == 0:
                en["y"] += 35
                shake = 8

        elif en["tipo"]=="void_orb":

            en["y"] += 1.2
            en["x"] += math.sin(en["y"]/25)*2

            distancia = abs((en["x"]+35) - (estado["nave_x"]+25))

            if distancia < 120:
                if estado["nave_x"] < en["x"]:
                    estado["nave_x"] += 1
                else:
                    estado["nave_x"] -= 1

        elif en["tipo"]=="laser_satellite":

            en.setdefault("cool", 0)
            en.setdefault("laser", 0)
            en.setdefault("dir", random.choice([-1,1]))

            if en["y"] < 90:
                en["y"] += 1
            else:
                en["x"] += en["dir"] * 2

                if en["x"] < 0 or en["x"] > ANCHO-80:
                    en["dir"] *= -1

                en["cool"] += 1

                if en["cool"] % 180 == 0:
                    en["laser"] = 100
                    shake = 15
                    flash = 5

                if en["laser"] > 0:
                    en["laser"] -= 1

                    if en["laser"] < 50:
                        laser_rect_izq = pygame.Rect(0, en["y"]+15, max(0, int(en["x"])), 30)
                        laser_rect_der = pygame.Rect(int(en["x"]+80), en["y"]+15, max(0, ANCHO-int(en["x"]+80)), 30)

                        if (laser_rect_izq.colliderect(nave_rect) or laser_rect_der.colliderect(nave_rect)) and estado["inv"] <= 0:
                            if estado["shield"] > 0:
                                estado["shield"] = 0
                                reproducir_sfx("shield_hit")
                            else:
                                aplicar_dano_jugador(1)
                                estado["inv"] = 60
                                flash = 12
                                shake = 18

        elif en["tipo"]=="parasite":

            en["y"]+=4
            en["x"]+=(estado["nave_x"]-en["x"])/24

            if random.randint(1,10)==1:
                particulas.append([en["x"]+22,en["y"]+22,random.uniform(-1.5,1.5),random.uniform(-1.5,1.5),random.randint(10,20)])

        elif en["tipo"]=="hive":

            en["y"]+=0.8
            en["x"]+=math.sin(en["y"]/35)*1.2
            en["spawn_cool"]=en.get("spawn_cool",0)+1

            if en["spawn_cool"]%115==0 and len(estado["enemigos"])<9:
                estado["enemigos"].append({
                    "tipo":"parasite",
                    "x":en["x"]+random.randint(-25,25),
                    "y":en["y"]+45,
                    "vida":5
                })

        elif en["tipo"]=="shadow_phantom":

            en["y"]+=2.2
            en["x"]+=math.sin(pygame.time.get_ticks()/230 + en["y"]*0.02)*2.8
            en["phase"]=en.get("phase",random.randint(0,120))+1
            en["invisible"]=(en["phase"]%150)>95

        elif en["tipo"]=="leech_drone":

            en["y"]+=1.8
            en["x"]+=(estado["nave_x"]-en["x"])/45

            if random.randint(1,90)==1:
                estado["balas_enemigas"].append([
                    en["x"]+25,
                    en["y"]+45,
                    "leech"
                ])

        elif en["tipo"]=="rift_splitter":

            en.setdefault("phase", random.uniform(0, 6.28))
            en["y"] += 1.35
            en["x"] += math.sin(en["y"]/28 + en["phase"]) * 2.2

            if random.randint(1,85)==1:
                estado["balas_enemigas"].append([en["x"]+35,en["y"]+40,random.uniform(-1.8,1.8),3.2,"rift"])

        elif en["tipo"]=="quantum_shard":

            en.setdefault("vx", random.choice([-2.3,2.3]))
            en["y"] += 3.1
            en["x"] += en["vx"] + math.sin(en["y"]/16)*1.2

        elif en["tipo"]=="phase_reaper":

            en.setdefault("cool", random.randint(0,80))
            en.setdefault("fade", 0)
            en["cool"] += 1
            en["y"] += 1.45
            en["x"] += math.sin(pygame.time.get_ticks()/250 + en["y"]*0.02)*2.1

            if en["cool"] % 135 == 0:
                en["fade"] = 45
                en["x"] = max(20,min(ANCHO-90,estado["nave_x"] + random.randint(-190,190)))
                en["y"] = max(25,min(ALTO-250,en["y"] + random.randint(35,80)))
                flash = max(flash,4)

            if en.get("fade",0)>0:
                en["fade"]-=1
                en["invisible"] = en["fade"]>18
            else:
                en["invisible"] = False

            if en["cool"] % 95 == 0:
                for dx in [-2.2,0,2.2]:
                    estado["balas_enemigas"].append([en["x"]+35,en["y"]+45,dx,3.4,"rift"])

        elif en["tipo"]=="chrono_mine":

            en.setdefault("pulse", random.randint(0,120))
            en["pulse"] += 1
            en["y"] += 0.85
            en["x"] += math.sin(en["pulse"]/35)*1.3

            campo_rect = pygame.Rect(en["x"]-70,en["y"]-70,200,200)
            if colisiona_con_jugador(campo_rect):
                estado["slow_effect"] = max(estado.get("slow_effect",0), 12)

            if en["pulse"] % 160 == 0:
                estado["quantum_fields"].append({
                    "x":en["x"]+30,
                    "y":en["y"]+30,
                    "r":20,
                    "max":95,
                    "vida":150,
                    "hit":False
                })

        elif en["tipo"]=="abyss_wisp":

            en.setdefault("phase", random.randint(0,160))
            en["phase"] += 1
            en["y"] += 1.15
            en["x"] += math.sin(en["phase"]/22)*2.4
            en["invisible"] = (en["phase"] % 140) > 102
            if colisiona_con_jugador(pygame.Rect(en["x"]-45,en["y"]-45,140,140)):
                estado["slow_effect"] = max(estado.get("slow_effect",0), 10)

        elif en["tipo"]=="null_seeker":

            en.setdefault("charge", random.randint(0,80))
            en["charge"] += 1
            en["y"] += 1.25
            if en["charge"] % 110 < 70:
                en["x"] += (estado["nave_x"] - en["x"]) / 55
            else:
                en["x"] += (estado["nave_x"] - en["x"]) / 18
                en["y"] += 2.2

        elif en["tipo"]=="void_lantern":

            en.setdefault("cool", random.randint(0,100))
            en["cool"] += 1
            if en["y"] < 105:
                en["y"] += 0.85
            else:
                en["x"] += math.sin(en["cool"]/45)*0.8
            if en["cool"] % 180 == 0:
                estado["abyss_zones"].append({"x":en["x"]+35,"y":random.randint(280,ALTO-90),"r":16,"max":58,"vida":170})

        elif en["tipo"]=="solar_mantis":

            en.setdefault("phase", random.uniform(0,6.28))
            en["y"] += 2.6
            en["x"] += math.sin(en["y"]/18 + en["phase"]) * 5
            if random.randint(1,95)==1:
                en["y"] += 42

        elif en["tipo"]=="flare_drone":

            en.setdefault("cool", random.randint(0,70))
            en["cool"] += 1
            en["y"] += 1.2
            en["x"] += math.sin(en["cool"]/30)*1.6
            if en["cool"] % 95 == 0:
                for dx in [-2.8,0,2.8]:
                    estado["balas_enemigas"].append([en["x"]+30,en["y"]+40,dx,3.3,"solar"])

        elif en["tipo"]=="helio_spire":

            en.setdefault("cool", random.randint(0,120))
            en.setdefault("laser", 0)
            if en["y"] < 90:
                en["y"] += 0.8
            else:
                en["cool"] += 1
            if en["cool"] % 170 == 0:
                en["laser"] = 95
            if en["laser"] > 0:
                en["laser"] -= 1
                if en["laser"] < 45:
                    laser_rect = pygame.Rect(en["x"]+25,en["y"]+45,30,ALTO)
                    if colisiona_con_jugador(laser_rect) and estado["inv"]<=0:
                        aplicar_dano_jugador(1)
                        estado["inv"]=60
                        flash=12
                        shake=18

        elif en["tipo"]=="bloom_parasite":

            en["y"] += 2.4
            en["x"] += (estado["nave_x"] - en["x"]) / 34 + math.sin(en["y"]/20)*1.5

        elif en["tipo"]=="crystal_seraph":

            en.setdefault("cool", random.randint(0,90))
            en["cool"] += 1
            en["y"] += 1.25
            en["x"] += math.sin(en["cool"]/42)*2.2
            if en["cool"] % 120 == 0:
                for ang in [60,90,120]:
                    dx=math.cos(math.radians(ang))*2.7
                    dy=math.sin(math.radians(ang))*2.7
                    estado["balas_enemigas"].append([en["x"]+35,en["y"]+45,dx,dy,"eden"])

        elif en["tipo"]=="root_hydra":

            en.setdefault("cool", random.randint(0,140))
            en["cool"] += 1
            en["y"] += 0.75
            en["x"] += math.sin(en["cool"]/55)*1.0
            if en["cool"] % 155 == 0:
                estado["eden_roots"].append({"x":random.randint(50,ANCHO-90),"timer":110,"hit":False,"phase":random.uniform(0,math.pi*2)})

        rect=pygame.Rect(en["x"],en["y"],50,50)

        if en["tipo"] in ["sentinel", "void_orb"]:
            rect=pygame.Rect(en["x"],en["y"],70,70)

        elif en["tipo"]=="hunter":
            rect=pygame.Rect(en["x"],en["y"],65,65)

        elif en["tipo"]=="laser_satellite":
            rect=pygame.Rect(en["x"],en["y"],80,50)

        elif en["tipo"] in ["rift_splitter", "phase_reaper"]:
            rect=pygame.Rect(en["x"],en["y"],70,70)

        elif en["tipo"]=="chrono_mine":
            rect=pygame.Rect(en["x"],en["y"],60,60)

        elif en["tipo"]=="quantum_shard":
            rect=pygame.Rect(en["x"],en["y"],38,38)

        elif en["tipo"] in ["abyss_wisp","bloom_parasite"]:
            rect=pygame.Rect(en["x"],en["y"],45,45)

        elif en["tipo"] in ["null_seeker","solar_mantis","flare_drone","crystal_seraph"]:
            rect=pygame.Rect(en["x"],en["y"],65,65)

        elif en["tipo"] in ["void_lantern","helio_spire","root_hydra"]:
            rect=pygame.Rect(en["x"],en["y"],80,80)

        for b in estado["balas"][:]:

            if rect.collidepoint(b[0],b[1]) and not en.get("invisible", False):

                en["vida"]-=1
                en["hit_flash"] = 5
                color_hit = color_enemigo(en["tipo"])
                emitir_chispas_cineticas(b[0], b[1], color_hit, 7, 4.0, (10,20), 2)
                emitir_particulas_energia(b[0], b[1], color_hit, 4, 2.6, (10,18), 1)
                if random.randint(1, 2) == 1:
                    destellos.append({"x":b[0],"y":b[1],"radio":34,"vida":8,"max":8,"color":color_hit})

                if b in estado["balas"]:
                    estado["balas"].remove(b)

                hitstop=1

        if colisiona_con_jugador(rect):
            if estado["inv"]<=0:
                if estado["shield"]>0:
                    estado["shield"]=0
                    reproducir_sfx("shield_hit")
                else:
                    aplicar_dano_jugador(1)
                    estado["inv"]=60
                    estado["combo"]=0

            puntos_choque = max(25, PUNTOS.get(en["tipo"],100)//2)
            estado["score"] += puntos_choque
            ganar_monedas(max(3,puntos_choque//12))
            registrar_enemigo_destruido()
            reproducir_sfx("metal_hit", volumen_extra=0.9)
            explosion(en["x"],en["y"])
            emitir_particulas_energia(en["x"]+35,en["y"]+35,(255,170,95),18,4.2,(16,30),2)
            flash=max(flash,12)
            shake=max(shake,18)
            hitstop=max(hitstop,3)
            continue

        if en["vida"]<=0:

            estado["score"]+=PUNTOS[en["tipo"]]

            ganar_monedas(PUNTOS[en["tipo"]]//10)
            registrar_enemigo_destruido()

            estado["combo"]+=1
            estado["combo_timer"]=120
            estado["score"]+=estado["combo"]

            if en["tipo"]=="rift_splitter" and len(estado["enemigos"])<10:
                for vx in [-2.4,2.4]:
                    estado["enemigos"].append({
                        "tipo":"quantum_shard",
                        "x":en["x"]+30,
                        "y":en["y"]+25,
                        "vida":5,
                        "vx":vx
                    })

            if en["tipo"]=="bloom_parasite" and len(estado["enemigos"])<10:
                for vx in [-2.0,2.0]:
                    estado["enemigos"].append({
                        "tipo":"bloom_parasite",
                        "x":en["x"]+20,
                        "y":en["y"]+20,
                        "vida":3,
                        "vx":vx
                    })

            explosion(en["x"],en["y"])
            color_dead = color_enemigo(en["tipo"])
            emitir_chispas_cineticas(en["x"]+rect.w//2, en["y"]+rect.h//2, color_dead, 18, 6.2, (16,34), 3)
            ondas_expansion.append({"x":en["x"]+rect.w//2,"y":en["y"]+rect.h//2,"r":10,"vida":18,"max":90,"color":color_dead})

            if random.randint(1,6)==1:

                estado["powerups"].append([
                    en["x"],
                    en["y"],
                    random.choice([
                        "rapid",
                        "double",
                        "shield",
                        "bomb"
                    ])
                ])

        else:
            nuevos.append(en)

    estado["enemigos"]=nuevos

    # =====================
    # BOSS NORMAL
    # =====================
    if estado["boss"]:

        boss=estado["boss"]

        if boss["vida"]>100:
            fase=1

        elif boss["vida"]>40:
            fase=2

        else:
            fase=3

        actualizar_fase_boss_visual("boss", boss, fase)
        speed = 3 if fase==1 else (4 if fase==2 else 6)

        boss["x"]+=boss["dir"]*speed

        if boss["x"]<0 or boss["x"]>ANCHO-150:
            boss["dir"]*=-1

        boss["cool"]+=1

        if fase==1:

            if boss["cool"]%40==0:

                estado["balas_enemigas"].append([
                    boss["x"]+75,
                    boss["y"]+150
                ])

        elif fase==2:

            if boss["cool"]%30==0:

                for i in [-20,0,20]:

                    estado["balas_enemigas"].append([
                        boss["x"]+75+i,
                        boss["y"]+150
                    ])

        elif fase==3:

            if boss["cool"]%50==0:

                for ang in range(0,360,30):

                    dx=math.cos(math.radians(ang))*3
                    dy=math.sin(math.radians(ang))*3

                    estado["balas_enemigas"].append([
                        boss["x"]+75,
                        boss["y"]+75,
                        dx,
                        dy
                    ])

        boss_rect=pygame.Rect(
            boss["x"],
            boss["y"],
            150,
            150
        )

        for b in estado["balas"][:]:

            if boss_rect.collidepoint(b[0],b[1]):

                boss["vida"]-=dano_bala_boss()
                marcar_boss_golpeado(boss)

                if b in estado["balas"]:
                    estado["balas"].remove(b)

                hitstop=2

        if boss["vida"]<=0:

            estado["score"]+=10000

            ganar_monedas(5000)
            registrar_boss_derrotado()
            iniciar_botin_boss("boss")

            explosion(
                boss["x"],
                boss["y"]
            )
            explosion_boss_cinematica(boss["x"]+75,boss["y"]+75,(255,85,70))

            flash=20
            slowmo = 1
            slowmo_timer = 0

            estado["boss"]=None

    # =====================
    # BOSS FINAL
    # =====================
    if estado["boss_final"]:

        boss=estado["boss_final"]

        if boss["vida"]>250:
            fase=1

        elif boss["vida"]>100:
            fase=2

        else:
            fase=3

        actualizar_fase_boss_visual("boss_final", boss, fase)
        boss["x"]+=boss["dir"]*(3+fase)

        if boss["x"]<0 or boss["x"]>ANCHO-170:
            boss["dir"]*=-1

        boss["cool"]+=1

        # =====================
        # FASE 1
        # =====================
        if fase==1:

            # disparo lento
            if boss["cool"]%25==0:

                estado["balas_enemigas"].append([
                    boss["x"]+80,
                    boss["y"]+150,
                    "boss_final"
                ])

        # =====================
        # FASE 2
        # =====================
        elif fase==2:

            # doble disparo
            if boss["cool"]%35==0:

                for i in [-25,25]:

                    estado["balas_enemigas"].append([
                        boss["x"]+80+i,
                        boss["y"]+150,
                        "boss_final"
                    ])

        # =====================
        # FASE 3
        # =====================
        elif fase==3:

            # laser cinematografico
            if boss["cool"]%180==0:

                estado["laser"]=120
                estado["laser_x"]=boss["x"]+85

                shake=25
                flash=8

            # pequeï¿½as rafagas entre lasers
            if boss["cool"]%50==0:

                for i in [-20,20]:

                    estado["balas_enemigas"].append([
                        boss["x"]+80+i,
                        boss["y"]+150,
                        "boss_final"
                    ])

        boss_rect=pygame.Rect(
            boss["x"],
            boss["y"],
            170,
            170
        )

        for b in estado["balas"][:]:

            if boss_rect.collidepoint(b[0],b[1]):

                boss["vida"]-=dano_bala_boss()
                marcar_boss_golpeado(boss)

                if b in estado["balas"]:
                    estado["balas"].remove(b)

                hitstop=2

        if boss["vida"]<=0:

            estado["score"]+=20000

            ganar_monedas(10000)
            registrar_boss_derrotado()
            iniciar_botin_boss("boss_final")

            explosion(
                boss["x"],
                boss["y"]
            )
            explosion_boss_cinematica(boss["x"]+85,boss["y"]+85,(190,70,255))

            flash=30
            slowmo = 1
            slowmo_timer = 0

            estado["boss_final"]=None

    # =====================
    # NUEVO BOSS LASER
    # =====================
    if estado["boss_laser"]:

        boss=estado["boss_laser"]

        if boss["vida"]>430:
            fase=1

        elif boss["vida"]>220:
            fase=2

        else:
            fase=3

        actualizar_fase_boss_visual("boss_laser", boss, fase)
        boss["cool"]+=1

        # movimiento
        if fase==1:
            speed=3
        elif fase==2:
            speed=4
        else:
            speed=5

        boss["x"]+=boss["dir"]*speed

        if boss["x"]<0 or boss["x"]>ANCHO-190:
            boss["dir"]*=-1

        # FASE 1: lasers verticales
        if fase==1:

            if boss["cool"]%160==0:

                estado["laser"]=120
                estado["laser_x"]=boss["x"]+95

                shake=20
                flash=6

        # FASE 2: lasers horizontales
        elif fase==2:

            if boss["cool"]%170==0:

                estado["laser_horizontal"]=120
                estado["laser_y"]=random.choice([220,300,380,460])
                estado["laser_horizontal_color"]=(255,40,40)

                shake=24
                flash=8

            if boss["cool"]%260==0:

                estado["laser"]=120
                estado["laser_x"]=random.randint(80,ANCHO-80)

                shake=20
                flash=6

        # FASE 3: cruz y barridos
        elif fase==3:

            if boss["cool"]%220==0:

                estado["laser_cross"]=130
                estado["laser_cross_x"]=random.randint(90,ANCHO-90)
                estado["laser_cross_y"]=random.choice([240,320,400])

                shake=30
                flash=12
                slowmo = 1
                slowmo_timer = 0

            # Ataque final mï¿½s justo: lï¿½ser fijo, no barrido mï¿½vil.
            if boss["cool"]%360==0 and estado["laser_sweep"]<=0:

                estado["laser_sweep"]=150
                estado["laser_sweep_tipo"]=random.choice(["vertical","horizontal"])
                estado["laser_sweep_dir"]=0

                if estado["laser_sweep_tipo"]=="vertical":
                    estado["laser_sweep_x"]=random.choice([140,260,380,520,660])
                else:
                    estado["laser_sweep_y"]=random.choice([240,320,400,480])

                shake=25
                flash=10
                slowmo = 1
                slowmo_timer = 0

        boss_rect=pygame.Rect(
            boss["x"],
            boss["y"],
            190,
            190
        )

        for b in estado["balas"][:]:

            if boss_rect.collidepoint(b[0],b[1]):

                boss["vida"]-=dano_bala_boss()
                marcar_boss_golpeado(boss)

                if b in estado["balas"]:
                    estado["balas"].remove(b)

                hitstop=2

        if boss["vida"]<=0:

            estado["score"]+=50000

            ganar_monedas(25000)
            registrar_boss_derrotado()
            iniciar_botin_boss("boss_laser")

            explosion(
                boss["x"],
                boss["y"]
            )
            explosion_boss_cinematica(boss["x"]+95,boss["y"]+95,(255,55,55))

            flash=40
            slowmo = 1
            slowmo_timer = 0
            shake=45

            estado["boss_laser"]=None

    # =====================
    # BOSS NIVEL 5 - THE OVERMIND
    # =====================
    if estado.get("boss_overmind"):

        boss=estado.get("boss_overmind")

        if boss["vida"]>500:
            fase=1
        elif boss["vida"]>230:
            fase=2
        else:
            fase=3

        actualizar_fase_boss_visual("boss_overmind", boss, fase)
        boss["x"] += boss["dir"]*(1.2+fase*0.4)

        if boss["x"]<120 or boss["x"]>ANCHO-330:
            boss["dir"]*=-1

        boss["cool"]+=1

        # Fase 1: invocador orgï¿½nico
        if fase==1:
            if boss["cool"]%105==0 and len(estado["enemigos"])<5:
                estado["enemigos"].append({
                    "tipo":"parasite",
                    "x":boss["x"]+random.randint(20,160),
                    "y":boss["y"]+150,
                    "vida":5
                })

        # Fase 2: zonas corruptas
        elif fase==2:
            if boss["cool"]%120==0:
                estado["void_zones"].append({
                    "x":random.randint(60,ANCHO-160),
                    "y":random.randint(250,ALTO-110),
                    "r":20,
                    "max":random.randint(75,110),
                    "vida":260
                })
                shake=max(shake,15)

            if boss["cool"]%50==0:
                for i in [-45,0,45]:
                    estado["balas_enemigas"].append([boss["x"]+105+i,boss["y"]+170,"boss_final"])

        # Fase 3: tentï¿½culos
        else:
            if boss["cool"]%85==0:
                estado["tentacles"].append(crear_tentaculo_animado(random.randint(40,ANCHO-80)))
                shake=max(shake,20)

            if boss["cool"]%65==0 and len(estado["enemigos"])<9:
                estado["enemigos"].append({
                    "tipo":random.choice(["parasite","parasite","leech_drone"]),
                    "x":random.randint(0,ANCHO-80),
                    "y":-60,
                    "vida":8
                })

        # Daï¿½o de balas del jugador al boss
        boss_rect=pygame.Rect(boss["x"],boss["y"],210,210)

        for b in estado["balas"][:]:
            if boss_rect.collidepoint(b[0],b[1]):
                boss["vida"]-=dano_bala_boss()
                marcar_boss_golpeado(boss)
                estado["balas"].remove(b)
                hitstop=2

        if boss["vida"]<=0:
            estado["score"]+=80000
            ganar_monedas(35000)
            registrar_boss_derrotado()
            iniciar_botin_boss("boss_overmind")
            explosion(boss["x"]+105,boss["y"]+105)
            explosion_boss_cinematica(boss["x"]+105,boss["y"]+105,(185,45,255))
            flash=35
            shake=45
            slowmo = 1
            slowmo_timer = 0
            estado["boss_overmind"]=None
            estado["void_zones"].clear()
            estado["tentacles"].clear()

    # =====================
    # BOSS NIVEL 6 - THE RIFT MONARCH
    # =====================
    if estado.get("boss_rift"):

        boss=estado.get("boss_rift")

        if boss["vida"]>650:
            fase=1
        elif boss["vida"]>300:
            fase=2
        else:
            fase=3

        actualizar_fase_boss_visual("boss_rift", boss, fase)
        boss["x"] += boss["dir"]*(1.6+fase*0.55)

        if boss["x"]<90 or boss["x"]>ANCHO-310:
            boss["dir"]*=-1

        boss["cool"]+=1

        # Fase 1: cuchillas dimensionales
        if fase==1:
            if boss["cool"]%88==0:
                estado["rift_attacks"].append({"tipo":"v","x":random.randint(70,ANCHO-70),"timer":80,"hit":False})
                shake=max(shake,12)

            if boss["cool"]%120==0:
                for dx in [-2.8,0,2.8]:
                    estado["balas_enemigas"].append([boss["x"]+110,boss["y"]+165,dx,3.6,"rift"])

        # Fase 2: teletransporte cuï¿½ntico
        elif fase==2:
            if boss["cool"]%115==0:
                old_x=boss["x"]+110
                boss["x"]=random.choice([90,290,500])
                estado["quantum_fields"].append({"x":old_x,"y":boss["y"]+120,"r":25,"max":110,"vida":190,"hit":False})
                flash=max(flash,8)
                shake=max(shake,20)

            if boss["cool"]%48==0:
                for ang in range(210,331,30):
                    dx=math.cos(math.radians(ang))*3.1
                    dy=math.sin(math.radians(ang))*3.1
                    estado["balas_enemigas"].append([boss["x"]+110,boss["y"]+125,dx,abs(dy)+1.8,"rift"])

        # Fase 3: colapso temporal
        else:
            if boss["cool"]%155==0:
                for _ in range(3):
                    estado["rift_attacks"].append({"tipo":random.choice(["v","h"]),"x":random.randint(80,ANCHO-80),"y":random.randint(260,ALTO-90),"timer":90,"hit":False})
                slowmo = 1
                slowmo_timer = 0
                shake=max(shake,25)

            if boss["cool"]%95==0:
                estado["quantum_fields"].append({"x":random.randint(80,ANCHO-80),"y":random.randint(270,ALTO-80),"r":25,"max":115,"vida":175,"hit":False})

            if boss["cool"]%55==0:
                for i in [-70,-35,0,35,70]:
                    estado["balas_enemigas"].append([boss["x"]+110+i,boss["y"]+175,0,3.8,"rift"])

        boss_rect=pygame.Rect(boss["x"],boss["y"],220,220)

        for b in estado["balas"][:]:
            if boss_rect.collidepoint(b[0],b[1]):
                boss["vida"]-=dano_bala_boss()
                marcar_boss_golpeado(boss)
                if b in estado["balas"]:
                    estado["balas"].remove(b)
                hitstop=2

        if boss["vida"]<=0:
            estado["score"]+=120000
            ganar_monedas(50000)
            registrar_boss_derrotado()
            iniciar_botin_boss("boss_rift")
            explosion(boss["x"]+110,boss["y"]+110)
            explosion_boss_cinematica(boss["x"]+110,boss["y"]+110,(80,225,255))
            flash=45
            shake=55
            slowmo = 1
            slowmo_timer = 0
            estado["boss_rift"]=None
            estado["rift_attacks"].clear()
            estado["quantum_fields"].clear()

    # =====================
    # BOSS NIVEL 7 - THE HOLLOW SAINT
    # =====================
    if estado.get("boss_hollow"):
        boss=estado["boss_hollow"]
        fase = 1 if boss["vida"]>760 else (2 if boss["vida"]>360 else 3)
        actualizar_fase_boss_visual("boss_hollow", boss, fase)
        boss["cool"]+=1
        boss["x"] += boss["dir"]*(1.0+fase*0.35)
        if boss["x"]<95 or boss["x"]>ANCHO-325:
            boss["dir"]*=-1

        if boss["cool"]%110==0:
            estado["silence_rings"].append({"x":boss["x"]+115,"y":boss["y"]+120,"r":18,"vida":105,"hit":False})
        if boss["cool"]%(150 if fase<3 else 105)==0:
            estado["laser"]=120
            estado["laser_x"]=boss["x"]+115
            shake=max(shake,20)
        if fase>=2 and boss["cool"]%125==0:
            estado["abyss_zones"].append({"x":random.randint(70,ANCHO-70),"y":random.randint(270,ALTO-85),"r":16,"max":64,"vida":170})
        if fase==3 and boss["cool"]%70==0:
            for dx in [-2.4,0,2.4]:
                estado["balas_enemigas"].append([boss["x"]+115,boss["y"]+170,dx,3.4,"abyss"])

        boss_rect=pygame.Rect(boss["x"],boss["y"],230,230)
        for b in estado["balas"][:]:
            if boss_rect.collidepoint(b[0],b[1]):
                boss["vida"]-=dano_bala_boss()
                marcar_boss_golpeado(boss)
                if b in estado["balas"]:
                    estado["balas"].remove(b)
                hitstop=2
        if boss["vida"]<=0:
            estado["score"]+=150000
            ganar_monedas(65000)
            registrar_boss_derrotado()
            iniciar_botin_boss("boss_hollow")
            estado["hp"]=estado.get("max_hp",hp_maximo_jugador())
            estado["vidas"]=estado["hp"]
            explosion(boss["x"]+115,boss["y"]+115)
            explosion_boss_cinematica(boss["x"]+115,boss["y"]+115,(40,220,255))
            flash=45
            shake=36
            slowmo = 1
            slowmo_timer = 0
            estado["boss_hollow"]=None
            estado["abyss_zones"].clear()
            estado["silence_rings"].clear()

    # =====================
    # BOSS NIVEL 8 - THE SUN EATER
    # =====================
    if estado.get("boss_sun_eater"):
        boss=estado["boss_sun_eater"]
        fase = 1 if boss["vida"]>860 else (2 if boss["vida"]>430 else 3)
        actualizar_fase_boss_visual("boss_sun_eater", boss, fase)
        boss["cool"]+=1
        boss["angle"] = boss.get("angle",0) + 0.045
        boss["x"] += boss["dir"]*(1.4+fase*0.35)
        if boss["x"]<90 or boss["x"]>ANCHO-320:
            boss["dir"]*=-1

        if boss["cool"]%95==0:
            estado["solar_waves"].append({"y":random.choice([265,330,395,460]),"timer":115,"hit":False})
        if boss["cool"]%(160 if fase<3 else 115)==0:
            estado["laser_horizontal"]=120
            estado["laser_y"]=random.choice([260,330,400,470])
            estado["laser_horizontal_color"]=(255,205,45)
            shake=max(shake,24)
        if boss["cool"]%70==0:
            for i in [-70,-35,0,35,70]:
                estado["balas_enemigas"].append([boss["x"]+115+i,boss["y"]+170,0,3.9,"solar"])

        boss_rect=pygame.Rect(boss["x"],boss["y"],230,230)
        for b in estado["balas"][:]:
            if boss_rect.collidepoint(b[0],b[1]):
                boss["vida"]-=dano_bala_boss()
                marcar_boss_golpeado(boss)
                if b in estado["balas"]:
                    estado["balas"].remove(b)
                hitstop=2
        if boss["vida"]<=0:
            estado["score"]+=190000
            ganar_monedas(80000)
            registrar_boss_derrotado()
            iniciar_botin_boss("boss_sun_eater")
            estado["hp"]=estado.get("max_hp",hp_maximo_jugador())
            estado["vidas"]=estado["hp"]
            explosion(boss["x"]+115,boss["y"]+115)
            explosion_boss_cinematica(boss["x"]+115,boss["y"]+115,(255,165,40))
            flash=55
            shake=40
            slowmo = 1
            slowmo_timer = 0
            estado["boss_sun_eater"]=None
            estado["solar_waves"].clear()

    # =====================
    # BOSS NIVEL 9 - EDEN PRIME
    # =====================
    if estado.get("boss_eden"):
        boss=estado["boss_eden"]
        fase = 1 if boss["vida"]>1000 else (2 if boss["vida"]>480 else 3)
        actualizar_fase_boss_visual("boss_eden", boss, fase)
        boss["cool"]+=1
        boss["x"] += boss["dir"]*(1.1+fase*0.45)
        if boss["x"]<85 or boss["x"]>ANCHO-320:
            boss["dir"]*=-1

        if boss["cool"]%95==0:
            estado["eden_roots"].append({"x":random.randint(45,ANCHO-90),"timer":120,"hit":False,"phase":random.uniform(0,math.pi*2)})
        if boss["cool"]%120==0:
            estado["life_pulses"].append({"x":boss["x"]+115,"y":boss["y"]+125,"r":18,"vida":100,"hit":False})
        if boss["cool"]%55==0:
            for dx in [-3,-1.5,0,1.5,3]:
                estado["crystal_rain"].append([boss["x"]+115+random.randint(-90,90),boss["y"]+165,dx,3.5])
        if fase==3 and boss["cool"]%170==0:
            estado["laser"]=125
            estado["laser_x"]=boss["x"]+115

        boss_rect=pygame.Rect(boss["x"],boss["y"],230,230)
        for b in estado["balas"][:]:
            if boss_rect.collidepoint(b[0],b[1]):
                boss["vida"]-=dano_bala_boss()
                marcar_boss_golpeado(boss)
                if b in estado["balas"]:
                    estado["balas"].remove(b)
                hitstop=2
        if boss["vida"]<=0:
            estado["score"]+=250000
            ganar_monedas(120000)
            registrar_boss_derrotado()
            iniciar_botin_boss("boss_eden")
            estado["hp"]=estado.get("max_hp",hp_maximo_jugador())
            estado["vidas"]=estado["hp"]
            explosion(boss["x"]+115,boss["y"]+115)
            explosion_boss_cinematica(boss["x"]+115,boss["y"]+115,(90,255,180))
            flash=65
            shake=44
            slowmo = 1
            slowmo_timer = 0
            estado["boss_eden"]=None
            estado["eden_roots"].clear()
            estado["crystal_rain"].clear()
            estado["life_pulses"].clear()

    # =====================
    # RIFT ATTACKS Y QUANTUM FIELDS
    # =====================
    nuevas_rift=[]

    for r in estado.get("rift_attacks",[]):
        r["timer"]-=1

        if r.get("tipo")=="v":
            attack_rect=pygame.Rect(r.get("x",ANCHO//2)-22,0,44,ALTO)
        else:
            attack_rect=pygame.Rect(0,r.get("y",ALTO//2)-22,ANCHO,44)

        if r["timer"]<42 and not r.get("hit",False) and colisiona_con_jugador(attack_rect) and estado["inv"]<=0:
            r["hit"]=True
            if estado["shield"]>0:
                estado["shield"]=0
                reproducir_sfx("shield_hit")
            else:
                aplicar_dano_jugador(1)
                estado["inv"]=60
                flash=14
                shake=25

        if r["timer"]>0:
            nuevas_rift.append(r)

    estado["rift_attacks"]=nuevas_rift

    nuevas_q=[]

    for q in estado.get("quantum_fields",[]):
        q["vida"]-=1
        if q["r"]<q["max"]:
            q["r"]+=2

        field_rect=pygame.Rect(q["x"]-q["r"],q["y"]-q["r"],q["r"]*2,q["r"]*2)

        if colisiona_con_jugador(field_rect):
            estado["slow_effect"]=max(estado.get("slow_effect",0),18)
            if q["vida"]%35==0 and estado["inv"]<=0:
                aplicar_dano_jugador(0.5)
                estado["inv"]=35
                flash=8

        if q["vida"]>0:
            nuevas_q.append(q)

    estado["quantum_fields"]=nuevas_q

    # =====================
    # NIVEL 7-9: CAMPOS, ANILLOS, OLAS Y RAICES
    # =====================
    nuevas_abyss=[]
    for z in estado.get("abyss_zones",[]):
        z["vida"]-=1
        if z["r"]<z["max"]:
            z["r"]+=2
        zona_rect=pygame.Rect(z["x"]-z["r"],z["y"]-z["r"],z["r"]*2,z["r"]*2)
        if colisiona_con_jugador(zona_rect):
            estado["slow_effect"]=max(estado.get("slow_effect",0),22)
            if z["vida"]%45==0 and estado["inv"]<=0:
                aplicar_dano_jugador(1)
                estado["inv"]=35
        if z["vida"]>0:
            nuevas_abyss.append(z)
    estado["abyss_zones"]=nuevas_abyss

    nuevas_rings=[]
    for r in estado.get("silence_rings",[]):
        r["vida"]-=1
        r["r"]+=2
        dist=math.hypot((estado["nave_x"]+25)-r["x"],(estado["nave_y"]+25)-r["y"])
        if abs(dist-r["r"])<18 and not r.get("hit",False) and estado["inv"]<=0:
            r["hit"]=True
            aplicar_dano_jugador(1)
            estado["inv"]=55
            estado["slow_effect"]=max(estado.get("slow_effect",0),50)
        if r["vida"]>0 and r["r"]<260:
            nuevas_rings.append(r)
    estado["silence_rings"]=nuevas_rings

    nuevas_waves=[]
    for w in estado.get("solar_waves",[]):
        w["timer"]-=1
        wave_rect=pygame.Rect(0,w["y"]-18,ANCHO,36)
        if w["timer"]<65 and not w.get("hit",False) and colisiona_con_jugador(wave_rect) and estado["inv"]<=0:
            w["hit"]=True
            aplicar_dano_jugador(1)
            estado["inv"]=55
            flash=12
        if w["timer"]>0:
            nuevas_waves.append(w)
    estado["solar_waves"]=nuevas_waves

    nuevas_roots=[]
    for root in estado.get("eden_roots",[]):
        root["timer"]-=1
        root_rect=pygame.Rect(root["x"],ALTO-230,65,230)
        if root["timer"]<62 and not root.get("hit",False) and colisiona_con_jugador(root_rect) and estado["inv"]<=0:
            root["hit"]=True
            aplicar_dano_jugador(1)
            estado["inv"]=60
            flash=10
        if root["timer"]>0:
            nuevas_roots.append(root)
    estado["eden_roots"]=nuevas_roots

    nuevas_rain=[]
    for c in estado.get("crystal_rain",[]):
        c[0]+=c[2]
        c[1]+=c[3]
        if punto_colisiona_jugador(c[0],c[1]) and estado["inv"]<=0:
            aplicar_dano_jugador(1)
            estado["inv"]=50
            flash=8
        elif -60<c[0]<ANCHO+60 and -60<c[1]<ALTO+80:
            nuevas_rain.append(c)
    estado["crystal_rain"]=nuevas_rain

    nuevas_pulses=[]
    for p in estado.get("life_pulses",[]):
        p["vida"]-=1
        p["r"]+=2
        dist=math.hypot((estado["nave_x"]+25)-p["x"],(estado["nave_y"]+25)-p["y"])
        if abs(dist-p["r"])<16 and not p.get("hit",False) and estado["inv"]<=0:
            p["hit"]=True
            aplicar_dano_jugador(1)
            estado["inv"]=50
        if p["vida"]>0 and p["r"]<250:
            nuevas_pulses.append(p)
    estado["life_pulses"]=nuevas_pulses

    # =====================
    # VOID ZONES Y TENTACULOS
    # =====================
    nuevas_void=[]

    for z in estado["void_zones"]:
        z["vida"]-=1
        if z["r"]<z["max"]:
            z["r"]+=2

        zona_rect=pygame.Rect(z["x"]-z["r"],z["y"]-z["r"],z["r"]*2,z["r"]*2)

        if colisiona_con_jugador(zona_rect) and estado["inv"]<=0:
            if random.randint(1,22)==1:
                aplicar_dano_jugador(1)
                estado["inv"]=45
                flash=12
                shake=15

        if z["vida"]>0:
            nuevas_void.append(z)

    estado["void_zones"]=nuevas_void

    nuevas_tent=[]

    for t in estado["tentacles"]:
        t["timer"]-=1

        tent_rect=pygame.Rect(t["x"],ALTO-230,65,230)

        if t["timer"]<72 and t["timer"]>25 and not t["hit"] and colisiona_con_jugador(tent_rect) and estado["inv"]<=0:
            t["hit"]=True
            aplicar_dano_jugador(1)
            estado["inv"]=60
            flash=14
            shake=25

        if t["timer"]>0:
            nuevas_tent.append(t)

    estado["tentacles"]=nuevas_tent

    # =====================
    # BALAS ENEMIGAS
    # =====================
    nuevas=[]

    for b in estado["balas_enemigas"]:

        # balas con velocidad dx/dy, por ejemplo [x,y,dx,dy] o [x,y,dx,dy,"boss_final"]
        if len(b)>=4 and isinstance(b[2], (int,float)) and isinstance(b[3], (int,float)):

            b[0]+=b[2]
            b[1]+=b[3]

        else:
            b[1]+=5

        if punto_colisiona_jugador(b[0],b[1]) and estado["inv"]<=0:

            if "leech" in b:
                estado["slow_effect"]=180
                flash=8
                shake=8

            elif estado["shield"]>0:
                estado["shield"]=0
                reproducir_sfx("shield_hit")

            else:
                aplicar_dano_jugador(1)
                estado["inv"]=60
                flash=10

        else:
            if -100 < b[0] < ANCHO+100 and -100 < b[1] < ALTO+100:
                nuevas.append(b)

    # =====================
    # SUPERLASER DEL JUGADOR
    # =====================
    if estado["player_laser"] > 0:

        laser_jugador_rect = pygame.Rect(
            estado["nave_x"]+2,
            0,
            56,
            estado["nave_y"]
        )

        nuevos_enemigos_laser=[]

        for en in estado["enemigos"]:

            rect_enemigo = pygame.Rect(en["x"], en["y"], 60, 60)

            if en["tipo"] in ["sentinel", "void_orb"]:
                rect_enemigo = pygame.Rect(en["x"], en["y"], 70, 70)

            elif en["tipo"]=="hunter":
                rect_enemigo = pygame.Rect(en["x"], en["y"], 65, 65)

            elif en["tipo"]=="laser_satellite":
                rect_enemigo = pygame.Rect(en["x"], en["y"], 80, 50)

            if laser_jugador_rect.colliderect(rect_enemigo):
                en["vida"] -= 1

            if en["vida"] > 0:
                nuevos_enemigos_laser.append(en)
            else:
                estado["score"] += PUNTOS.get(en["tipo"], 1000)
                registrar_enemigo_destruido()
                ganar_monedas(PUNTOS.get(en["tipo"], 1000)//10)
                explosion(en["x"], en["y"])

        estado["enemigos"] = nuevos_enemigos_laser

        if estado["boss"]:
            boss_rect_temp = pygame.Rect(estado["boss"]["x"], estado["boss"]["y"], 150, 150)
            if laser_jugador_rect.colliderect(boss_rect_temp):
                estado["boss"]["vida"] -= 1

        if estado["boss_final"]:
            boss_rect_temp = pygame.Rect(estado["boss_final"]["x"], estado["boss_final"]["y"], 170, 170)
            if laser_jugador_rect.colliderect(boss_rect_temp):
                estado["boss_final"]["vida"] -= 1

        if estado["boss_laser"]:
            boss_rect_temp = pygame.Rect(estado["boss_laser"]["x"], estado["boss_laser"]["y"], 190, 190)
            if laser_jugador_rect.colliderect(boss_rect_temp):
                estado["boss_laser"]["vida"] -= 1

        if estado.get("boss_overmind"):
            boss_rect_temp = pygame.Rect(estado["boss_overmind"]["x"], estado["boss_overmind"]["y"], 210, 210)
            if laser_jugador_rect.colliderect(boss_rect_temp):
                estado["boss_overmind"]["vida"] -= 1

        if estado.get("boss_rift"):
            boss_rect_temp = pygame.Rect(estado["boss_rift"]["x"], estado["boss_rift"]["y"], 220, 220)
            if laser_jugador_rect.colliderect(boss_rect_temp):
                estado["boss_rift"]["vida"] -= 1

        for boss_key in ["boss_hollow","boss_sun_eater","boss_eden"]:
            if estado.get(boss_key):
                boss_rect_temp = pygame.Rect(estado[boss_key]["x"], estado[boss_key]["y"], 230, 230)
                if laser_jugador_rect.colliderect(boss_rect_temp):
                    estado[boss_key]["vida"] -= 1

    estado["balas_enemigas"]=nuevas

    # =====================
    # SUPERLASER DEL JUGADOR 2
    # =====================
    if estado.get("coop",False) and estado.get("player_laser2",0) > 0:

        laser_jugador2_rect = pygame.Rect(
            estado["nave2_x"]+2,
            0,
            48,
            estado["nave2_y"]
        )

        nuevos_enemigos_laser2=[]

        for en in estado["enemigos"]:

            rect_enemigo = pygame.Rect(en["x"], en["y"], 60, 60)

            if en["tipo"] in ["sentinel", "void_orb"]:
                rect_enemigo = pygame.Rect(en["x"], en["y"], 70, 70)

            elif en["tipo"]=="hunter":
                rect_enemigo = pygame.Rect(en["x"], en["y"], 65, 65)

            elif en["tipo"]=="laser_satellite":
                rect_enemigo = pygame.Rect(en["x"], en["y"], 80, 50)

            if laser_jugador2_rect.colliderect(rect_enemigo):
                en["vida"] -= 1

            if en["vida"] > 0:
                nuevos_enemigos_laser2.append(en)
            else:
                estado["score"] += PUNTOS.get(en["tipo"], 1000)
                registrar_enemigo_destruido()
                ganar_monedas(PUNTOS.get(en["tipo"], 1000)//10)
                explosion(en["x"], en["y"])

        estado["enemigos"] = nuevos_enemigos_laser2

        if estado["boss"]:
            boss_rect_temp = pygame.Rect(estado["boss"]["x"], estado["boss"]["y"], 150, 150)
            if laser_jugador2_rect.colliderect(boss_rect_temp):
                estado["boss"]["vida"] -= 1

        if estado["boss_final"]:
            boss_rect_temp = pygame.Rect(estado["boss_final"]["x"], estado["boss_final"]["y"], 170, 170)
            if laser_jugador2_rect.colliderect(boss_rect_temp):
                estado["boss_final"]["vida"] -= 1

        if estado["boss_laser"]:
            boss_rect_temp = pygame.Rect(estado["boss_laser"]["x"], estado["boss_laser"]["y"], 190, 190)
            if laser_jugador2_rect.colliderect(boss_rect_temp):
                estado["boss_laser"]["vida"] -= 1

        if estado.get("boss_overmind"):
            boss_rect_temp = pygame.Rect(estado["boss_overmind"]["x"], estado["boss_overmind"]["y"], 210, 210)
            if laser_jugador2_rect.colliderect(boss_rect_temp):
                estado["boss_overmind"]["vida"] -= 1

        if estado.get("boss_rift"):
            boss_rect_temp = pygame.Rect(estado["boss_rift"]["x"], estado["boss_rift"]["y"], 220, 220)
            if laser_jugador2_rect.colliderect(boss_rect_temp):
                estado["boss_rift"]["vida"] -= 1

        for boss_key in ["boss_hollow","boss_sun_eater","boss_eden"]:
            if estado.get(boss_key):
                boss_rect_temp = pygame.Rect(estado[boss_key]["x"], estado[boss_key]["y"], 230, 230)
                if laser_jugador2_rect.colliderect(boss_rect_temp):
                    estado[boss_key]["vida"] -= 1


    # =====================
    # LASER VERTICAL
    # =====================
    if estado["laser"]>0:

        if estado["laser"]<60:

            laser_rect=pygame.Rect(
                estado["laser_x"]-25,
                0,
                50,
                ALTO
            )

            if colisiona_con_jugador(laser_rect):

                if estado["inv"]<=0:

                    if estado["shield"]>0:
                        estado["shield"]=0
                        reproducir_sfx("shield_hit")

                    else:
                        aplicar_dano_jugador(1)
                        estado["inv"]=60
                        flash=15
                        shake=20

    # =====================
    # LASER HORIZONTAL
    # =====================
    if estado["laser_horizontal"]>0:

        if estado["laser_horizontal"]<60:

            laser_rect=pygame.Rect(
                0,
                estado["laser_y"]-25,
                ANCHO,
                50
            )

            if colisiona_con_jugador(laser_rect):

                if estado["inv"]<=0:

                    if estado["shield"]>0:
                        estado["shield"]=0
                        reproducir_sfx("shield_hit")

                    else:
                        aplicar_dano_jugador(1)
                        estado["inv"]=60
                        flash=15
                        shake=20

    # =====================
    # CROSS LASER
    # =====================
    if estado["laser_cross"]>0:

        if estado["laser_cross"]<65:

            rect_v=pygame.Rect(
                estado["laser_cross_x"]-25,
                0,
                50,
                ALTO
            )

            rect_h=pygame.Rect(
                0,
                estado["laser_cross_y"]-25,
                ANCHO,
                50
            )

            if (rect_v.colliderect(nave_rect) or rect_h.colliderect(nave_rect)) and estado["inv"]<=0:

                if estado["shield"]>0:
                    estado["shield"]=0
                    reproducir_sfx("shield_hit")

                else:
                    aplicar_dano_jugador(1)
                    estado["inv"]=60
                    flash=18
                    shake=25

    # =====================
    # LASER FIJO ESPECIAL DEL BOSS LASER
    # =====================
    if estado["laser_sweep"]>0:

        if estado["laser_sweep_tipo"]=="vertical":

            if estado["laser_sweep"]<90:

                laser_rect=pygame.Rect(
                    estado["laser_sweep_x"]-22,
                    0,
                    44,
                    ALTO
                )

                if colisiona_con_jugador(laser_rect) and estado["inv"]<=0:

                    if estado["shield"]>0:
                        estado["shield"]=0
                        reproducir_sfx("shield_hit")

                    else:
                        aplicar_dano_jugador(1)
                        estado["inv"]=60
                        flash=16
                        shake=22

        else:

            if estado["laser_sweep"]<90:

                laser_rect=pygame.Rect(
                    0,
                    estado["laser_sweep_y"]-22,
                    ANCHO,
                    44
                )

                if colisiona_con_jugador(laser_rect) and estado["inv"]<=0:

                    if estado["shield"]>0:
                        estado["shield"]=0
                        reproducir_sfx("shield_hit")

                    else:
                        aplicar_dano_jugador(1)
                        estado["inv"]=60
                        flash=16
                        shake=22

    # =====================
    # ULTIMATE ATTACKS - LOGICA Y DAï¿½O
    # =====================

    if estado["ultimate_blackhole"] > 0:

        cx = estado["ultimate_blackhole_x"]
        cy = estado["ultimate_blackhole_y"]
        radio = 230

        nuevas_balas_blackhole=[]

        for b in estado["balas_enemigas"]:
            dist = math.hypot(b[0]-cx, b[1]-cy)

            if dist < radio:
                b[0] += (cx-b[0]) / 14
                b[1] += (cy-b[1]) / 14

                if dist > 28:
                    nuevas_balas_blackhole.append(b)
            else:
                nuevas_balas_blackhole.append(b)

        estado["balas_enemigas"] = nuevas_balas_blackhole

        nuevos_enemigos_blackhole=[]

        for en in estado["enemigos"]:
            ex = en["x"] + 35
            ey = en["y"] + 35
            dist = math.hypot(ex-cx, ey-cy)

            if dist < radio:
                en["x"] += (cx-ex) / 18
                en["y"] += (cy-ey) / 18

                if estado["ultimate_blackhole"] % 12 == 0:
                    en["vida"] -= 1

            if en["vida"] > 0:
                nuevos_enemigos_blackhole.append(en)
            else:
                estado["score"] += PUNTOS.get(en["tipo"], 1000)
                registrar_enemigo_destruido()
                ganar_monedas(PUNTOS.get(en["tipo"], 1000)//10)
                explosion(en["x"], en["y"])

        estado["enemigos"] = nuevos_enemigos_blackhole

        boss_temp, tipo_temp = obtener_boss_activo()

        if boss_temp is not None and estado["ultimate_blackhole"] % 10 == 0:
            boss_temp["vida"] -= 1

    if estado["ultimate_orbital"] > 0:

        if estado["ultimate_orbital"] < 90:

            orbital_rect = pygame.Rect(
                estado["ultimate_orbital_x"]-45,
                0,
                90,
                ALTO
            )

            nuevos_enemigos_orbital=[]

            for en in estado["enemigos"]:
                rect_enemigo = pygame.Rect(en["x"], en["y"], 70, 70)

                if orbital_rect.colliderect(rect_enemigo):
                    en["vida"] -= 2

                if en["vida"] > 0:
                    nuevos_enemigos_orbital.append(en)
                else:
                    estado["score"] += PUNTOS.get(en["tipo"], 1000)
                    registrar_enemigo_destruido()
                    ganar_monedas(PUNTOS.get(en["tipo"], 1000)//10)
                    explosion(en["x"], en["y"])

            estado["enemigos"] = nuevos_enemigos_orbital

            if estado["boss"]:
                boss_rect_temp = pygame.Rect(estado["boss"]["x"], estado["boss"]["y"], 150, 150)
                if orbital_rect.colliderect(boss_rect_temp):
                    estado["boss"]["vida"] -= 2

            if estado["boss_final"]:
                boss_rect_temp = pygame.Rect(estado["boss_final"]["x"], estado["boss_final"]["y"], 170, 170)
                if orbital_rect.colliderect(boss_rect_temp):
                    estado["boss_final"]["vida"] -= 2

            if estado["boss_laser"]:
                boss_rect_temp = pygame.Rect(estado["boss_laser"]["x"], estado["boss_laser"]["y"], 190, 190)
                if orbital_rect.colliderect(boss_rect_temp):
                    estado["boss_laser"]["vida"] -= 2

            if estado.get("boss_overmind"):
                boss_rect_temp = pygame.Rect(estado["boss_overmind"]["x"], estado["boss_overmind"]["y"], 210, 210)
                if orbital_rect.colliderect(boss_rect_temp):
                    estado["boss_overmind"]["vida"] -= 2

            for boss_key in ["boss_rift","boss_hollow","boss_sun_eater","boss_eden"]:
                if estado.get(boss_key):
                    boss_rect_temp = pygame.Rect(estado[boss_key]["x"], estado[boss_key]["y"], 230, 230)
                    if orbital_rect.colliderect(boss_rect_temp):
                        estado[boss_key]["vida"] -= 2

    # =====================
    # POWERUPS
    # =====================
    nuevos=[]

    for p in estado["powerups"]:

        p[1]+=2

        if punto_colisiona_jugador(p[0],p[1]):

            if p[2]=="rapid":
                estado["rapid"]=300
                reproducir_sfx("pickup")

            if p[2]=="double":
                estado["double"]=300
                reproducir_sfx("pickup")

            if p[2]=="shield":
                estado["shield"]=300
                reproducir_sfx("shield_pickup")

            if p[2]=="bomb":
                estado["enemigos"].clear()
                reproducir_sfx("explosion", force=True)

        else:
            nuevos.append(p)

    estado["powerups"]=nuevos

    # =====================
    # LIMPIEZA DE SEGURIDAD DE ENEMIGOS
    # =====================
    estado["enemigos"] = [
        en for en in estado["enemigos"]
        if en.get("vida", 1) > 0 and en.get("y", 0) < ALTO + 150
    ]

    # =====================
    # MUERTE
    # =====================
    if estado["hp"]<=0:

        if habilidad_comprada("revive_core") and not estado.get("revive_used", False):
            estado["hp"] = 35
            estado["vidas"] = estado["hp"]
            estado["inv"] = 150
            estado["shield"] = max(estado.get("shield",0), 180)
            estado["revive_used"] = True
            flash = 18
            shake = 25
        else:
            game_over_score = int(estado["score"])
            game_over_coins = int(estado["score"])//500
            ganar_monedas(game_over_coins)
            finalizar_partida_y_guardar(estado["score"])
            estado=reiniciar()
            estado["estado"]="GAME_OVER"

    estado["score"]+=2

    # temporizadores laser
    if estado["laser"]>0:
        if estado["laser"] in [120,125]:
            reproducir_sfx("boss_charge")
        estado["laser"]-=1

    if estado["laser_horizontal"]>0:
        if estado["laser_horizontal"] in [120,125]:
            reproducir_sfx("boss_charge")
        estado["laser_horizontal"]-=1

    if estado["laser_cross"]>0:
        if estado["laser_cross"] == 130:
            reproducir_sfx("boss_charge")
        estado["laser_cross"]-=1

    if estado["laser_sweep"]>0:
        if estado["laser_sweep"] == 150:
            reproducir_sfx("boss_charge")
        estado["laser_sweep"]-=1

    # =====================
    # EFECTOS VISUALES AVANZADOS - ACTUALIZACION
    # =====================
    for o in ondas_expansion:
        o["r"] += 4
        o["vida"] -= 1

    ondas_expansion[:] = [
        o for o in ondas_expansion
        if o["vida"] > 0 and o["r"] < o["max"]
    ]

    for d in destellos:
        d["vida"] -= 1

    destellos[:] = [
        d for d in destellos
        if d["vida"] > 0
    ]

    for tr in estelas_nave:
        tr["vida"] -= 1

    estelas_nave[:] = [
        tr for tr in estelas_nave
        if tr["vida"] > 0
    ]

    # =====================
    # PARTICULAS
    # =====================
    for p in particulas:

        p[0]+=p[2]
        p[1]+=p[3]
        p[4]-=1

    particulas=[
        p for p in particulas
        if p[4]>0
    ]
    actualizar_particulas_energia()
    actualizar_fx_v73()

    # =====================
    # DIBUJO
    # =====================
    shake_visual = min(18, int(shake * 0.55))
    offset_x=random.randint(-shake_visual,shake_visual) if shake_visual>0 else 0
    offset_y=random.randint(-shake_visual,shake_visual) if shake_visual>0 else 0

    if shake>0:
        shake=max(0,shake-2)

    # Fondo profundo con parallax, nebulosas y meteoritos
    dibujar_fondo_profundo(nivel, offset_x, offset_y)
    dibujar_planeta_gameplay_v69(offset_x, offset_y)
    if random.randint(1, 7) == 1:
        emitir_micro_polvo(random.randint(0, ANCHO), -10, color_nivel_v59(nivel), 1)
    dibujar_fx_detras_v73(offset_x, offset_y)

    # estrellas cercanas rï¿½pidas
    for e in estrellas:

        e["y"]+=e["vel"]*slowmo

        if e["y"]>ALTO:
            e["y"]=0
            e["x"]=random.randint(0,ANCHO)

        pygame.draw.circle(
            pantalla,
            BLANCO,
            (
                int(e["x"]+offset_x*0.7),
                int(e["y"]+offset_y*0.7)
            ),
            2
        )

    # =====================
    # ESTELA DE NAVE VISUAL
    # =====================
    for tr in estelas_nave:

        alpha = int(42 * (tr["vida"]/tr["max"]))
        radio = int(tr["r"] * 0.65 * (tr["vida"]/tr["max"]))

        if radio > 1:
            crear_glow(
                pantalla,
                int(tr["x"]+offset_x*0.4),
                int(tr["y"]+offset_y*0.4),
                radio,
                tr["color"],
                alpha
            )

    # =====================
    # DESTELLOS Y ONDAS DE EXPLOSION
    # =====================
    for d in destellos:
        alpha = int(130 * (d["vida"]/d["max"]))
        radio = int(d["radio"] * (d["vida"]/d["max"]))

        if radio > 2:
            crear_glow(
                pantalla,
                int(d["x"]+offset_x),
                int(d["y"]+offset_y),
                radio,
                d["color"],
                alpha
            )

    for o in ondas_expansion:
        alpha = int(180 * (o["vida"]/32))
        pygame.draw.circle(
            pantalla,
            o["color"],
            (
                int(o["x"]+offset_x),
                int(o["y"]+offset_y)
            ),
            int(o["r"]),
            2
        )

    dibujar_wormhole_evento(offset_x, offset_y)
    dibujar_modo_boss_ambiente(offset_x, offset_y)
    dibujar_boss_cinematica_v65(offset_x, offset_y)

    # nave / naves
    nave_actual_img = imagen_nave_por_tipo(estado.get("nave_tipo",1))

    if estado.get("coop",False):
        nave_actual_img = pygame.transform.scale(nave_actual_img,(50,50))

    crear_glow(
        pantalla,
        int(estado["nave_x"]+(25 if estado.get("coop",False) else 30)+offset_x),
        int(estado["nave_y"]+(25 if estado.get("coop",False) else 30)+offset_y),
        22 if estado.get("coop",False) else (26 if estado.get("ultimate_overdrive",0)<=0 else 38),
        color_nave_por_tipo(estado.get("nave_tipo",1)),
        18 if estado.get("ultimate_overdrive",0)<=0 else 34
    )

    pantalla.blit(
        nave_actual_img,
        (
            estado["nave_x"]+offset_x,
            estado["nave_y"]+offset_y
        )
    )

    if estado.get("coop",False):
        nave2_actual_img = pygame.transform.scale(imagen_nave_por_tipo(estado.get("nave2_tipo",2)),(50,50))

        crear_glow(
            pantalla,
            int(estado["nave2_x"]+25+offset_x),
            int(estado["nave2_y"]+25+offset_y),
            22,
            color_nave_por_tipo(estado.get("nave2_tipo",2)),
            18
        )

        pantalla.blit(
            nave2_actual_img,
            (
                estado["nave2_x"]+offset_x,
                estado["nave2_y"]+offset_y
            )
        )

        p2_label = fuente_peq.render("P2", True, BLANCO)
        pantalla.blit(p2_label,(estado["nave2_x"]+offset_x+14,estado["nave2_y"]+offset_y-18))

    # escudo
    if estado["shield"]>0:
        shield_cx = int(estado["nave_x"] + nave_actual_img.get_width()//2 + offset_x)
        shield_cy = int(estado["nave_y"] + nave_actual_img.get_height()//2 + offset_y)
        shield_radio = max(SHIELD_RADIUS_MAIN, int(max(nave_actual_img.get_width(), nave_actual_img.get_height())*0.58))
        crear_glow(pantalla, shield_cx, shield_cy, shield_radio + 10, (40,190,255), 24)

        pygame.draw.circle(
            pantalla,
            (55,210,255),
            (shield_cx, shield_cy),
            shield_radio,
            2
        )
        pygame.draw.circle(pantalla,(180,245,255),(shield_cx, shield_cy), max(8, shield_radio-8), 1)

    if estado.get("coop",False) and estado["shield"]>0:
        shield2_cx = int(estado["nave2_x"] + nave2_actual_img.get_width()//2 + offset_x)
        shield2_cy = int(estado["nave2_y"] + nave2_actual_img.get_height()//2 + offset_y)
        shield2_radio = max(SHIELD_RADIUS_COOP, int(max(nave2_actual_img.get_width(), nave2_actual_img.get_height())*0.58))
        crear_glow(pantalla, shield2_cx, shield2_cy, shield2_radio + 8, (180,90,255), 20)
        pygame.draw.circle(
            pantalla,
            (180,90,255),
            (shield2_cx, shield2_cy),
            shield2_radio,
            2
        )

    # enemigos
    for en in estado["enemigos"]:

        dibujar_aura_enemigo(en, offset_x, offset_y)

        if en["tipo"]=="asteroide":
            pantalla.blit(asteroid_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="alien":
            pantalla.blit(alien_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="drone":
            pantalla.blit(drone_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="zigzag":
            pantalla.blit(zigzag_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="crucero":
            pantalla.blit(crucero_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="phantom":
            pantalla.blit(phantom_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="orb":
            pantalla.blit(orb_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="gravity":
            pantalla.blit(gravity_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="sentinel":
            pantalla.blit(sentinel_img,(en["x"]+offset_x,en["y"]+offset_y))

            if en.get("laser",0)>0:
                laser_x = en["x"] + 35
                laser_inicio = en["y"] + 55
                laser_final = ALTO

                if en["laser"]>45:
                    pygame.draw.line(
                        pantalla,
                        (255,0,0),
                        (laser_x+offset_x,laser_inicio+offset_y),
                        (laser_x+offset_x,laser_final+offset_y),
                        3
                    )
                else:
                    particulas_laser_vertical_lados(laser_x, laser_inicio, laser_final)

                    pygame.draw.rect(
                        pantalla,
                        (255,40,40),
                        (laser_x-10+offset_x,laser_inicio+offset_y,20,laser_final-laser_inicio)
                    )
                    pygame.draw.rect(
                        pantalla,
                        (255,200,200),
                        (laser_x-4+offset_x,laser_inicio+offset_y,8,laser_final-laser_inicio)
                    )

        elif en["tipo"]=="hunter":
            pantalla.blit(hunter_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="void_orb":
            pantalla.blit(void_orb_img,(en["x"]+offset_x,en["y"]+offset_y))
            pygame.draw.circle(
                pantalla,
                (120,0,200),
                (
                    int(en["x"]+35+offset_x),
                    int(en["y"]+35+offset_y)
                ),
                120,
                1
            )

        elif en["tipo"]=="parasite":
            crear_glow(pantalla,int(en["x"]+23+offset_x),int(en["y"]+23+offset_y),24,(190,40,255),60)
            pantalla.blit(parasite_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="hive":
            crear_glow(pantalla,int(en["x"]+45+offset_x),int(en["y"]+45+offset_y),60,(120,0,180),75)
            pantalla.blit(hive_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="shadow_phantom":
            if en.get("invisible",False):
                temp=shadow_phantom2_img.copy()
                temp.set_alpha(80)
                pantalla.blit(temp,(en["x"]+offset_x,en["y"]+offset_y))
            else:
                crear_glow(pantalla,int(en["x"]+35+offset_x),int(en["y"]+35+offset_y),42,(180,70,255),65)
                pantalla.blit(shadow_phantom2_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="leech_drone":
            crear_glow(pantalla,int(en["x"]+30+offset_x),int(en["y"]+30+offset_y),36,(220,0,255),65)
            pantalla.blit(leech_drone_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="rift_splitter":
            crear_glow(pantalla,int(en["x"]+35+offset_x),int(en["y"]+35+offset_y),32,(80,220,255),55)
            pantalla.blit(rift_splitter_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="quantum_shard":
            crear_glow(pantalla,int(en["x"]+19+offset_x),int(en["y"]+19+offset_y),18,(120,240,255),60)
            pygame.draw.polygon(pantalla,(120,240,255),[(en["x"]+19+offset_x,en["y"]+offset_y),(en["x"]+38+offset_x,en["y"]+19+offset_y),(en["x"]+19+offset_x,en["y"]+38+offset_y),(en["x"]+offset_x,en["y"]+19+offset_y)])

        elif en["tipo"]=="phase_reaper":
            if not en.get("invisible",False):
                crear_glow(pantalla,int(en["x"]+37+offset_x),int(en["y"]+37+offset_y),36,(190,90,255),60)
                pantalla.blit(phase_reaper_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="chrono_mine":
            crear_glow(pantalla,int(en["x"]+30+offset_x),int(en["y"]+30+offset_y),48,(255,210,80),35)
            pygame.draw.circle(pantalla,(255,210,80),(int(en["x"]+30+offset_x),int(en["y"]+30+offset_y)),85,1)
            pantalla.blit(chrono_mine_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="abyss_wisp":
            crear_glow(pantalla,int(en["x"]+29+offset_x),int(en["y"]+29+offset_y),48,(35,200,255),45)
            temp=abyss_wisp_img.copy()
            if en.get("invisible",False):
                temp.set_alpha(95)
            pantalla.blit(temp,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="null_seeker":
            crear_glow(pantalla,int(en["x"]+31+offset_x),int(en["y"]+31+offset_y),44,(35,90,180),50)
            pantalla.blit(null_seeker_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="void_lantern":
            crear_glow(pantalla,int(en["x"]+38+offset_x),int(en["y"]+38+offset_y),62,(90,230,255),55)
            pantalla.blit(void_lantern_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="solar_mantis":
            crear_glow(pantalla,int(en["x"]+34+offset_x),int(en["y"]+34+offset_y),42,(255,170,50),50)
            pantalla.blit(solar_mantis_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="flare_drone":
            crear_glow(pantalla,int(en["x"]+31+offset_x),int(en["y"]+31+offset_y),50,(255,120,40),50)
            pantalla.blit(flare_drone_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="helio_spire":
            crear_glow(pantalla,int(en["x"]+35+offset_x),int(en["y"]+40+offset_y),54,(255,205,70),45)
            pantalla.blit(helio_spire_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="bloom_parasite":
            crear_glow(pantalla,int(en["x"]+25+offset_x),int(en["y"]+25+offset_y),38,(90,255,170),50)
            pantalla.blit(bloom_parasite_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="crystal_seraph":
            crear_glow(pantalla,int(en["x"]+37+offset_x),int(en["y"]+37+offset_y),55,(190,255,240),55)
            pantalla.blit(crystal_seraph_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="root_hydra":
            crear_glow(pantalla,int(en["x"]+45+offset_x),int(en["y"]+45+offset_y),66,(70,230,150),50)
            pantalla.blit(root_hydra_img,(en["x"]+offset_x,en["y"]+offset_y))

        elif en["tipo"]=="laser_satellite":
            pantalla.blit(laser_satellite_img,(en["x"]+offset_x,en["y"]+offset_y))

            if en.get("laser",0)>0:
                laser_y = en["y"] + 25

                # El rayo sale desde los dos lados del satï¿½lite, no como una lï¿½nea infinita sin origen.
                izquierda_x = 0
                izquierda_w = max(0, int(en["x"]))

                derecha_x = int(en["x"] + 80)
                derecha_w = max(0, ANCHO - derecha_x)

                if en["laser"]>50:
                    pygame.draw.line(
                        pantalla,
                        (255,0,0),
                        (izquierda_x,laser_y+offset_y),
                        (en["x"]+offset_x,laser_y+offset_y),
                        3
                    )
                    pygame.draw.line(
                        pantalla,
                        (255,0,0),
                        (en["x"]+80+offset_x,laser_y+offset_y),
                        (ANCHO,laser_y+offset_y),
                        3
                    )
                else:
                    particulas_laser_horizontal_lados(laser_y, izquierda_x, ANCHO)

                    pygame.draw.rect(
                        pantalla,
                        (255,40,40),
                        (izquierda_x,laser_y-15+offset_y,izquierda_w,30)
                    )
                    pygame.draw.rect(
                        pantalla,
                        (255,200,200),
                        (izquierda_x,laser_y-5+offset_y,izquierda_w,10)
                    )

                    pygame.draw.rect(
                        pantalla,
                        (255,40,40),
                        (derecha_x+offset_x,laser_y-15+offset_y,derecha_w,30)
                    )
                    pygame.draw.rect(
                        pantalla,
                        (255,200,200),
                        (derecha_x+offset_x,laser_y-5+offset_y,derecha_w,10)
                    )

    # balas jugador
    for b in estado["balas"]:
        crear_glow(
            pantalla,
            int(b[0]+offset_x+2),
            int(b[1]+offset_y+2),
            7,
            (90,210,255),
            28
        )

        pygame.draw.line(pantalla,(80,190,225),(int(b[0]+offset_x+2),int(b[1]+offset_y+7)),(int(b[0]+offset_x+2),int(b[1]+offset_y-5)),2)
        pygame.draw.circle(pantalla,BLANCO,(int(b[0]+offset_x+2),int(b[1]+offset_y)),2)

    # balas enemigas
    for b in estado["balas_enemigas"]:

        if "boss_final" in b:
            crear_glow(
                pantalla,
                int(b[0]+offset_x+12),
                int(b[1]+offset_y+12),
                12,
                (255,60,255),
                35
            )

            pantalla.blit(
                bala_boss_final_img,
                (
                    b[0]+offset_x,
                    b[1]+offset_y
                )
            )

        else:
            color_bala = (255,80,80)
            if len(b) > 4 and b[4] == "solar":
                color_bala = (255,180,65)
            elif len(b) > 4 and b[4] == "rift":
                color_bala = (90,230,255)
            elif len(b) > 4 and b[4] == "eden":
                color_bala = (120,255,190)
            crear_glow(
                pantalla,
                int(b[0]+offset_x+10),
                int(b[1]+offset_y+10),
                9,
                color_bala,
                30
            )

            pantalla.blit(
                bala_enemiga_img,
                (
                    b[0]+offset_x,
                    b[1]+offset_y
                )
            )

    # =====================
    # ULTIMATE ATTACKS VISUALES
    # =====================

    if estado["ultimate_message"] > 0:
        texto_ult = pygame.font.SysFont(None,42).render(
            estado["ultimate_message_text"],
            True,
            (255,255,255)
        )

        pygame.draw.rect(
            pantalla,
            (0,0,0),
            (
                ANCHO//2 - texto_ult.get_width()//2 - 18,
                90,
                texto_ult.get_width()+36,
                45
            )
        )

        pygame.draw.rect(
            pantalla,
            (80,200,255),
            (
                ANCHO//2 - texto_ult.get_width()//2 - 18,
                90,
                texto_ult.get_width()+36,
                45
            ),
            2
        )

        pantalla.blit(
            texto_ult,
            (
                ANCHO//2 - texto_ult.get_width()//2,
                100
            )
        )

    if estado["ultimate_overdrive"] > 0:

        aura_radio = 42 + (estado["ultimate_overdrive"] % 12)

        pygame.draw.circle(
            pantalla,
            (40,200,255),
            (
                int(estado["nave_x"]+30+offset_x),
                int(estado["nave_y"]+30+offset_y)
            ),
            aura_radio,
            3
        )

        pygame.draw.circle(
            pantalla,
            (220,250,255),
            (
                int(estado["nave_x"]+30+offset_x),
                int(estado["nave_y"]+30+offset_y)
            ),
            max(10,aura_radio-18),
            1
        )

    if estado["ultimate_blackhole"] > 0:

        cx = estado["ultimate_blackhole_x"]
        cy = estado["ultimate_blackhole_y"]
        radio = 90 + (estado["ultimate_blackhole"] % 40)

        pygame.draw.circle(
            pantalla,
            (15,0,25),
            (
                int(cx+offset_x),
                int(cy+offset_y)
            ),
            radio
        )

        pygame.draw.circle(
            pantalla,
            (120,0,220),
            (
                int(cx+offset_x),
                int(cy+offset_y)
            ),
            radio,
            4
        )

        pygame.draw.circle(
            pantalla,
            (230,180,255),
            (
                int(cx+offset_x),
                int(cy+offset_y)
            ),
            max(12,radio//4),
            2
        )

        for i in range(12):
            ang = (estado["ultimate_blackhole"]*0.08) + i*(math.pi*2/12)
            r = radio + 20
            pygame.draw.circle(
                pantalla,
                (170,60,255),
                (
                    int(cx + math.cos(ang)*r + offset_x),
                    int(cy + math.sin(ang)*r + offset_y)
                ),
                3
            )

    if estado["ultimate_orbital"] > 0:

        x = estado["ultimate_orbital_x"]

        if estado["ultimate_orbital"] > 90:

            pygame.draw.line(
                pantalla,
                (80,220,255),
                (
                    int(x+offset_x),
                    0
                ),
                (
                    int(x+offset_x),
                    ALTO
                ),
                4
            )

        else:

            shake = max(shake, 24)

            pygame.draw.rect(
                pantalla,
                (40,170,255),
                (
                    int(x-45+offset_x),
                    0,
                    90,
                    ALTO
                )
            )

            pygame.draw.rect(
                pantalla,
                (230,250,255),
                (
                    int(x-18+offset_x),
                    0,
                    36,
                    ALTO
                )
            )

    # =====================
    # HABILIDADES DEL JUGADOR VISUALES
    # =====================

    # =====================
    # HABILIDADES DEL JUGADOR 2 VISUALES
    # =====================
    if estado.get("coop",False) and estado.get("player_laser2",0) > 0:

        laser_x = estado["nave2_x"] + 25

        dibujar_laser_jugador_cinematico(
            laser_x,
            estado["nave2_y"],
            offset_x,
            offset_y,
            (180,80,255),
            48
        )

    if estado.get("coop",False) and estado.get("pulse2_timer",0) > 0:

        pygame.draw.circle(
            pantalla,
            (190,90,255),
            (
                int(estado["nave2_x"]+21+offset_x),
                int(estado["nave2_y"]+21+offset_y)
            ),
            estado["pulse2_radius"],
            3
        )

    if estado["player_laser"] > 0:

        laser_x = estado["nave_x"] + 30

        dibujar_laser_jugador_cinematico(
            laser_x,
            estado["nave_y"],
            offset_x,
            offset_y,
            (40,180,255),
            56
        )

        pygame.draw.circle(
            pantalla,
            (210,245,255),
            (
                int(laser_x+offset_x),
                int(estado["nave_y"]+offset_y)
            ),
            22,
            3
        )

    if estado["pulse_timer"] > 0:

        radio = estado["pulse_radius"]

        pygame.draw.circle(
            pantalla,
            (80,200,255),
            (
                int(estado["nave_x"]+25+offset_x),
                int(estado["nave_y"]+25+offset_y)
            ),
            radio,
            3
        )

        if radio > 20:
            pygame.draw.circle(
                pantalla,
                (220,250,255),
                (
                    int(estado["nave_x"]+25+offset_x),
                    int(estado["nave_y"]+25+offset_y)
                ),
                max(1, radio-20),
                1
            )

    # =====================
    # LASER VERTICAL VISUAL
    # =====================
    if estado["laser"]>0:

        if estado["laser"]>60:
            dibujar_rayo_cinematico(pantalla, "v", estado["laser_x"], offset_x, offset_y, aviso=True)

        else:

            shake=24
            particulas_laser_vertical(estado["laser_x"])
            dibujar_rayo_cinematico(pantalla, "v", estado["laser_x"], offset_x, offset_y, aviso=False, grosor=58)

    # =====================
    # LASER HORIZONTAL VISUAL
    # =====================
    if estado["laser_horizontal"]>0:
        color_laser_h = estado.get("laser_horizontal_color",(255,40,40))

        if estado["laser_horizontal"]>60:
            dibujar_rayo_cinematico(pantalla, "h", estado["laser_y"], offset_x, offset_y, aviso=True, color=color_laser_h)

        else:

            shake=24
            particulas_laser_horizontal(estado["laser_y"], color_laser_h)
            dibujar_rayo_cinematico(pantalla, "h", estado["laser_y"], offset_x, offset_y, aviso=False, grosor=58, color=color_laser_h)

    # =====================
    # CROSS LASER VISUAL
    # =====================
    if estado["laser_cross"]>0:

        if estado["laser_cross"]>65:
            dibujar_rayo_cinematico(pantalla, "v", estado["laser_cross_x"], offset_x, offset_y, aviso=True)
            dibujar_rayo_cinematico(pantalla, "h", estado["laser_cross_y"], offset_x, offset_y, aviso=True)

        else:

            shake=25
            particulas_laser_vertical(estado["laser_cross_x"])
            particulas_laser_horizontal(estado["laser_cross_y"])
            dibujar_rayo_cinematico(pantalla, "v", estado["laser_cross_x"], offset_x, offset_y, aviso=False, grosor=54)
            dibujar_rayo_cinematico(pantalla, "h", estado["laser_cross_y"], offset_x, offset_y, aviso=False, grosor=54)

    # =====================
    # LASER FIJO ESPECIAL VISUAL
    # =====================
    if estado["laser_sweep"]>0:

        if estado["laser_sweep_tipo"]=="vertical":

            if estado["laser_sweep"]>90:
                dibujar_rayo_cinematico(pantalla, "v", estado["laser_sweep_x"], offset_x, offset_y, aviso=True)

            else:

                shake=20
                particulas_laser_vertical(estado["laser_sweep_x"])
                dibujar_rayo_cinematico(pantalla, "v", estado["laser_sweep_x"], offset_x, offset_y, aviso=False, grosor=50)

        else:

            if estado["laser_sweep"]>90:
                dibujar_rayo_cinematico(pantalla, "h", estado["laser_sweep_y"], offset_x, offset_y, aviso=True)

            else:

                shake=20
                particulas_laser_horizontal(estado["laser_sweep_y"])
                dibujar_rayo_cinematico(pantalla, "h", estado["laser_sweep_y"], offset_x, offset_y, aviso=False, grosor=50)

        # =====================
    # QUANTUM RIFT VISUALES
    # =====================
    for q in estado.get("quantum_fields",[]):
        alpha_color=(80,220,255) if q["vida"]%20<10 else (190,90,255)
        crear_glow(pantalla,int(q["x"]+offset_x),int(q["y"]+offset_y),int(q["r"]),alpha_color,35)
        pygame.draw.circle(pantalla,alpha_color,(int(q["x"]+offset_x),int(q["y"]+offset_y)),int(q["r"]),2)

    for r in estado.get("rift_attacks",[]):
        activo = r["timer"] < 42
        color = (80,220,255) if activo else (80,120,180)
        ancho = 42 if activo else 4
        if r.get("tipo")=="v":
            x=int(r.get("x",ANCHO//2)+offset_x)
            if activo:
                crear_rect_glow(pantalla,(x-22,0,44,ALTO),color,65,20)
            pygame.draw.line(pantalla,color,(x,0),(x,ALTO),ancho)
        else:
            y=int(r.get("y",ALTO//2)+offset_y)
            if activo:
                crear_rect_glow(pantalla,(0,y-22,ANCHO,44),color,65,20)
            pygame.draw.line(pantalla,color,(0,y),(ANCHO,y),ancho)

    for z in estado.get("abyss_zones",[]):
        pulso_zona = z.get("timer", z.get("vida", 0))
        color=(35,210,255) if pulso_zona%24<12 else (20,80,160)
        cx=int(z["x"]+offset_x)
        cy=int(z["y"]+offset_y)
        crear_glow(pantalla,cx,cy,int(z["r"]+18),color,34)
        pygame.draw.circle(pantalla,(0,0,8),(cx,cy),int(z["r"]))
        pygame.draw.circle(pantalla,color,(cx,cy),int(z["r"]),2)
        pygame.draw.circle(pantalla,(230,255,255),(cx,cy),max(3,int(z["r"]//6)),1)

    for s in estado.get("silence_rings",[]):
        radio=int(s["r"])
        crear_glow(pantalla,int(s["x"]+offset_x),int(s["y"]+offset_y),radio,(45,210,255),20)
        pygame.draw.circle(pantalla,(80,230,255),(int(s["x"]+offset_x),int(s["y"]+offset_y)),radio,2)

    for w in estado.get("solar_waves",[]):
        activo=w["timer"]<65
        color=(255,205,45)
        if activo:
            particulas_laser_horizontal(w["y"], color)
            dibujar_rayo_cinematico(pantalla, "h", w["y"], offset_x, offset_y, aviso=False, grosor=48, color=color)
        else:
            dibujar_rayo_cinematico(pantalla, "h", w["y"], offset_x, offset_y, aviso=True, color=color)

    for r in estado.get("eden_roots",[]):
        dibujar_tentaculo_animado(r, offset_x, offset_y)

    for c in estado.get("crystal_rain",[]):
        x=int(c[0]+offset_x)
        y=int(c[1]+offset_y)
        crear_glow(pantalla,x,y,26,(180,255,230),35)
        pygame.draw.polygon(pantalla,(180,255,230),[(x,y-18),(x+11,y),(x,y+18),(x-11,y)])
        pygame.draw.polygon(pantalla,(45,140,120),[(x,y-18),(x+11,y),(x,y+18),(x-11,y)],2)

    for p in estado.get("life_pulses",[]):
        radio=int(p["r"])
        crear_glow(pantalla,int(p["x"]+offset_x),int(p["y"]+offset_y),radio,(90,255,170),18)
        pygame.draw.circle(pantalla,(120,255,190),(int(p["x"]+offset_x),int(p["y"]+offset_y)),radio,2)

# powerups
    for p in estado["powerups"]:

        crear_glow(
            pantalla,
            int(p[0]+offset_x),
            int(p[1]+offset_y),
            22,
            (0,255,120),
            80
        )

        pygame.draw.circle(
            pantalla,
            (0,255,0),
            (
                int(p[0]+offset_x),
                int(p[1]+offset_y)
            ),
            6
        )

        pygame.draw.circle(
            pantalla,
            BLANCO,
            (
                int(p[0]+offset_x),
                int(p[1]+offset_y)
            ),
            11,
            1
        )

    # void zones nivel 5
    for z in estado["void_zones"]:
        crear_glow(pantalla,int(z["x"]+offset_x),int(z["y"]+offset_y),int(z["r"]+25),(140,0,220),75)
        pygame.draw.circle(
            pantalla,
            (100,0,160),
            (int(z["x"]+offset_x),int(z["y"]+offset_y)),
            int(z["r"]),
            3
        )
        pygame.draw.circle(
            pantalla,
            (230,160,255),
            (int(z["x"]+offset_x),int(z["y"]+offset_y)),
            max(4,int(z["r"]//4)),
            1
        )

    # tentï¿½culos nivel 5
    for t in estado["tentacles"]:
        dibujar_tentaculo_animado(t, offset_x, offset_y)

    ticks = pygame.time.get_ticks()

    # boss rift monarch
    if estado.get("boss_rift"):

        boss=estado.get("boss_rift")
        dibujar_pre_boss("boss_rift", boss, offset_x, offset_y)

        crear_glow(pantalla,int(boss["x"]+110+offset_x),int(boss["y"]+110+offset_y),110,(80,220,255),60)

        pantalla.blit(
            boss_rift_monarch_img,
            (
                boss["x"]+offset_x,
                boss["y"]+offset_y
            )
        )

        dibujar_barra_boss_profesional("THE RIFT MONARCH", boss["vida"], 950, (80,220,255), 82)
        dibujar_post_boss("boss_rift", boss, offset_x, offset_y)

    # boss hollow cathedral
    if estado.get("boss_hollow"):
        boss=estado.get("boss_hollow")
        dibujar_pre_boss("boss_hollow", boss, offset_x, offset_y)
        cx=int(boss["x"]+115+offset_x)
        cy=int(boss["y"]+115+offset_y)
        crear_glow(pantalla,cx,cy,145,(35,220,255),70)
        for i in range(4):
            radio=70+i*18+int(math.sin(ticks*0.04+i)*5)
            pygame.draw.circle(pantalla,(40,180,230),(cx,cy),radio,2)
        pygame.draw.circle(pantalla,(5,15,38),(cx,cy),72)
        pygame.draw.circle(pantalla,(90,240,255),(cx,cy),72,4)
        pygame.draw.polygon(pantalla,(200,255,255),[(cx,cy-92),(cx+58,cy+58),(cx,cy+28),(cx-58,cy+58)],3)
        pantalla.blit(boss_hollow_saint_img,(boss["x"]+offset_x,boss["y"]+offset_y))
        dibujar_barra_boss_profesional("THE HOLLOW SAINT", boss["vida"], 1150, (40,220,255), 82)
        dibujar_post_boss("boss_hollow", boss, offset_x, offset_y)

    # boss sun eater
    if estado.get("boss_sun_eater"):
        boss=estado.get("boss_sun_eater")
        dibujar_pre_boss("boss_sun_eater", boss, offset_x, offset_y)
        cx=int(boss["x"]+115+offset_x)
        cy=int(boss["y"]+115+offset_y)
        crear_glow(pantalla,cx,cy,165,(255,145,35),85)
        for i in range(16):
            ang=ticks*0.025+i*math.pi/8
            p1=(int(cx+math.cos(ang)*58),int(cy+math.sin(ang)*58))
            p2=(int(cx+math.cos(ang)*116),int(cy+math.sin(ang)*116))
            pygame.draw.line(pantalla,(255,190,55),p1,p2,4)
        pygame.draw.circle(pantalla,(105,35,8),(cx,cy),70)
        pygame.draw.circle(pantalla,(255,210,80),(cx,cy),70,5)
        pygame.draw.circle(pantalla,(255,245,180),(cx,cy),24)
        pantalla.blit(boss_sun_eater_img,(boss["x"]+offset_x,boss["y"]+offset_y))
        dibujar_barra_boss_profesional("THE SUN EATER", boss["vida"], 1300, (255,155,35), 82)
        dibujar_post_boss("boss_sun_eater", boss, offset_x, offset_y)

    # boss eden crown
    if estado.get("boss_eden"):
        boss=estado.get("boss_eden")
        dibujar_pre_boss("boss_eden", boss, offset_x, offset_y)
        cx=int(boss["x"]+115+offset_x)
        cy=int(boss["y"]+115+offset_y)
        crear_glow(pantalla,cx,cy,175,(90,255,180),85)
        for i in range(8):
            ang=ticks*0.018+i*math.pi/4
            ex=int(cx+math.cos(ang)*96)
            ey=int(cy+math.sin(ang)*56)
            pygame.draw.line(pantalla,(95,255,180),(cx,cy),(ex,ey),4)
            pygame.draw.circle(pantalla,(190,255,225),(ex,ey),10)
        pygame.draw.polygon(pantalla,(20,85,60),[(cx,cy-92),(cx+82,cy-20),(cx+50,cy+78),(cx-50,cy+78),(cx-82,cy-20)])
        pygame.draw.polygon(pantalla,(180,255,230),[(cx,cy-92),(cx+82,cy-20),(cx+50,cy+78),(cx-50,cy+78),(cx-82,cy-20)],4)
        pygame.draw.circle(pantalla,(230,255,245),(cx,cy),22)
        pantalla.blit(boss_eden_prime_img,(boss["x"]+offset_x,boss["y"]+offset_y))
        dibujar_barra_boss_profesional("EDEN PRIME", boss["vida"], 1500, (90,255,180), 82)
        dibujar_post_boss("boss_eden", boss, offset_x, offset_y)

    # boss overmind
    if estado.get("boss_overmind"):

        boss=estado.get("boss_overmind")
        dibujar_pre_boss("boss_overmind", boss, offset_x, offset_y)

        crear_glow(
            pantalla,
            int(boss["x"]+105+offset_x),
            int(boss["y"]+105+offset_y),
            145,
            (180,0,255),
            95
        )

        if boss["vida"]<250:
            crear_glow(
                pantalla,
                int(boss["x"]+105+offset_x),
                int(boss["y"]+105+offset_y),
                180,
                (255,20,120),
                80
            )

        pantalla.blit(
            boss_overmind_img,
            (
                boss["x"]+offset_x,
                boss["y"]+offset_y
            )
        )

        dibujar_barra_boss_profesional("THE OVERMIND", boss["vida"], 750, (180,0,255), 82)
        dibujar_post_boss("boss_overmind", boss, offset_x, offset_y)

    # boss normal
    if estado["boss"]:

        boss=estado["boss"]
        dibujar_pre_boss("boss", boss, offset_x, offset_y)

        if estado.get("boss_intro_tipo","") == "normal" and estado.get("boss_intro",0) > 0:
            pygame.draw.circle(
                pantalla,
                (255,60,60),
                (
                    int(boss["x"]+85+offset_x),
                    int(boss["y"]+85+offset_y)
                ),
                105 + (estado["boss_intro"] % 25),
                3
            )

        boss_color_fase = (255,60,60) if boss["vida"] > 100 else ((255,140,40) if boss["vida"] > 40 else (255,0,0))
        crear_glow(
            pantalla,
            int(boss["x"]+85+offset_x),
            int(boss["y"]+85+offset_y),
            95 if boss["vida"] > 40 else 125,
            boss_color_fase,
            45 if boss["vida"] > 40 else 80
        )

        pantalla.blit(
            boss_img,
            (
                boss["x"]+offset_x,
                boss["y"]+offset_y
            )
        )

        dibujar_barra_boss_profesional("ASTEROID COMMANDER", boss["vida"], 200, (255,75,75), 18)
        dibujar_post_boss("boss", boss, offset_x, offset_y)

    # boss final
    if estado["boss_final"]:

        boss=estado["boss_final"]
        dibujar_pre_boss("boss_final", boss, offset_x, offset_y)

        if estado.get("boss_intro_tipo","") == "final" and estado.get("boss_intro",0) > 0:
            pygame.draw.circle(
                pantalla,
                (190,40,255),
                (
                    int(boss["x"]+85+offset_x),
                    int(boss["y"]+85+offset_y)
                ),
                115 + (estado["boss_intro"] % 35),
                4
            )

        boss_color_fase = (160,40,255) if boss["vida"] > 250 else ((255,70,210) if boss["vida"] > 100 else (255,30,90))
        crear_glow(
            pantalla,
            int(boss["x"]+85+offset_x),
            int(boss["y"]+85+offset_y),
            105 if boss["vida"] > 100 else 135,
            boss_color_fase,
            55 if boss["vida"] > 100 else 90
        )

        pantalla.blit(
            boss_final_img,
            (
                boss["x"]+offset_x,
                boss["y"]+offset_y
            )
        )

        dibujar_barra_boss_profesional("OMEGA DESTROYER", boss["vida"], 400, (190,70,255), 18)
        dibujar_post_boss("boss_final", boss, offset_x, offset_y)

    # nuevo boss laser
    if estado["boss_laser"]:

        boss=estado["boss_laser"]
        dibujar_pre_boss("boss_laser", boss, offset_x, offset_y)

        if estado.get("boss_intro_tipo","") == "laser" and estado.get("boss_intro",0) > 0:
            pygame.draw.circle(
                pantalla,
                (255,40,40),
                (
                    int(boss["x"]+95+offset_x),
                    int(boss["y"]+95+offset_y)
                ),
                130 + (estado["boss_intro"] % 45),
                5
            )
            pygame.draw.line(
                pantalla,
                (255,80,80),
                (int(boss["x"]+95+offset_x),0),
                (int(boss["x"]+95+offset_x),ALTO),
                2
            )

        boss_color_fase = (255,80,80) if boss["vida"] > 430 else ((255,40,40) if boss["vida"] > 220 else (255,0,0))
        crear_glow(
            pantalla,
            int(boss["x"]+95+offset_x),
            int(boss["y"]+95+offset_y),
            125 if boss["vida"] > 220 else 155,
            boss_color_fase,
            65 if boss["vida"] > 220 else 105
        )

        pantalla.blit(
            boss_laser_img,
            (
                boss["x"]+offset_x,
                boss["y"]+offset_y
            )
        )

        dibujar_barra_boss_profesional("LASER OVERLORD", boss["vida"], 650, (255,55,55), 18)
        dibujar_post_boss("boss_laser", boss, offset_x, offset_y)

    dibujar_particulas_energia(offset_x, offset_y)
    dibujar_fx_delante_v73(offset_x, offset_y)
    dibujar_micro_anomalias()
    dibujar_hud_v64()
    dibujar_mision_planeta()
    dibujar_luces_dinamicas_v59(nivel, offset_x, offset_y)

    # =====================
    # BANNER DE NIVEL
    # =====================
    if level_banner > 0:
        alpha_factor = min(1, level_banner/45)
        texto_level = pygame.font.SysFont(None,72).render(level_banner_text, True, BLANCO)

        panel = pygame.Surface((ANCHO,90), pygame.SRCALPHA)
        panel.fill((0,0,0,int(120*alpha_factor)))

        pantalla.blit(panel,(0,230))

        pygame.draw.line(pantalla,(80,200,255),(0,230),(ANCHO,230),3)
        pygame.draw.line(pantalla,(80,200,255),(0,320),(ANCHO,320),3)

        pantalla.blit(
            texto_level,
            (
                ANCHO//2 - texto_level.get_width()//2,
                245
            )
        )

    # =====================
    # UI HABILIDADES ARCADE
    # =====================
    def texto_cooldown(nombre, cd):
        if cd <= 0:
            return f"{nombre}: {txt('ready')}"
        else:
            return f"{nombre}: {cd/60:.1f}s"

    def barra_vida_jugador(x,y,w,h):
        hp = max(0, estado.get("hp", estado.get("vidas",0)))
        max_hp = max(1, estado.get("max_hp",100))
        ratio = max(0,min(1,hp/max_hp))

        if ratio > 0.6:
            color = (80,255,160)
        elif ratio > 0.3:
            color = (255,210,70)
        else:
            color = (255,70,70)

        crear_rect_glow(pantalla,(x,y,w,h),color,35,8)

        pygame.draw.rect(pantalla,(18,18,24),(x,y,w,h),border_radius=8)
        pygame.draw.rect(pantalla,color,(x,y,int(w*ratio),h),border_radius=8)
        pygame.draw.rect(pantalla,BLANCO,(x,y,w,h),2,border_radius=8)

        texto_hp = f"{txt('hp')}: {int(hp)} / {int(max_hp)}"
        dibujar_texto_centrado_auto(
            pantalla,
            texto_hp,
            (x,y,w,h),
            BLANCO,
            22,
            12
        )

    def barra_cooldown(x, y, w, h, nombre, cd, max_cd, color):
        crear_rect_glow(pantalla,(x,y,w,h),color,26,5)
        pygame.draw.rect(pantalla,(3,10,22),(x,y,w,h),border_radius=4)
        pygame.draw.rect(pantalla,(70,95,120),(x,y,w,h),1,border_radius=4)

        if cd <= 0:
            relleno = w-4
            pygame.draw.rect(pantalla,color,(x+2,y+2,relleno,h-4),border_radius=3)
            texto = f"{nombre}: {txt('ready')}"
        else:
            relleno = int((1 - cd/max_cd) * (w-4))
            pygame.draw.rect(pantalla,color,(x+2,y+2,max(0,relleno),h-4),border_radius=3)
            texto = f"{nombre}: {cd/60:.1f}s"

        dibujar_texto_centrado_auto(
            pantalla,
            texto,
            (x,y,w,h),
            BLANCO,
            18,
            12
        )

    barra_cooldown(10, ALTO-82, 165, 20, "P1 DASH", estado["dash_cd"], 600, (40,180,255))
    barra_cooldown(10, ALTO-58, 165, 20, "P1 LASER", estado["player_laser_cd"], 1100, (60,220,255))
    barra_cooldown(10, ALTO-34, 165, 20, "P1 PULSE", estado["pulse_cd"], 1500, (80,255,160))

    if estado.get("coop",False):
        barra_cooldown(ANCHO-185, ALTO-82, 175, 20, "P2 DASH", estado["dash2_cd"], 600, (180,90,255))
        barra_cooldown(ANCHO-185, ALTO-58, 175, 20, "P2 LASER", estado["player_laser2_cd"], 1100, (180,90,255))
        barra_cooldown(ANCHO-185, ALTO-34, 175, 20, "P2 PULSE", estado["pulse2_cd"], 1500, (180,90,255))

    if hay_boss_activo():
        max_od = 1920 if habilidad_comprada("ultimate_core") else 2400
        max_bh = 2400 if habilidad_comprada("ultimate_core") else 3000
        max_orb = 2880 if habilidad_comprada("ultimate_core") else 3600

        if overdrive_permitido():
            barra_cooldown(ANCHO-220, ALTO-86, 210, 20, "Q OVERDRIVE", estado["ultimate_overdrive_cd"], max_od, (40,200,255))

        if ultimates_boss_permitidas():
            barra_cooldown(ANCHO-220, ALTO-60, 210, 20, "R BLACKHOLE", estado["ultimate_blackhole_cd"], max_bh, (160,70,255))
            barra_cooldown(ANCHO-220, ALTO-34, 210, 20, "T ORBITAL", estado["ultimate_orbital_cd"], max_orb, (80,220,255))

    if estado.get("coop",False):
        coop_render = fuente_peq.render("LOCAL COOP  |  P2: IJKL + RCTRL", True, (210,220,255))
        pantalla.blit(coop_render,(ANCHO//2 - coop_render.get_width()//2,15))

    # score
    pantalla.blit(
        fuente.render(
            f"{txt('score')}: {int(estado['score'])}",
            True,
            BLANCO
        ),
        (15,15)
    )

    # barra de vida del jugador
    barra_vida_jugador(15,50,210,22)

    # particulas
    for p in particulas:
        color_particula = p[5] if len(p) > 5 else BLANCO

        pygame.draw.circle(
            pantalla,
            color_particula,
            (
                int(p[0]+offset_x),
                int(p[1]+offset_y)
            ),
            2
        )

    # =====================
    # BORDES DE PELIGRO
    # =====================
    peligro_activo = (
        estado.get("laser",0) > 0 or
        estado.get("laser_horizontal",0) > 0 or
        estado.get("laser_cross",0) > 0 or
        estado.get("laser_sweep",0) > 0 or
        estado.get("ultimate_orbital",0) > 0
    )

    if peligro_activo:
        borde = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
        intensidad = 45 + int(abs(math.sin(pygame.time.get_ticks()/120))*50)
        pygame.draw.rect(borde,(255,30,30,intensidad),(0,0,ANCHO,ALTO),8)
        pantalla.blit(borde,(0,0))

    # cinematicas de boss encima del gameplay
    dibujar_intro_boss(offset_x, offset_y)
    dibujar_cabina_emergencia_v66()

    aplicar_postprocesado_v59(nivel)

    dibujar_admin_panel()

    # flash
    if flash>0:

        s=pygame.Surface((ANCHO,ALTO))
        s.set_alpha(120)
        s.fill(BLANCO)

        pantalla.blit(s,(0,0))

        flash-=1

    if net_role == "host":
        estado_red = net_status if net_status else (obtener_ip_local() + ":" + str(NET_PORT))
        red_render = fuente_peq.render("LAN HOST: " + estado_red, True, (180,220,255))
        pygame.draw.rect(
            pantalla,
            (0,0,0),
            (
                ANCHO//2-red_render.get_width()//2-10,
                34,
                red_render.get_width()+20,
                22
            ),
            border_radius=6
        )
        pantalla.blit(red_render,(ANCHO//2-red_render.get_width()//2,38))

        # Snapshot ligero de respaldo + frame completo para LAN V2.
        enviar_snapshot_host()
        enviar_frame_host()

    presentar_frame()
    clock.tick(60)



