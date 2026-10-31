extends Node2D
const Art = preload("res://presentation.gd")
# Living Dungeon. Simulation is tile-based; pixels below are presentation only.
const GRID := Vector2i(96, 96)
const TILE := 32.0
const FACTIONS := [Color("#5bbdf1"), Color("#ed6969"), Color("#8fd878")]
const BIOME_TINT := [Color(0.94, 0.9, 1.04), Color(0.78, 1.08, 0.76), Color(1.1, 0.84, 0.72), Color(0.72, 0.9, 1.14)]
const TEAM_NAMES := ["Azure", "Crimson", "Verdant"]
const GIVEN_NAMES := ["Aldric","Veyra","Morwen","Kael","Eryn","Darian","Sable","Rhun","Nyx","Orin","Mara","Thorne"]
const TRAITS := ["Brave","Cautious","Greedy","Loyal","Curious","Ruthless"]
const GOALS := ["Protect","Explore","Gather","Glory"]
const PROFESSIONS := ["Warrior","Scout","Guardian","Worker","Hunter"]
const EQUIPMENT := ["Rusty sword","Iron spear","Leather armor","Hunter bow","Steel blade"]
var terrain: Array = []
var biomes: Array = []
var art
var facing := {}
var seen_hp := {}
var hit_flash := {}
var dust: CPUParticles2D
var vignette: ColorRect
var minimap: TextureRect
var minimap_img: Image
var minimap_tex: ImageTexture
var minimap_turn := 0
var fighters: Array = []
var settlements: Array = []
var resource_nodes: Array = []
var claims: Array = []
var next_unit_id := 1000
var stories: Array = []
var monsters: Array = []
var ruins: Array = []
var calamity := 0
var catastrophe_until := 0
var god_mode := 0
var god_team := 0
var god_power := 100
var god_button: Button
var god_team_button: Button
var effect_marks: Array = []
var tool_hint: Label
var turn := 0
var deaths := 0
var rng := RandomNumberGenerator.new()
var sim_accum := 0.0
var speed := 1
var selected := -1
var events := "The dungeon awakens."
var camera: Camera2D
var hud: CanvasLayer
var status: Label
var details: Label
var pause_button: Button
var drag_previous := Vector2.ZERO
var dragging := false
var seed_value := 0

func _ready() -> void:
    art = Art.new()
    art.load_all()
    art.configure(self)
    camera = Camera2D.new()
    camera.position = Vector2(30,30) * TILE
    camera.zoom = Vector2.ONE
    camera.enabled = true
    add_child(camera)
    hud = CanvasLayer.new()
    add_child(hud)
    var overlay := Control.new()
    overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
    hud.add_child(overlay)
    vignette = ColorRect.new()
    vignette.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    vignette.mouse_filter = Control.MOUSE_FILTER_IGNORE
    vignette.color = Color(1, 1, 1, 1)
    var vignette_mat := ShaderMaterial.new()
    vignette_mat.shader = load("res://shaders/vignette.gdshader")
    vignette.material = vignette_mat
    overlay.add_child(vignette)
    var header := PanelContainer.new()
    header.position = Vector2(10, 28)
    header.size = Vector2(700, 124)
    overlay.add_child(header)
    stylize_panel(header,Color("#131b28"))
    var headbox := VBoxContainer.new()
    header.add_child(headbox)
    var title := Label.new()
    title.text = "LIVING DUNGEON"
    theme_label(title, 48, Color("#f0d7a2"))
    headbox.add_child(title)
    status = Label.new()
    theme_label(status, 32, Color("#e6dcc8"))
    headbox.add_child(status)
    var map_border := PanelContainer.new()
    map_border.position = Vector2(530,164)
    map_border.size = Vector2(174,174)
    overlay.add_child(map_border)
    stylize_panel(map_border,Color("#171c2b"))
    minimap = TextureRect.new()
    minimap.custom_minimum_size = Vector2(166,166)
    minimap.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    minimap.stretch_mode = TextureRect.STRETCH_SCALE
    minimap.mouse_filter = Control.MOUSE_FILTER_IGNORE
    minimap.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
    map_border.add_child(minimap)
    minimap_img = Image.create(GRID.x,GRID.y,false,Image.FORMAT_RGBA8)
    minimap_tex = ImageTexture.create_from_image(minimap_img)
    minimap.texture = minimap_tex
    var bottom := PanelContainer.new()
    bottom.position = Vector2(8, 930)
    bottom.size = Vector2(704, 335)
    overlay.add_child(bottom)
    stylize_panel(bottom,Color("#121823"))
    var stack := VBoxContainer.new()
    bottom.add_child(stack)
    details = Label.new()
    theme_label(details, 32, Color("#f3e6c8"))
    details.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    stack.add_child(details)
    var buttons := HBoxContainer.new()
    stack.add_child(buttons)
    pause_button = Button.new()
    pause_button.text = "Pause"
    pause_button.pressed.connect(toggle_pause)
    buttons.add_child(pause_button)
    stylize_button(pause_button)
    var step_button := Button.new()
    step_button.text = "Speed x1"
    step_button.pressed.connect(change_speed)
    buttons.add_child(step_button)
    stylize_button(step_button)
    step_button.set_meta("speed_button", true)
    var new_button := Button.new()
    new_button.text = "New World"
    new_button.pressed.connect(generate)
    buttons.add_child(new_button)
    stylize_button(new_button)
    var powers := HBoxContainer.new()
    stack.add_child(powers)
    god_button = Button.new()
    god_button.text = "Select"
    god_button.pressed.connect(cycle_god_mode)
    powers.add_child(god_button)
    stylize_button(god_button)
    god_team_button = Button.new()
    god_team_button.text = "Blue"
    god_team_button.pressed.connect(cycle_god_team)
    powers.add_child(god_team_button)
    stylize_button(god_team_button)
    var action_hint := Label.new()
    action_hint.text = "Choose a power, then tap a tile on the map"
    theme_label(action_hint, 32, Color("#ffe0a3"))
    tool_hint = action_hint
    stack.add_child(action_hint)
    var save_button := Button.new()
    save_button.text = "Save"
    save_button.pressed.connect(save_world)
    buttons.add_child(save_button)
    stylize_button(save_button)
    var load_button := Button.new()
    load_button.text = "Load"
    load_button.pressed.connect(load_world)
    buttons.add_child(load_button)
    stylize_button(load_button)
    rng.randomize()
    _make_dust()
    generate()

func theme_label(label: Label, size: int, color: Color) -> void:
    label.add_theme_font_size_override("font_size", size)
    label.add_theme_color_override("font_color", color)
    if art != null and art.font != null:
        label.add_theme_font_override("font", art.font)

