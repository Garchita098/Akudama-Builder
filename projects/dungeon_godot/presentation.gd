extends RefCounted
## Loads sliced dungeon textures and picks autotile / animation frames.
## Simulation state stays in world.gd. This file is drawing data only.

const PixelArt = preload("res://tools/pixel_filter.gd")

# 47 Godot 3x3-minimal patterns: tl, tr, bl, br, column, row.
# Corner states: 0 outer, 1 vertical side, 2 horizontal side, 3 concave, 4 filled.
const WALL_PATTERNS: Array = [
	[0, 0, 0, 0, 0, 3], [0, 0, 1, 1, 0, 0], [0, 2, 0, 2, 1, 3], [0, 2, 1, 3, 1, 0],
	[0, 2, 1, 4, 8, 0], [1, 1, 0, 0, 0, 2], [1, 1, 1, 1, 0, 1], [1, 3, 0, 2, 1, 2],
	[1, 3, 1, 3, 1, 1], [1, 3, 1, 4, 4, 1], [1, 4, 0, 2, 8, 3], [1, 4, 1, 3, 4, 2],
	[1, 4, 1, 4, 8, 1], [2, 0, 2, 0, 3, 3], [2, 0, 3, 1, 3, 0], [2, 0, 4, 1, 11, 0],
	[2, 2, 2, 2, 2, 3], [2, 2, 3, 3, 2, 0], [2, 2, 3, 4, 5, 0], [2, 2, 4, 3, 6, 0],
	[2, 2, 4, 4, 10, 0], [3, 1, 2, 0, 3, 2], [3, 1, 3, 1, 3, 1], [3, 1, 4, 1, 7, 1],
	[3, 3, 2, 2, 2, 2], [3, 3, 3, 3, 2, 1], [3, 3, 3, 4, 7, 3], [3, 3, 4, 3, 4, 3],
	[3, 3, 4, 4, 9, 0], [3, 4, 2, 2, 5, 3], [3, 4, 3, 3, 7, 0], [3, 4, 3, 4, 8, 2],
	[3, 4, 4, 3, 9, 1], [3, 4, 4, 4, 5, 1], [4, 1, 2, 0, 11, 3], [4, 1, 3, 1, 7, 2],
	[4, 1, 4, 1, 11, 2], [4, 3, 2, 2, 6, 3], [4, 3, 3, 3, 4, 0], [4, 3, 3, 4, 10, 2],
	[4, 3, 4, 3, 11, 1], [4, 3, 4, 4, 6, 1], [4, 4, 2, 2, 9, 3], [4, 4, 3, 3, 10, 3],
	[4, 4, 3, 4, 5, 2], [4, 4, 4, 3, 6, 2], [4, 4, 4, 4, 9, 2],
]

var floors: Array[Texture2D] = []
var wall_cells: Array[Texture2D] = []
var wall_fill: Texture2D
var wall_lookup := {}
var skull: Texture2D
var crate: Texture2D
var hole: Texture2D
var rock: Texture2D
var mushroom: Texture2D
var moss: Texture2D
var puddle: Texture2D
var ember: Texture2D
var bones: Texture2D
var torch: Array[Texture2D] = []
var portal: Array[Texture2D] = []
var fire: Array[Texture2D] = []
var plague: Array[Texture2D] = []
var bless: Array[Texture2D] = []
var dust: Array[Texture2D] = []
var hex: Array[Texture2D] = []
var shock: Array[Texture2D] = []
var glow: Texture2D
var shadow: Texture2D
var select_ring: Texture2D
var mote: Texture2D
var panel: Texture2D
var button: Texture2D
var button_pressed: Texture2D
var keeps: Array = []
var clips := {}
var font: Font
var ready := false