func stylize_panel(panel: PanelContainer, _fill: Color) -> void:
    var style := StyleBoxTexture.new()
    style.texture = art.panel
    style.texture_margin_left = 8
    style.texture_margin_top = 8
    style.texture_margin_right = 8
    style.texture_margin_bottom = 8
    style.set_content_margin_all(10)
    panel.add_theme_stylebox_override("panel", style)
    art.configure(panel)

func stylize_button(btn: Button) -> void:
    theme_button(btn)
    var normal := _button_style(art.button)
    var pressed := _button_style(art.button_pressed)
    btn.add_theme_stylebox_override("normal", normal)
    btn.add_theme_stylebox_override("hover", pressed)
    btn.add_theme_stylebox_override("pressed", pressed)
    btn.add_theme_stylebox_override("focus", normal)
    btn.custom_minimum_size = Vector2(0, 44)
    art.configure(btn)

func theme_button(btn: Button) -> void:
    btn.add_theme_font_size_override("font_size", 32)
    btn.add_theme_color_override("font_color", Color("#f4e6cc"))
    btn.add_theme_color_override("font_hover_color", Color("#fff4d8"))
    btn.add_theme_color_override("font_pressed_color", Color("#fff4d8"))
    if art != null and art.font != null:
        btn.add_theme_font_override("font", art.font)

func _button_style(texture: Texture2D) -> StyleBoxTexture:
    var style := StyleBoxTexture.new()
    style.texture = texture
    style.texture_margin_left = 6
    style.texture_margin_top = 6
    style.texture_margin_right = 6
    style.texture_margin_bottom = 6
    style.set_content_margin_all(6)
    return style

func _make_dust() -> void:
    dust = CPUParticles2D.new()
    dust.texture = art.mote
    dust.amount = 24
    dust.lifetime = 5.5
    dust.preprocess = 2.5
    dust.explosiveness = 0.0
    dust.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
    dust.emission_rect_extents = Vector2(460, 700)
    dust.direction = Vector2(0, -1)
    dust.spread = 28.0
    dust.gravity = Vector2(0, -4)
    dust.initial_velocity_min = 8.0
    dust.initial_velocity_max = 18.0
    dust.scale_amount_min = 1.0
    dust.scale_amount_max = 2.0
    dust.color = Color(1, 0.86, 0.62, 0.3)
    dust.local_coords = true
    camera.add_child(dust)
    art.configure(dust)

func generate() -> void:
    seed_value = rng.randi()
    rng.seed = seed_value
    turn = 0
    deaths = 0
    fighters.clear()
    terrain.clear()
    biomes.clear()
    settlements.clear()
    stories.clear()
    monsters.clear()
    ruins.clear()
    calamity = 0
    catastrophe_until = 0
    effect_marks.clear()
    god_power = 100
    resource_nodes.clear()
    claims.clear()
    for y in range(GRID.y):
        var row: Array = []
        var biome_row: Array = []
        for x in range(GRID.x):
            var boundary: bool = x == 0 or y == 0 or x == GRID.x - 1 or y == GRID.y - 1
            var zone: int = (int(x / 24) + 3 * int(y / 24) + int(x * y / 120)) % 4
            biome_row.append(zone)
            row.append(1 if boundary or rng.randf() < (0.08 if zone == 1 else 0.13) else 0)
        terrain.append(row)
        biomes.append(biome_row)
    var capitals := [Vector2i(15,15),Vector2i(80,16),Vector2i(49,79)]
    for team in range(3):
        var base: Vector2i = capitals[team]
        for yy in range(base.y - 3,base.y + 4):
            for xx in range(base.x - 3,base.x + 4):
                terrain[yy][xx] = 0
        settlements.append({"p":base, "team":team, "wood":25, "stone":20, "food":30, "level":1, "hp":35, "territory":8})
    for n in range(250):
        var p := Vector2i(rng.randi_range(2, GRID.x - 3),rng.randi_range(2,GRID.y - 3))
        if terrain[p.y][p.x] == 0:
            resource_nodes.append({"p":p, "type":rng.randi_range(0,2),"amount":rng.randi_range(6,18)})
    for ruin_idx in range(14):
        var rp := Vector2i(rng.randi_range(5,GRID.x - 6),rng.randi_range(5,GRID.y - 6))
        if terrain[rp.y][rp.x] == 0:
            ruins.append(rp)
            monsters.append({"p":rp,"old":rp,"hp":14 if ruin_idx == 0 else 5,"kind":2 if ruin_idx == 0 else ruin_idx % 2,"cooldown":0})
    for i in range(95):
        for attempt in range(300):
            var pos := Vector2i(rng.randi_range(1, GRID.x - 2), rng.randi_range(1, GRID.y - 2))
            if accessible(pos):
                fighters.append(make_person(pos,i % 3,i,1 if i % 4 == 0 else 0))
                break
    events = "Three factions enter the dungeon."
    update_minimap()
    selected = -1
    refresh()
    queue_redraw()

func accessible(p: Vector2i) -> bool:
    if p.x < 1 or p.y < 1 or p.x >= GRID.x - 1 or p.y >= GRID.y - 1:
        return false
    if terrain[p.y][p.x] != 0:
        return false
    for f in fighters:
        if f.hp > 0 and f.p == p:
            return false
    return true

func _process(delta: float) -> void:
    _track_hits()
    _tint_dust()
    if speed == 0:
        queue_redraw()
        return
    sim_accum += delta * speed
    while sim_accum >= 0.55:
        sim_accum -= 0.55
        simulate()
    queue_redraw()

func simulate() -> void:
    turn += 1
    god_power = mini(100, god_power + 1)
    effect_marks = effect_marks.filter(func(e): return int(e.until_ms) > Time.get_ticks_msec())
    update_economy()
    update_monsters()
    update_magic()
    fighters.shuffle()
    for f in fighters:
        f.old = f.p
        if f.hp <= 0:
            continue
        if int(f.get("role",0)) == 1 and worker_action(f):
            continue
        var enemy: Dictionary = {}
        var nearest := 9999
        for other in fighters:
            if other.hp <= 0 or other.team == f.team:
                continue
            var distance: int = abs(other.p.x - f.p.x) + abs(other.p.y - f.p.y)
            if distance < nearest:
                nearest = distance
                enemy = other
        if enemy.is_empty():
            continue
        if nearest == 1:
            enemy.hp -= 1
            f.xp += 1
            enemy.morale = maxi(0,int(enemy.morale)-3)
            if enemy.hp <= 0:
                deaths += 1
                f.kills += 1
                f.xp += 3
                f.memory = "Defeated " + str(enemy.name)
                f.rival = str(enemy.name)
                f.morale = mini(100,int(f.morale)+5)
                enemy.memory = "Fell to " + str(f.name)
                remember(str(f.name) + " defeated " + str(enemy.name))
                events = TEAM_NAMES[f.team] + " defeated " + TEAM_NAMES[enemy.team] + "."
        else:
            var move := Vector2i.ZERO
            if f.goal == "Survive" and int(f.morale) < 30 and nearest < 7:
                move = Vector2i(1 if f.p.x > enemy.p.x else -1,0)
                if not accessible(f.p + move):
                    move = Vector2i(0,1 if f.p.y > enemy.p.y else -1)
            elif nearest < 11:
                var diff: Vector2i = enemy.p - f.p
                if abs(diff.x) > abs(diff.y):
                    move.x = 1 if diff.x > 0 else -1
                else:
                    move.y = 1 if diff.y > 0 else -1
            else:
                move = [Vector2i.RIGHT, Vector2i.LEFT, Vector2i.UP, Vector2i.DOWN][rng.randi_range(0,3)]
            if accessible(f.p + move):
                f.p += move
            else:
                var random_move: Vector2i = [Vector2i.RIGHT, Vector2i.LEFT, Vector2i.UP, Vector2i.DOWN][rng.randi_range(0,3)]
                if accessible(f.p + random_move):
                    f.p += random_move
    fighters = fighters.filter(func(f): return f.hp > 0)
    # Nearby attackers besiege strongholds. Capturing a base transfers its
    # resources and territory, but does not modify any device data.
    for base in settlements:
        var attackers := [0,0,0]
        var defenders := 0
        for f in fighters:
            var range_to_base: int = abs(f.p.x - base.p.x) + abs(f.p.y - base.p.y)
            if range_to_base <= 3:
                if int(f.team) == int(base.team):
                    defenders += 1
                else:
                    attackers[int(f.team)] += 1
        var strongest := 0
        for team in range(1,3):
            if attackers[team] > attackers[strongest]:
                strongest = team
        if attackers[strongest] > defenders and attackers[strongest] > 0:
            base.hp -= maxi(1,attackers[strongest] - defenders)
            if int(base.hp) <= 0:
                var previous: int = int(base.team)
                base.team = strongest
                base.hp = 35
                base.wood = int(base.wood) / 2
                base.stone = int(base.stone) / 2
                base.food = int(base.food) / 2
                base.level = maxi(1,int(base.level)-1)
                events = TEAM_NAMES[strongest] + " captured a fortress from " + TEAM_NAMES[previous] + "!"
        elif defenders > 0:
            base.hp = mini(35,int(base.hp)+1)
    # Friends develop organically when living and working together.
    if turn % 18 == 0:
        for f in fighters:
            for other in fighters:
                if int(f.id) == int(other.id) or int(f.team) != int(other.team):
                    continue
                if (f.p - other.p).length_squared() <= 9:
                    var relation_key: String = str(other.id)
                    var score: int = int(f.relations.get(relation_key,0)) + 1
                    f.relations[relation_key] = mini(score,100)
                    if score == 4:
                        f.friend = str(other.name)
                        f.memory = "Befriended " + str(other.name)
                    break
    for f in fighters:
        if int(f.xp) >= int(f.level) * 10:
            f.level += 1
            f.hp = mini(5 + int(f.level),int(f.hp)+1)
            f.memory = "Reached level " + str(f.level)
        if turn % 12 == 0:
            f.morale = mini(100,int(f.morale)+1)
        if turn % 20 == 0:
            f.goal = choose_goal(f)
    if turn % 25 == 0 and fighters.size() < 120:
        for team in range(3):
            var parents := fighters.filter(func(f): return f.team == team)
            if parents.is_empty():
                continue
            var parent: Dictionary = parents[rng.randi_range(0, parents.size() - 1)]
            var newpos: Vector2i = parent.p + Vector2i(rng.randi_range(-1,1), rng.randi_range(-1,1))
            if accessible(newpos):
                fighters.append(make_person(newpos,team,next_unit_id,0))
                next_unit_id += 1
    refresh()

func update_monsters() -> void:
    for monster in monsters:
        if int(monster.hp) <= 0:
            continue
        monster.old = monster.p
        var target: Dictionary = {}
        var best := 9999
        for f in fighters:
            if int(f.hp) <= 0:
                continue
            var d: int = abs(f.p.x - monster.p.x) + abs(f.p.y - monster.p.y)
            if d < best:
                best = d
                target = f
        if target.is_empty():
            continue
        if best <= 1:
            target.hp -= 2 if int(monster.kind) == 2 else 1
            if int(target.hp) <= 0:
                deaths += 1
                remember(str(target.name) + " was slain by a dungeon beast")
                events = "A monster killed " + str(target.name)
        elif best < 9:
            var diff: Vector2i = target.p - monster.p
            var step := Vector2i.ZERO
            if abs(diff.x) >= abs(diff.y):
                step.x = 1 if diff.x > 0 else -1
            else:
                step.y = 1 if diff.y > 0 else -1
            if accessible(monster.p + step) and not monster_at(monster.p + step):
                monster.p += step
    if turn % 24 == 0:
        for monster in monsters:
            if int(monster.hp) <= 0:
                continue
            for f in fighters:
                if int(f.hp) > 0 and (f.p - monster.p).length_squared() <= 2:
                    monster.hp -= 1
                    if int(monster.hp) <= 0:
                        f.xp += 8
                        f.memory = "Slayed a dungeon beast"
                        remember(str(f.name) + " vanquished a beast")
                    break
    monsters = monsters.filter(func(m): return int(m.hp) > 0)
    if turn % 55 == 0 and monsters.size() < 18 and not ruins.is_empty():
        var spawn: Vector2i = ruins[rng.randi_range(0,ruins.size()-1)]
        if accessible(spawn) and not monster_at(spawn):
            monsters.append({"p":spawn,"old":spawn,"hp":6,"kind":rng.randi_range(0,1),"cooldown":0})

func monster_at(pos: Vector2i) -> bool:
    for m in monsters:
        if int(m.hp) > 0 and m.p == pos:
            return true
    return false