func load_all() -> void:
    floors.clear()
    for i in range(1, 9):
        floors.append(_tex("res://art/tiles/floor_%d.png" % i))
    wall_cells.clear()
    wall_lookup.clear()
    for row in range(4):
        for col in range(12):
            wall_cells.append(_tex("res://art/tiles/wall_%d_%d.png" % [col, row]))
    for pattern in WALL_PATTERNS:
        var key := int(pattern[0]) + int(pattern[1]) * 5 + int(pattern[2]) * 25 + int(pattern[3]) * 125
        wall_lookup[key] = int(pattern[4]) + int(pattern[5]) * 12
    wall_fill = _tex("res://art/tiles/wall_fill.png")
    skull = _tex("res://art/tiles/skull.png")
    crate = _tex("res://art/tiles/crate.png")
    hole = _tex("res://art/tiles/hole.png")
    rock = _tex("res://art/tiles/rock.png")
    mushroom = _tex("res://art/tiles/mushroom.png")
    moss = _tex("res://art/tiles/moss.png")
    puddle = _tex("res://art/tiles/puddle.png")
    ember = _tex("res://art/tiles/ember.png")
    bones = _tex("res://art/tiles/bones.png")
    torch = _seq("res://art/fx/torch", 4)
    portal = _seq("res://art/fx/portal", 4)
    fire = _seq("res://art/fx/fire", 4)
    plague = _seq("res://art/fx/plague", 4)
    bless = _seq("res://art/fx/bless", 4)
    dust = _seq("res://art/fx/dust", 4)
    hex = _seq("res://art/fx/hex", 4)
    shock = _seq("res://art/fx/shock", 3)
    glow = _tex("res://art/fx/glow.png")
    shadow = _tex("res://art/fx/shadow.png")
    select_ring = _tex("res://art/fx/select.png")
    mote = _tex("res://art/fx/mote.png")
    panel = _tex("res://art/ui/panel.png")
    button = _tex("res://art/ui/button.png")
    button_pressed = _tex("res://art/ui/button_pressed.png")
    keeps.clear()
    for tier in range(3):
        var row: Array[Texture2D] = []
        for faction in ["azure", "crimson", "verdant"]:
            row.append(_tex("res://art/buildings/tier%d_%s.png" % [tier, faction]))
        keeps.append(row)
    clips.clear()
    for faction in ["azure", "crimson", "verdant"]:
        for role in ["warrior", "guard", "worker", "mage"]:
            _clip("%s_%s_idle" % [faction, role], "res://art/units/%s/%s_idle" % [faction, role], 4)
            _clip("%s_%s_run" % [faction, role], "res://art/units/%s/%s_run" % [faction, role], 4)
            _clip_if("%s_%s_hit" % [faction, role], "res://art/units/%s/%s_hit" % [faction, role], 1)
    _clip("shared_necro_idle", "res://art/units/shared/necro_idle", 4)
    _clip("shared_necro_run", "res://art/units/shared/necro_run", 4)
    _clip("shared_undead_idle", "res://art/units/shared/undead_idle", 4)
    _clip("shared_undead_run", "res://art/units/shared/undead_run", 4)
    for monster in ["goblin", "chort", "demon"]:
        _clip("monsters_%s_idle" % monster, "res://art/units/monsters/%s_idle" % monster, 4)
        _clip("monsters_%s_run" % monster, "res://art/units/monsters/%s_run" % monster, 4)
    font = load("res://fonts/m5x7.ttf")
    if font == null:
        push_error("SCRIPT ERROR missing texture res://fonts/m5x7.ttf")
    ready = true


func configure(item: CanvasItem) -> void:
    PixelArt.configure(item)


func wall_texture(x: int, y: int, is_wall: Callable) -> Texture2D:
    var n: bool = bool(is_wall.call(x, y - 1))
    var s: bool = bool(is_wall.call(x, y + 1))
    var e: bool = bool(is_wall.call(x + 1, y))
    var w: bool = bool(is_wall.call(x - 1, y))
    var ne: bool = bool(is_wall.call(x + 1, y - 1))
    var nw: bool = bool(is_wall.call(x - 1, y - 1))
    var se: bool = bool(is_wall.call(x + 1, y + 1))
    var sw: bool = bool(is_wall.call(x - 1, y + 1))
    var key := _corner(n, w, nw) + _corner(n, e, ne) * 5 + _corner(s, w, sw) * 25 + _corner(s, e, se) * 125
    if key == 624:
        return wall_fill
    var index: int = int(wall_lookup.get(key, 2 + 1 * 12))
    return wall_cells[index]


func keep_texture(level: int, team: int) -> Texture2D:
    var tier := 0
    if level >= 4:
        tier = 2
    elif level >= 2:
        tier = 1
    return keeps[tier][clampi(team, 0, 2)]


func unit_frames(team: int, profession: String, role: int, moving: bool, attacking: bool) -> Array:
    var faction := "shared"
    var role_name := "undead"
    var prof := profession.to_lower()
    if prof.find("undead") >= 0:
        role_name = "undead"
    elif prof.find("necro") >= 0:
        role_name = "necro"
    else:
        faction = ["azure", "crimson", "verdant"][clampi(team, 0, 2)]
        if prof.find("mage") >= 0:
            role_name = "mage"
        elif prof.find("worker") >= 0 or role == 1:
            role_name = "worker"
        elif prof.find("guardian") >= 0:
            role_name = "guard"
        else:
            role_name = "warrior"
    var anim := "idle"
    var hit_key := "%s_%s_hit" % [faction, role_name]
    if attacking and clips.has(hit_key):
        anim = "hit"
    elif moving and clips.has("%s_%s_run" % [faction, role_name]):
        anim = "run"
    return _frames("%s_%s_%s" % [faction, role_name, anim])


func monster_frames(kind: int, moving: bool) -> Array:
    var name := "goblin"
    if kind == 2:
        name = "demon"
    elif kind == 1:
        name = "chort"
    var anim := "run" if moving else "idle"
    return _frames("monsters_%s_%s" % [name, anim])


func frame_at(frames: Array, msec: int, speed: int) -> Texture2D:
    if frames.is_empty():
        return null
    var index := 0
    if frames.size() > 1:
        index = int(msec / speed) % frames.size()
    return frames[index]


func _frames(key: String) -> Array:
    if clips.has(key):
        return clips[key]
    return []


func _corner(a: bool, b: bool, c: bool) -> int:
    if not a and not b:
        return 0
    if a and not b:
        return 1
    if not a and b:
        return 2
    if not c:
        return 3
    return 4


func _tex(path: String) -> Texture2D:
    var tex: Texture2D = load(path)
    if tex == null:
        push_error("SCRIPT ERROR missing texture " + path)
    return tex


func _seq(path: String, count: int) -> Array[Texture2D]:
    var out: Array[Texture2D] = []
    for i in count:
        out.append(_tex("%s_%d.png" % [path, i]))
    return out


func _clip(key: String, path: String, count: int) -> void:
    clips[key] = _seq(path, count)


func _clip_if(key: String, path: String, count: int) -> void:
    if ResourceLoader.exists(path + "_0.png"):
        _clip(key, path, count)