func update_magic() -> void:
    if turn % 14 == 0:
        var candidates: Array = fighters.filter(func(f): return int(f.hp) > 0 and str(f.profession) == "Mage")
        for mage in candidates:
            var nearby: Array = fighters.filter(func(f): return int(f.hp) > 0 and int(f.team) != int(mage.team) and (f.p - mage.p).length_squared() <= 25)
            if not nearby.is_empty():
                var victim: Dictionary = nearby[rng.randi_range(0,nearby.size()-1)]
                victim.hp -= 2
                mage.xp += 2
                mage.memory = "Cast a hex on " + str(victim.name)
                events = str(mage.name) + " casts a shadow hex!"
                effect_marks.append({"p": victim.p, "kind": 7, "until_ms": Time.get_ticks_msec() + 1100})
    if turn % 35 == 0:
        for necro in fighters:
            if str(necro.profession) != "Necromancer" or int(necro.hp) <= 0:
                continue
            var spawn: Vector2i = necro.p + [Vector2i.UP,Vector2i.DOWN,Vector2i.LEFT,Vector2i.RIGHT][rng.randi_range(0,3)]
            if accessible(spawn):
                fighters.append(make_person(spawn,int(necro.team),next_unit_id,0))
                fighters[-1].name = "Raised " + str(next_unit_id)
                fighters[-1].profession = "Undead"
                fighters[-1].trait = "Loyal"
                fighters[-1].memory = "Raised by " + str(necro.name)
                necro.memory = "Raised an undead servant"
                necro.xp += 3
                next_unit_id += 1
                events = str(necro.name) + " raises an undead servant!"
                effect_marks.append({"p": spawn, "kind": 1, "until_ms": Time.get_ticks_msec() + 1100})
    if turn % 90 == 0:
        calamity = rng.randi_range(1,3)
        catastrophe_until = turn + 22
        events = ["", "PLAGUE spreads", "BLOOD MOON rises", "ARCANE STORM erupts"][calamity]
        remember(events)
    if calamity != 0 and turn <= catastrophe_until and turn % 5 == 0:
        for f in fighters:
            if rng.randf() < 0.04:
                f.hp -= 1
    if turn > catastrophe_until:
        calamity = 0

func make_person(pos: Vector2i, team: int, uid: int, role: int) -> Dictionary:
    var first: String = GIVEN_NAMES[rng.randi_range(0,GIVEN_NAMES.size()-1)]
    var person: Dictionary = {
        "p":pos,"old":pos,"team":team,"hp":5,"id":uid,"kills":0,"role":role,
        "name":first + " " + str(uid),"trait":TRAITS[rng.randi_range(0,TRAITS.size()-1)],
        "goal":GOALS[rng.randi_range(0,GOALS.size()-1)],
        "xp":0,"level":1,"morale":rng.randi_range(50,90),
        "memory":"Born in " + TEAM_NAMES[team],"rival":"","friend":"",
        "profession":"Worker" if role == 1 else (("Necromancer" if rng.randf() < 0.035 else "Mage") if rng.randf() < 0.16 else PROFESSIONS[rng.randi_range(0,2)]),
        "equipment":EQUIPMENT[rng.randi_range(0,EQUIPMENT.size()-1)],
        "relations":{}, "wanderlust":rng.randi_range(0,100)
    }
    return person

func choose_goal(f: Dictionary) -> String:
    if int(f.morale) < 30:
        return "Survive"
    if int(f.role) == 1:
        return "Gather"
    if int(f.kills) >= 2:
        return "Glory"
    if str(f.trait) == "Curious":
        return "Explore"
    if str(f.trait) == "Loyal":
        return "Protect"
    return GOALS[rng.randi_range(0,GOALS.size()-1)]

func remember(line: String) -> void:
    stories.push_back("T" + str(turn) + ": " + line)
    if stories.size() > 80:
        stories.pop_front()

func worker_action(f: Dictionary) -> bool:
    var home: Dictionary = {}
    for base in settlements:
        if int(base.team) == int(f.team):
            home = base
            break
    if home.is_empty():
        return false
    var target: Dictionary = {}
    var nearest := 99999
    for node in resource_nodes:
        if int(node.amount) <= 0:
            continue
        var d: int = abs(node.p.x - f.p.x) + abs(node.p.y - f.p.y)
        var home_distance: int = abs(node.p.x - home.p.x) + abs(node.p.y - home.p.y)
        if home_distance < 17 and d < nearest:
            nearest = d
            target = node
    if target.is_empty():
        return false
    if nearest <= 1:
        target.amount -= 1
        var kind: int = int(target.type)
        if kind == 0:
            home.wood += 1
        elif kind == 1:
            home.stone += 1
        else:
            home.food += 2
        return true
    var diff: Vector2i = target.p - f.p
    var move := Vector2i.ZERO
    if abs(diff.x) > abs(diff.y):
        move.x = 1 if diff.x > 0 else -1
    else:
        move.y = 1 if diff.y > 0 else -1
    if accessible(f.p + move):
        f.p += move
    return true

func update_economy() -> void:
    if turn % 8 != 0:
        return
    for base in settlements:
        var team: int = int(base.team)
        var population := 0
        for fighter in fighters:
            if int(fighter.team) == team and int(fighter.hp) > 0:
                population += 1
        base.food = maxi(0,int(base.food) - maxi(1,int(population / 12)))
        if int(base.wood) >= 12 and int(base.stone) >= 10 and int(base.level) < 5:
            base.wood -= 12
            base.stone -= 10
            base.level += 1
            base.territory += 2
            events = TEAM_NAMES[team] + " expands their stronghold to tier " + str(base.level)
        if int(base.food) >= 8 and population < 48:
            var spawn: Vector2i = base.p + Vector2i(rng.randi_range(-3,3),rng.randi_range(-3,3))
            if accessible(spawn):
                base.food -= 8
                fighters.append(make_person(spawn,team,next_unit_id,1 if population % 4 == 0 else 0))
                next_unit_id += 1

func update_minimap() -> void:
    if minimap_img == null or terrain.size() != GRID.y:
        return
    var shades := [Color("#3c343c"), Color("#2a4a32"), Color("#5a382c"), Color("#243e52")]
    for y in range(GRID.y):
        for x in range(GRID.x):
            var color: Color = Color("#14110f") if terrain[y][x] == 1 else shades[int(biomes[y][x])]
            minimap_img.set_pixel(x,y,color)
    for b in settlements:
        var bp: Vector2i = b.p
        minimap_img.set_pixel(bp.x,bp.y,FACTIONS[int(b.team)])
    for f in fighters:
        var fp: Vector2i = f.p
        if fp.x >= 0 and fp.x < GRID.x and fp.y >= 0 and fp.y < GRID.y:
            minimap_img.set_pixel(fp.x,fp.y,FACTIONS[int(f.team)])
    minimap_tex.update(minimap_img)

func refresh() -> void:
    minimap_turn += 1
    if minimap_turn % 5 == 0:
        update_minimap()
    if status == null:
        return
    var counts := [0,0,0]
    for f in fighters:
        counts[f.team] += 1
    status.text = "TURN %d  |  KILLS %d  |  BLUE %d  RED %d  GREEN %d" % [turn, deaths, counts[0], counts[1], counts[2]]
    var economy := ""
    for b in settlements:
        economy += TEAM_NAMES[int(b.team)].substr(0,1) + " F" + str(b.food) + " W" + str(b.wood) + " S" + str(b.stone) + "   "
    details.text = events + "\n" + economy + "GOD " + str(god_power)
    if selected >= 0:
        for f in fighters:
            if f.id == selected:
                details.text = "%s L%d %s | HP %d | %s\n%s | %s" % [f.name, f.level, f.profession, f.hp, f.goal, f.trait, f.memory]
                break
    queue_redraw()

func _track_hits() -> void:
    var now := Time.get_ticks_msec()
    for f in fighters:
        var id := int(f.id)
        var hp := int(f.hp)
        if seen_hp.has(id) and hp < int(seen_hp[id]):
            hit_flash[id] = now + 140
        seen_hp[id] = hp
    for m in monsters:
        var hp := int(m.hp)
        if m.has("seen_hp") and hp < int(m.seen_hp):
            m["flash_until"] = now + 140
        m["seen_hp"] = hp

func _tint_dust() -> void:
    if dust == null:
        return
    if calamity == 1:
        dust.color = Color(0.55, 1.0, 0.4, 0.45)
    elif calamity == 2:
        dust.color = Color(1.0, 0.32, 0.32, 0.42)
    elif calamity == 3:
        dust.color = Color(0.55, 0.75, 1.0, 0.48)
    else:
        dust.color = Color(1, 0.86, 0.62, 0.28)

func cell_is_wall(cx: int, cy: int) -> bool:
    if cx < 0 or cy < 0 or cx >= GRID.x or cy >= GRID.y:
        return true
    return int(terrain[cy][cx]) == 1

func is_torch(x: int, y: int) -> bool:
    if not cell_is_wall(x, y):
        return false
    if y + 1 >= GRID.y or cell_is_wall(x, y + 1):
        return false
    return (x * 13 + y * 29) % 7 == 0

func _draw() -> void:
    if art == null or not art.ready or terrain.is_empty():
        return
    var world_span: Vector2 = get_viewport_rect().size / camera.zoom
    var start_world: Vector2 = camera.get_screen_center_position() - world_span * 0.5
    var xmin: int = maxi(0, floori(start_world.x / TILE) - 2)
    var ymin: int = maxi(0, floori(start_world.y / TILE) - 2)
    var xmax: int = mini(GRID.x, ceili((start_world.x + world_span.x) / TILE) + 3)
    var ymax: int = mini(GRID.y, ceili((start_world.y + world_span.y) / TILE) + 3)
    var lights := _collect_lights(xmin, ymin, xmax, ymax)
    var claims: Array = []
    var now := Time.get_ticks_msec()
    var wall_fn := Callable(self, "cell_is_wall")
    for y in range(ymin, ymax):
        for x in range(xmin, xmax):
            var origin := Vector2(x, y) * TILE
            var mod := _shade(x, y, lights, claims)
            var floor_tex: Texture2D = art.floors[(x * 3 + y * 5) % art.floors.size()]
            draw_texture_rect(floor_tex, Rect2(origin, Vector2(TILE, TILE)), false, mod)
            if cell_is_wall(x, y):
                var wall_tex: Texture2D = art.wall_texture(x, y, wall_fn)
                if wall_tex:
                    draw_texture_rect(wall_tex, Rect2(origin, Vector2(TILE, TILE)), false, mod)
            else:
                _draw_floor_decal(x, y, origin, mod)
    for node in resource_nodes:
        if int(node.amount) <= 0:
            continue
        var np: Vector2i = node.p
        if np.x < xmin or np.y < ymin or np.x >= xmax or np.y >= ymax:
            continue
        var tex: Texture2D = art.crate
        if int(node.type) == 1:
            tex = art.rock
        elif int(node.type) == 2:
            tex = art.mushroom
        var foot := Vector2(np) * TILE + Vector2(TILE * 0.5, TILE - 1.0)
        _draw_sprite(tex, foot, _shade(np.x, np.y, lights, claims), false)
    for ruin in ruins:
        if ruin.x < xmin or ruin.y < ymin or ruin.x >= xmax or ruin.y >= ymax:
            continue
        var origin := Vector2(ruin) * TILE
        draw_texture_rect(art.hole, Rect2(origin, Vector2(TILE, TILE)), false, _shade(ruin.x, ruin.y, lights, claims))
    _draw_light_pools(lights)
    for base in settlements:
        var color: Color = FACTIONS[int(base.team)]
        color.a = 0.28
        var center := Vector2(base.p) * TILE + Vector2(TILE * 0.5, TILE * 0.5)
        draw_arc(center, float(base.territory) * TILE, 0, TAU, 72, color, 2.0)
    var tween := clampf(sim_accum / 0.55, 0.0, 1.0)
    tween = tween * tween * (3.0 - 2.0 * tween)
    var actors: Array = []
    for base in settlements:
        actors.append({"y": float(base.p.y), "kind": "keep", "d": base})
    for ruin in ruins:
        actors.append({"y": float(ruin.y) + 0.15, "kind": "portal", "d": ruin})
    for m in monsters:
        if int(m.hp) <= 0:
            continue
        var my := lerpf(float(m.old.y), float(m.p.y), tween)
        actors.append({"y": my, "kind": "monster", "d": m})
    for f in fighters:
        if int(f.hp) <= 0:
            continue
        var fy := lerpf(float(f.old.y), float(f.p.y), tween)
        actors.append({"y": fy, "kind": "unit", "d": f})
    actors.sort_custom(func(a, b): return float(a.y) < float(b.y))
    for actor in actors:
        match str(actor.kind):
            "keep":
                _draw_keep(actor.d, lights, claims)
            "portal":
                _draw_portal(actor.d, now, lights, claims)
            "monster":
                _draw_monster(actor.d, tween, now, lights, claims)
            "unit":
                _draw_unit(actor.d, tween, now, lights, claims)
    for mark in effect_marks:
        _draw_effect(mark, now)
    if calamity == 3 and now % 680 < 90:
        _draw_bolts(now)
    for x in range(xmin, xmax):
        for y in range(ymin, ymax):
            if is_torch(x, y):
                var frame: Texture2D = art.frame_at(art.torch, now, 140)
                var foot := Vector2(x, y) * TILE + Vector2(TILE * 0.5, TILE - 2.0)
                _draw_sprite(frame, foot, Color(1.15, 1.05, 0.9), false)

func _draw_floor_decal(x: int, y: int, origin: Vector2, mod: Color) -> void:
    var roll := (x * 17 + y * 31) % 47
    var decal: Texture2D = null
    var biome := int(biomes[y][x]) if biomes.size() == GRID.y else 0
    if roll == 0:
        decal = art.skull
    elif roll == 1:
        decal = art.bones
    elif roll == 2 and biome == 1:
        decal = art.moss
    elif roll == 3 and biome == 2:
        decal = art.ember
    elif roll == 4 and biome == 3:
        decal = art.puddle
    elif roll == 5 and biome == 1:
        decal = art.moss
    if decal:
        draw_texture_rect(decal, Rect2(origin, Vector2(TILE, TILE)), false, mod)

func _draw_keep(base: Dictionary, lights: Array, claims: Array) -> void:
    var tex: Texture2D = art.keep_texture(int(base.level), int(base.team))
    var foot := Vector2(base.p) * TILE + Vector2(TILE * 0.5, TILE - 2.0)
    var mod := _shade(int(base.p.x), int(base.p.y), lights, claims)
    _draw_ground_shadow(foot, float(tex.get_width()) * 1.4)
    _draw_sprite(tex, foot, mod, false)

func _draw_portal(ruin: Vector2i, now: int, lights: Array, claims: Array) -> void:
    var frame: Texture2D = art.frame_at(art.portal, now, 160)
    var foot := Vector2(ruin) * TILE + Vector2(TILE * 0.5, TILE - 1.0)
    _draw_sprite(frame, foot, _shade(ruin.x, ruin.y, lights, claims), false)

func _draw_monster(m: Dictionary, tween: float, now: int, lights: Array, claims: Array) -> void:
    var moving: bool = m.p != m.old
    var frames: Array = art.monster_frames(int(m.kind), moving)
    var tex: Texture2D = art.frame_at(frames, now, 130 if moving else 240)
    if tex == null:
        return
    var pos := Vector2(m.old).lerp(Vector2(m.p), tween)
    var foot := pos * TILE + Vector2(TILE * 0.5, TILE - 1.0)
    var face := 1
    if m.p.x < m.old.x:
        face = -1
    elif m.p.x > m.old.x:
        face = 1
    var mod := _shade(int(m.p.x), int(m.p.y), lights, claims)
    if int(m.get("flash_until", 0)) > now:
        mod = Color(1.8, 1.7, 1.6)
    _draw_ground_shadow(foot, float(tex.get_width()) * 1.5)
    if face < 0:
        foot.x -= 2.0
    _draw_sprite(tex, foot, mod, face < 0)

func _draw_unit(f: Dictionary, tween: float, now: int, lights: Array, claims: Array) -> void:
    var moving: bool = f.p != f.old
    var attacking := _in_melee(f)
    var frames: Array = art.unit_frames(int(f.team), str(f.profession), int(f.get("role", 0)), moving, attacking)
    var speed_ms := 120 if moving else (160 if attacking else 260)
    var tex: Texture2D = art.frame_at(frames, now, speed_ms)
    if tex == null:
        return
    var id := int(f.id)
    if f.p.x < f.old.x:
        facing[id] = -1
    elif f.p.x > f.old.x:
        facing[id] = 1
    elif not facing.has(id):
        facing[id] = 1
    var face := int(facing[id])
    var pos := Vector2(f.old).lerp(Vector2(f.p), tween)
    var foot := pos * TILE + Vector2(TILE * 0.5, TILE - 1.0)
    if attacking:
        foot.x += float(face) * 3.0
    var mod := _shade(int(f.p.x), int(f.p.y), lights, claims)
    if int(hit_flash.get(id, 0)) > now:
        mod = Color(1.85, 1.75, 1.6)
    _draw_ground_shadow(foot, float(tex.get_width()) * 1.6)
    _draw_sprite(tex, foot, mod, face < 0)
    if int(f.hp) < 5:
        var bar := foot + Vector2(-12, -float(tex.get_height()) * 2.0 - 6.0)
        draw_rect(Rect2(bar, Vector2(24, 3)), Color("#3a1818"))
        draw_rect(Rect2(bar, Vector2(24.0 * float(f.hp) / 5.0, 3)), Color("#b6e08a"))
    if f.id == selected and art.select_ring:
        var ring := Rect2(foot.x - 18.0, foot.y - 28.0, 36, 36)
        draw_texture_rect(art.select_ring, ring, false, Color(1, 0.92, 0.7, 0.95))

func _draw_effect(mark: Dictionary, now: int) -> void:
    var left := clampf(float(int(mark.until_ms) - now) / 1100.0, 0.0, 1.0)
    var center := Vector2(mark.p) * TILE + Vector2(TILE * 0.5, TILE * 0.5)
    var kind := int(mark.kind)
    var frames: Array = art.fire
    var tint := Color(1, 0.7, 0.3, left)
    if kind == 3:
        frames = art.bless
        tint = Color(1, 0.9, 0.5, left)
    elif kind == 6 or kind == 7:
        frames = art.plague if kind == 6 else art.hex
        tint = Color(0.7, 1, 0.5, left) if kind == 6 else Color(0.8, 0.5, 1, left)
    elif kind == 5:
        frames = art.dust
        tint = Color(0.9, 0.8, 0.7, left)
    elif kind == 1 or kind == 2:
        frames = art.bless if kind == 1 else art.hex
        tint = Color(0.6, 0.85, 1, left) if kind == 1 else Color(1, 0.45, 0.4, left)
    var frame: Texture2D = art.frame_at(frames, now, 90)
    var size := lerpf(28.0, 78.0, 1.0 - left)
    if frame:
        draw_texture_rect(frame, Rect2(center - Vector2(size, size) * 0.5, Vector2(size, size)), false, tint)
    if kind == 4 and not art.shock.is_empty():
        var ring: Texture2D = art.shock[mini(art.shock.size() - 1, int((1.0 - left) * float(art.shock.size())))]
        var shock := lerpf(20.0, 96.0, 1.0 - left)
        draw_texture_rect(ring, Rect2(center - Vector2(shock, shock), Vector2(shock * 2.0, shock * 2.0)), false, Color(1, 0.8, 0.4, left))
        draw_texture_rect(art.glow, Rect2(center - Vector2(48, 48), Vector2(96, 96)), false, Color(1, 0.45, 0.15, 0.55 * left))

func _draw_bolts(now: int) -> void:
    var origin := camera.get_screen_center_position()
    for i in range(3):
        var x := origin.x + float((now / 40 + i * 90) % 220) - 110.0
        draw_line(Vector2(x, origin.y - 180), Vector2(x + 18, origin.y + 40), Color(0.75, 0.85, 1, 0.55), 2.0)

func _draw_light_pools(lights: Array) -> void:
    for light in lights:
        var center: Vector2 = light.pos * TILE
        var radius: float = float(light.radius) * TILE
        var color: Color = light.color
        color.a *= 0.14
        draw_texture_rect(art.glow, Rect2(center - Vector2(radius, radius), Vector2(radius * 2.0, radius * 2.0)), false, color)

func _draw_sprite(tex: Texture2D, foot: Vector2, mod: Color, flip: bool) -> void:
    if tex == null:
        return
    var w := float(tex.get_width()) * 2.0
    var h := float(tex.get_height()) * 2.0
    var origin := Vector2(foot.x - w * 0.5, foot.y - h)
    if flip:
        draw_set_transform(Vector2(origin.x + w, origin.y), 0.0, Vector2(-1, 1))
        draw_texture_rect(tex, Rect2(Vector2.ZERO, Vector2(w, h)), false, mod)
        draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
    else:
        draw_texture_rect(tex, Rect2(origin, Vector2(w, h)), false, mod)

func _draw_ground_shadow(foot: Vector2, width: float) -> void:
    var h := maxf(6.0, width * 0.22)
    draw_texture_rect(art.shadow, Rect2(foot.x - width * 0.5, foot.y - h * 0.6, width, h), false, Color(1, 1, 1, 0.8))

func _collect_lights(xmin: int, ymin: int, xmax: int, ymax: int) -> Array:
    var lights: Array = []
    for base in settlements:
        lights.append({
            "pos": Vector2(base.p) + Vector2(0.5, 0.45),
            "radius": 4.2 + float(base.level) * 0.7,
            "color": Color(1.0, 0.72, 0.42, 1.0),
            "power": 0.85,
        })
    for ruin in ruins:
        lights.append({
            "pos": Vector2(ruin) + Vector2(0.5, 0.5),
            "radius": 3.2,
            "color": Color(0.72, 0.38, 1.0, 1.0),
            "power": 0.7,
        })
    for mark in effect_marks:
        var kind := int(mark.kind)
        var color := Color(1, 0.6, 0.3)
        if kind == 3:
            color = Color(1, 0.9, 0.45)
        elif kind == 6:
            color = Color(0.5, 1, 0.35)
        elif kind == 7 or kind == 2:
            color = Color(0.7, 0.4, 1)
        elif kind == 1:
            color = Color(0.5, 0.8, 1)
        lights.append({"pos": Vector2(mark.p) + Vector2(0.5, 0.5), "radius": 3.4, "color": color, "power": 0.9})
    var torches := 0
    for y in range(ymin, ymax):
        for x in range(xmin, xmax):
            if torches >= 18:
                break
            if is_torch(x, y):
                lights.append({
                    "pos": Vector2(x, y) + Vector2(0.5, 0.72),
                    "radius": 3.3,
                    "color": Color(1.0, 0.62, 0.28, 1.0),
                    "power": 0.75,
                })
                torches += 1
    return lights

func _shade(x: int, y: int, lights: Array, claims: Array) -> Color:
    var r := 0.84
    var g := 0.8
    var b := 0.9
    var px := float(x) + 0.5
    var py := float(y) + 0.5
    for light in lights:
        var lp: Vector2 = light.pos
        var dx := px - lp.x
        var dy := py - lp.y
        var rad: float = light.radius
        var d2 := dx * dx + dy * dy
        if d2 >= rad * rad:
            continue
        var t := 1.0 - sqrt(d2) / rad
        t *= t * float(light.power) * 0.55
        var color: Color = light.color
        r += color.r * t
        g += color.g * t
        b += color.b * t
    if calamity == 1:
        g += 0.08
        r -= 0.04
    elif calamity == 2:
        r += 0.12
        b -= 0.06
    elif calamity == 3:
        b += 0.1
        r -= 0.02
    var biome := 0
    if biomes.size() == GRID.y and x >= 0 and y >= 0 and x < GRID.x and y < GRID.y:
        biome = clampi(int(biomes[y][x]), 0, 3)
    var tint: Color = BIOME_TINT[biome]
    r *= tint.r
    g *= tint.g
    b *= tint.b
    return Color(clampf(r, 0.45, 1.2), clampf(g, 0.45, 1.2), clampf(b, 0.45, 1.2), 1.0)

func _in_melee(f: Dictionary) -> bool:
    for other in fighters:
        if int(other.hp) <= 0 or int(other.team) == int(f.team):
            continue
        if absi(int(other.p.x) - int(f.p.x)) + absi(int(other.p.y) - int(f.p.y)) == 1:
            return true
    for m in monsters:
        if int(m.hp) <= 0:
            continue
        if absi(int(m.p.x) - int(f.p.x)) + absi(int(m.p.y) - int(f.p.y)) == 1:
            return true
    return false


func cycle_god_mode() -> void:
    god_mode = (god_mode + 1) % 7
    god_button.text = ["Select","Spawn","Monster","Bless","Strike","Wall","Plague"][god_mode]
    var costs := [0,12,20,8,15,5,25]
    var descriptions := ["Inspect NPCs","Summon faction soldier","Create a powerful monster","Heal allies in a 3-tile area","Meteor: 3-tile explosion","Add or remove a stone wall","Unleash a plague"]
    tool_hint.text = descriptions[god_mode] + "   |   Cost: " + str(costs[god_mode]) + "   |   Tap map"
    events = "Selected: " + god_button.text
    refresh()

func cycle_god_team() -> void:
    god_team = (god_team + 1) % 3
    god_team_button.text = ["Blue","Red","Green"][god_team]
    refresh()

func use_god_power(p: Vector2i) -> void:
    if p.x < 1 or p.y < 1 or p.x >= GRID.x-1 or p.y >= GRID.y-1:
        return
    var cost: int = [0,12,20,8,15,5,25][god_mode]
    if god_power < cost:
        events = "Not enough divine energy (" + str(cost) + ")"
        refresh()
        return
    if god_mode == 1:
        if not accessible(p):
            return
        fighters.append(make_person(p,god_team,next_unit_id,0))
        fighters[-1].memory = "Summoned by the observer"
        next_unit_id += 1
    elif god_mode == 2:
        if not accessible(p) or monster_at(p):
            return
        monsters.append({"p":p,"old":p,"hp":12,"kind":2,"cooldown":0})
    elif god_mode == 3:
        for f in fighters:
            if (f.p-p).length_squared() <= 9 and int(f.team) == god_team:
                f.hp = mini(12,int(f.hp)+4)
                f.morale = 100
                f.xp += 5
    elif god_mode == 4:
        for f in fighters:
            if (f.p-p).length_squared() <= 9:
                f.hp -= 5
        for m in monsters:
            if (m.p-p).length_squared() <= 9:
                m.hp -= 8
    elif god_mode == 5:
        if occupied_tile(p) or monster_at(p):
            events = "Tile occupied; choose an empty square"
            refresh()
            return
        terrain[p.y][p.x] = 1 if terrain[p.y][p.x] == 0 else 0
    elif god_mode == 6:
        calamity = 1
        catastrophe_until = turn + 40
    god_power -= cost
    effect_marks.append({"p":p,"kind":god_mode,"until_ms":Time.get_ticks_msec()+1350})
    events = ["","A hero arrives","A boss manifests","Divine blessing","Meteor strike","Terrain reshaped","Plague unleashed"][god_mode]
    remember(events)
    refresh()
    queue_redraw()

func occupied_tile(p: Vector2i) -> bool:
    for f in fighters:
        if f.hp > 0 and f.p == p:
            return true
    for b in settlements:
        if b.p == p:
            return true
    return false

func toggle_pause() -> void:
    speed = 0 if speed != 0 else 1
    pause_button.text = "Resume" if speed == 0 else "Pause"

func change_speed() -> void:
    speed = 2 if speed == 1 else (4 if speed == 2 else 1)
    if speed == 0:
        speed = 1
    var speed_button := _find_speed_button(hud)
    if speed_button:
        speed_button.text = "Speed x%d" % speed

func _find_speed_button(node: Node) -> Button:
    if node is Button and node.has_meta("speed_button"):
        return node
    for child in node.get_children():
        var found := _find_speed_button(child)
        if found:
            return found
    return null

func save_world() -> void:
    var actors: Array = []
    for f in fighters:
        actors.append({"x":f.p.x,"y":f.p.y,"team":f.team,"hp":f.hp,"id":f.id,"kills":f.kills,"role":f.get("role",0),"name":f.name,"trait":f.trait,"goal":f.goal,"xp":f.xp,"level":f.level,"morale":f.morale,"memory":f.memory,"rival":f.rival,"friend":f.friend,"profession":f.profession,"equipment":f.equipment,"relations":f.relations,"wanderlust":f.wanderlust})
    var bases: Array = []
    for b in settlements:
        bases.append({"x":b.p.x,"y":b.p.y,"team":b.team,"wood":b.wood,"stone":b.stone,"food":b.food,"level":b.level,"hp":b.hp,"territory":b.territory})
    var nodes: Array = []
    for n in resource_nodes:
        nodes.append({"x":n.p.x,"y":n.p.y,"type":n.type,"amount":n.amount})
    var data := {"seed":seed_value,"terrain":terrain,"fighters":actors,"bases":bases,"nodes":nodes,"turn":turn,"deaths":deaths,"next_id":next_unit_id,"stories":stories,"monsters":monsters.map(func(m): return {"x":m.p.x,"y":m.p.y,"hp":m.hp,"kind":m.kind}),"ruins":ruins.map(func(p): return [p.x,p.y]),"calamity":calamity,"catastrophe_until":catastrophe_until,"god_power":god_power,"biomes":biomes}
    var file := FileAccess.open("user://world.json",FileAccess.WRITE)
    if file:
        file.store_string(JSON.stringify(data))
        events = "World saved."
    else:
        events = "Save failed."
    refresh()

func load_world() -> void:
    if not FileAccess.file_exists("user://world.json"):
        events = "No saved world yet."
        refresh()
        return
    var file := FileAccess.open("user://world.json",FileAccess.READ)
    if file == null:
        events = "Cannot read save."
        refresh()
        return
    var data = JSON.parse_string(file.get_as_text())
    if not data is Dictionary or not data.has("terrain") or not data.has("fighters"):
        events = "Invalid save."
        refresh()
        return
    if data.terrain.size() != GRID.y:
        events = "Old world size differs. Starting a new world."
        generate()
        return
    terrain = data.terrain
    biomes = data.get("biomes",[])
    if biomes.size() != GRID.y:
        biomes.clear()
        for y in range(GRID.y):
            var row: Array = []
            for x in range(GRID.x):
                row.append((int(x / 24) + 3 * int(y / 24)) % 4)
            biomes.append(row)
    fighters.clear()
    for f in data.fighters:
        var pos := Vector2i(int(f.x),int(f.y))
        var person: Dictionary = make_person(pos,int(f.team),int(f.id),int(f.get("role",0)))
        person.hp = int(f.hp)
        person.kills = int(f.kills)
        person.name = str(f.get("name",person.name))
        person.trait = str(f.get("trait",person.trait))
        person.goal = str(f.get("goal",person.goal))
        person.xp = int(f.get("xp",0))
        person.level = int(f.get("level",1))
        person.morale = int(f.get("morale",70))
        person.memory = str(f.get("memory",""))
        person.rival = str(f.get("rival",""))
        person.friend = str(f.get("friend",""))
        person.profession = str(f.get("profession",person.profession))
        person.equipment = str(f.get("equipment",person.equipment))
        person.relations = f.get("relations",{})
        person.wanderlust = int(f.get("wanderlust",0))
        fighters.append(person)
    settlements.clear()
    for b in data.get("bases",[]):
        settlements.append({"p":Vector2i(int(b.x),int(b.y)),"team":int(b.team),"wood":int(b.wood),"stone":int(b.stone),"food":int(b.food),"level":int(b.level),"hp":int(b.hp),"territory":int(b.territory)})
    resource_nodes.clear()
    for n in data.get("nodes",[]):
        resource_nodes.append({"p":Vector2i(int(n.x),int(n.y)),"type":int(n.type),"amount":int(n.amount)})
    if settlements.size() != 3:
        events = "Old save incompatible with civilizations. Create New World."
        generate()
        return
    next_unit_id = int(data.get("next_id",10000))
    stories = data.get("stories",[])
    monsters.clear()
    for m in data.get("monsters",[]):
        var mp := Vector2i(int(m.x),int(m.y))
        monsters.append({"p":mp,"old":mp,"hp":int(m.hp),"kind":int(m.kind),"cooldown":0})
    ruins.clear()
    for rp in data.get("ruins",[]):
        ruins.append(Vector2i(int(rp[0]),int(rp[1])))
    calamity = int(data.get("calamity",0))
    catastrophe_until = int(data.get("catastrophe_until",0))
    god_power = int(data.get("god_power",100))
    effect_marks.clear()
    turn = int(data.turn)
    deaths = int(data.deaths)
    seed_value = int(data.seed)
    selected = -1
    events = "World loaded."
    update_minimap()
    refresh()

func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventScreenDrag:
        camera.position -= event.relative / camera.zoom
    elif event is InputEventMagnifyGesture:
        var next_zoom: float = clamp(camera.zoom.x * event.factor,0.4,2.5)
        camera.zoom = Vector2(next_zoom,next_zoom)
    elif event is InputEventMouseButton:
        if event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
            camera.zoom *= 1.1
        elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
            camera.zoom /= 1.1
        elif event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
            choose_unit(event.position)
    elif event is InputEventScreenTouch and event.pressed:
        choose_unit(event.position)

func choose_unit(screen: Vector2) -> void:
    var pos := camera.get_screen_center_position() + (screen - get_viewport_rect().size / 2) / camera.zoom
    var cell := Vector2i(floori(pos.x / TILE),floori(pos.y / TILE))
    selected = -1
    if god_mode != 0:
        use_god_power(cell)
        return
    for f in fighters:
        if f.p == cell:
            selected = f.id
            break
    refresh()
