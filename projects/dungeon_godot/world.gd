extends Node2D
const AtlasTiles = preload("res://art_tiles.gd")
const SoldierSprites = preload("res://soldier_sprites.gd")
# Living Dungeon: Godot foundation. Entire world renders procedurally.
const GRID := Vector2i(96, 96)
const TILE := 30.0
const FACTIONS := [Color("#5bbdf1"), Color("#ed6969"), Color("#8fd878")]
const TEAM_NAMES := ["Azure", "Crimson", "Verdant"]
const GIVEN_NAMES := ["Aldric","Veyra","Morwen","Kael","Eryn","Darian","Sable","Rhun","Nyx","Orin","Mara","Thorne"]
const TRAITS := ["Brave","Cautious","Greedy","Loyal","Curious","Ruthless"]
const GOALS := ["Protect","Explore","Gather","Glory"]
const PROFESSIONS := ["Warrior","Scout","Guardian","Worker","Hunter"]
const EQUIPMENT := ["Rusty sword","Iron spear","Leather armor","Hunter bow","Steel blade"]
var terrain: Array = []
var biomes: Array = []
var art_textures: Array[Texture2D] = []
var faction_sprites: Array[Texture2D] = []
var creature_sprites: Array[Texture2D] = []
var animated_glow := 0.0
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
    art_textures = AtlasTiles.build()
    faction_sprites = SoldierSprites.build()
    creature_sprites = make_creature_sprites()
    camera = Camera2D.new()
    camera.position = Vector2(30,30) * TILE
    camera.zoom = Vector2(0.93, 0.93)
    camera.enabled = true
    add_child(camera)
    hud = CanvasLayer.new()
    add_child(hud)
    var overlay := Control.new()
    overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
    hud.add_child(overlay)
    var header := PanelContainer.new()
    header.position = Vector2(10, 42)
    header.size = Vector2(700, 108)
    overlay.add_child(header)
    stylize_panel(header,Color("#131b28"))
    var headbox := VBoxContainer.new()
    header.add_child(headbox)
    var title := Label.new()
    title.text = "LIVING DUNGEON  /  GODOT 1.0"
    title.add_theme_font_size_override("font_size", 24)
    title.add_theme_color_override("font_color", Color("#e2c49a"))
    headbox.add_child(title)
    status = Label.new()
    status.add_theme_font_size_override("font_size", 19)
    headbox.add_child(status)
    var map_border := PanelContainer.new()
    map_border.position = Vector2(530,165)
    map_border.size = Vector2(174,174)
    overlay.add_child(map_border)
    stylize_panel(map_border,Color("#171c2b"))
    minimap = TextureRect.new()
    minimap.custom_minimum_size = Vector2(166,166)
    minimap.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    minimap.stretch_mode = TextureRect.STRETCH_SCALE
    minimap.mouse_filter = Control.MOUSE_FILTER_IGNORE
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
    details.add_theme_font_size_override("font_size", 23)
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
    action_hint.add_theme_font_size_override("font_size",21)
    tool_hint = action_hint
    tool_hint.add_theme_color_override("font_color",Color("#ffe0a3"))
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
    generate()

func stylize_panel(panel: PanelContainer, fill: Color) -> void:
    var style := StyleBoxFlat.new()
    style.bg_color = Color(fill.r,fill.g,fill.b,0.92)
    style.border_color = Color("#b78b54")
    style.set_border_width_all(2)
    style.corner_radius_top_left = 5
    style.corner_radius_top_right = 5
    style.corner_radius_bottom_left = 5
    style.corner_radius_bottom_right = 5
    style.set_content_margin_all(7)
    panel.add_theme_stylebox_override("panel",style)

func stylize_button(btn: Button) -> void:
    btn.add_theme_font_size_override("font_size",19)
    btn.add_theme_color_override("font_color",Color("#f4e2c7"))
    var style := StyleBoxFlat.new()
    style.bg_color = Color("#273044")
    style.border_color = Color("#916f4c")
    style.set_border_width_all(1)
    style.set_content_margin_all(7)
    btn.add_theme_stylebox_override("normal",style)
    var hover := style.duplicate()
    hover.bg_color = Color("#4a3440")
    btn.add_theme_stylebox_override("hover",hover)
    btn.add_theme_stylebox_override("pressed",hover)

func make_creature_sprites() -> Array[Texture2D]:
    var result: Array[Texture2D] = []
    for monster_kind in range(2):
        var img := Image.create(28,32,false,Image.FORMAT_RGBA8)
        img.fill(Color.TRANSPARENT)
        var body: Color = Color("#865cba") if monster_kind == 0 else Color("#9d3935")
        var dark: Color = body.darkened(0.55)
        for yy in range(8,27):
            for xx in range(4,24):
                var cx: float = float(xx-14)/11.0
                var cy: float = float(yy-18)/13.0
                if cx*cx+cy*cy < 0.9:
                    img.set_pixel(xx,yy,dark if (xx+yy)%5==0 else body)
        for xx in range(7,21):
            for yy in range(7,15):
                if abs(xx-14)+abs(yy-11) < 9:
                    img.set_pixel(xx,yy,Color("#d8c5af"))
        for xx in [10,18]:
            img.set_pixel(xx,11,Color("#ff4a60") if monster_kind == 1 else Color("#abf7e9"))
            img.set_pixel(xx,12,Color("#2e1018"))
        for yy in range(2,11):
            img.set_pixel(5+int(yy/3),yy,Color("#e9d2c1"))
            img.set_pixel(22-int(yy/3),yy,Color("#e9d2c1"))
        for yy in range(25,30):
            for xx in [8,9,18,19]:
                img.set_pixel(xx,yy,dark)
        result.append(ImageTexture.create_from_image(img))
    return result

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
    var shades := [Color("#42495b"),Color("#35523e"),Color("#503c53"),Color("#674831")]
    for y in range(GRID.y):
        for x in range(GRID.x):
            var color: Color = Color("#171d27") if terrain[y][x] == 1 else shades[int(biomes[y][x])]
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
    var economy := "  |  "
    for b in settlements:
        economy += TEAM_NAMES[int(b.team)].substr(0,1) + ":F" + str(b.food) + "/W" + str(b.wood) + "/S" + str(b.stone) + " "
    details.text = events + "\n" + economy + " | GOD " + str(god_power)
    if selected >= 0:
        for f in fighters:
            if f.id == selected:
                details.text = "%s L%d %s | HP %d | %s\n%s | %s" % [f.name, f.level, f.profession, f.hp, f.goal, f.trait, f.memory]
                break
    queue_redraw()

func draw_ellipse_shadow(center: Vector2) -> void:
    draw_circle(center,11,Color(0,0,0,0.34))

func _draw() -> void:
    var world_span: Vector2 = get_viewport_rect().size / camera.zoom
    var start_world: Vector2 = camera.get_screen_center_position() - world_span * 0.5
    var xmin: int = maxi(0,floori(start_world.x / TILE)-2)
    var ymin: int = maxi(0,floori(start_world.y / TILE)-2)
    var xmax: int = mini(GRID.x,ceili((start_world.x+world_span.x)/TILE)+3)
    var ymax: int = mini(GRID.y,ceili((start_world.y+world_span.y)/TILE)+3)
    for y in range(ymin,ymax):
        for x in range(xmin,xmax):
            var p := Vector2(x, y) * TILE
            var variation: int = (x * 71 + y * 31 + x * y) % 7
            var tile_index: int = 4 if terrain[y][x] == 1 else int(biomes[y][x])
            if art_textures.size() == 5:
                var sprite_index: int = tile_index
                if tile_index == 2 and variation % 4 != 0:
                    sprite_index = 0
                draw_texture_rect(art_textures[sprite_index],Rect2(p,Vector2(TILE,TILE)),false)
                if terrain[y][x] == 0 and variation % 5 == 0:
                    draw_rect(Rect2(p+Vector2(4,25),Vector2(7,2)),Color(0.1,0.1,0.1,0.26))
                if terrain[y][x] == 1:
                    draw_line(p+Vector2(2,2),p+Vector2(28,2),Color("#b5b4a4"),2)
                elif variation % 7 == 3 and biomes[y][x] == 1:
                    draw_line(p+Vector2(12,24),p+Vector2(15,17),Color("#acc375"),2)
            else:
                draw_rect(Rect2(p,Vector2(TILE,TILE)),Color("#313744"))
    for base in settlements:
        var origin: Vector2 = Vector2(base.p) * TILE
        var color: Color = FACTIONS[int(base.team)]
        draw_arc(origin + Vector2(TILE/2,TILE/2),float(base.territory)*TILE,0,TAU,84,Color(color.r,color.g,color.b,0.16),3)
        draw_rect(Rect2(origin - Vector2(13,17),Vector2(55,54)),Color("#10131a"))
        for wall_x in [-12,30]:
            draw_rect(Rect2(origin+Vector2(wall_x,-21),Vector2(12,47)),Color("#526071"))
            draw_rect(Rect2(origin+Vector2(wall_x-3,-25),Vector2(18,7)),Color("#8d9ba5"))
        draw_rect(Rect2(origin - Vector2(5,1),Vector2(40,29)),Color("#667281"))
        draw_rect(Rect2(origin + Vector2(5,-16),Vector2(20,27)),color)
        draw_rect(Rect2(origin + Vector2(11,13),Vector2(10,20)),Color("#10131a"))
        draw_rect(Rect2(origin + Vector2(-5,-1),Vector2(40,4)),Color("#d3b888"))
        draw_rect(Rect2(origin + Vector2(14,-24),Vector2(3,13)),Color("#d7d4cb"))
    for node in resource_nodes:
        if int(node.amount) <= 0:
            continue
        var p: Vector2 = Vector2(node.p)*TILE
        var tint: Color = [Color("#94704e"),Color("#8b96a6"),Color("#899c56")][int(node.type)]
        draw_circle(p + Vector2(15,15),5.0,tint)
    for ruin in ruins:
        if ruin.x < xmin or ruin.y < ymin or ruin.x > xmax or ruin.y > ymax:
            continue
        var rp: Vector2 = Vector2(ruin)*TILE
        draw_rect(Rect2(rp-Vector2(5,7),Vector2(41,42)),Color("#191522"))
        draw_rect(Rect2(rp+Vector2(0,-9),Vector2(32,8)),Color("#716071"))
        draw_rect(Rect2(rp+Vector2(4,5),Vector2(24,28)),Color("#433049"))
        draw_circle(rp+Vector2(16,18),8,Color("#9d53b2"))
        draw_circle(rp+Vector2(16,18),4,Color("#24122e"))
    if calamity != 0:
        draw_rect(Rect2(Vector2.ZERO,Vector2(GRID)*TILE),Color(0.22,0.02,0.12,0.10 if calamity == 2 else 0.05))
    for mark in effect_marks:
        var center: Vector2 = Vector2(mark.p) * TILE + Vector2(15,15)
        var time_left: float = clampf(float(int(mark.until_ms) - Time.get_ticks_msec()) / 1350.0,0.0,1.0)
        var radius: float = lerpf(10.0,75.0,1.0-time_left)
        var kind: int = int(mark.kind)
        var power_color: Color = Color("#fff2a5") if kind == 4 else (Color("#72ddff") if kind == 5 else Color("#ec75e0"))
        draw_circle(center,14.0 + 30.0*time_left,Color(power_color.r,power_color.g,power_color.b,0.20*time_left))
        draw_arc(center,radius,0,TAU,40,Color(power_color.r,power_color.g,power_color.b,time_left),5)
        if kind == 4:
            for spark in range(14):
                var angle: float = float(spark) * TAU / 14.0
                var travel: float = (1.0-time_left)*115.0
                var outward: Vector2 = Vector2(cos(angle),sin(angle))
                draw_circle(center + outward*travel,float(2+spark%3)*time_left+1,Color("#ffc25b"))
            draw_line(center-Vector2(56,180)*time_left,center,Color("#ffb23a"),maxf(3.0,14.0*time_left))
            draw_circle(center,9.0+28.0*time_left,Color("#ff7b2e"))
            draw_arc(center,radius*0.75,0,TAU,32,Color("#ffe89b"),3)
        elif kind == 6:
            for cloud_idx in range(8):
                var phi: float = float(cloud_idx)*TAU/8.0
                var cloud_pos: Vector2 = center + Vector2(cos(phi),sin(phi))*(24.0+40.0*(1.0-time_left))
                draw_circle(cloud_pos,10.0*time_left+4.0,Color(0.40,0.94,0.18,0.47*time_left))
        elif kind == 3:
            for ray in range(10):
                var ray_pos: Vector2 = center+Vector2(cos(float(ray)*TAU/10.0),sin(float(ray)*TAU/10.0))*40.0
                draw_line(ray_pos,ray_pos-Vector2(0,55.0*time_left),Color(1.0,0.86,0.39,time_left),2)
        elif kind == 5:
            draw_rect(Rect2(Vector2(mark.p)*TILE,Vector2(TILE,TILE)),Color("#9ee8ff"))
            draw_arc(center,24,0,TAU,20,Color("#ffffff"),3)
    var tween: float = clamp(sim_accum / 0.55, 0.0, 1.0)
    tween = tween * tween * (3.0 - 2.0 * tween)
    for m in monsters:
        if m.p.x < xmin or m.p.x > xmax or m.p.y < ymin or m.p.y > ymax:
            continue
        var mp: Vector2 = Vector2(m.old).lerp(Vector2(m.p),tween)*TILE
        var creature_kind: int = 1 if int(m.kind) == 2 else 0
        draw_circle(mp+Vector2(15,26),12,Color(0,0,0,0.36))
        if creature_sprites.size() == 2:
            var bob: float = sin(float(Time.get_ticks_msec()) / 250.0 + float(m.p.x))*1.7
            draw_texture_rect(creature_sprites[creature_kind],Rect2(mp-Vector2(2,13+bob),Vector2(34,43)),false)
        else:
            draw_circle(mp+Vector2(15,15),12,Color("#8a3e6e"))
    for f in fighters:
        if f.p.x < xmin or f.p.x > xmax or f.p.y < ymin or f.p.y > ymax:
            continue
        var from: Vector2 = Vector2(f.old)
        var to: Vector2 = Vector2(f.p)
        var p: Vector2 = from.lerp(to,tween) * TILE + Vector2(4,3)
        var cloak: Color = FACTIONS[f.team]
        draw_ellipse_shadow(p + Vector2(12,23))
        if faction_sprites.size() == 3:
            draw_texture_rect(faction_sprites[int(f.team)],Rect2(p - Vector2(9,15),Vector2(41,51)),false)
            if str(f.profession).to_lower().contains("mage") or str(f.profession).to_lower().contains("necro"):
                draw_circle(p + Vector2(27,2),5,Color("#aa67e9"))
            elif str(f.profession).to_lower().contains("worker"):
                draw_rect(Rect2(p+Vector2(24,12),Vector2(5,10)),Color("#d2a15a"))
        else:
            draw_rect(Rect2(p + Vector2(5,7),Vector2(15,17)),cloak)
        if f.hp < 5:
            draw_rect(Rect2(p + Vector2(2,-4),Vector2(24,3)),Color("#632d35"))
            draw_rect(Rect2(p + Vector2(2,-4),Vector2(24.0 * f.hp / 5.0,3)),Color("#aee087"))
        if f.id == selected:
            draw_arc(p + Vector2(12,12),15,0,TAU,24,Color("#f5d789"),2)

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
    # Speed label is the second button in the bottom HBox.
    var bottom: PanelContainer = hud.get_child(0).get_child(1)
    var controls: HBoxContainer = bottom.get_child(0).get_child(1)
    controls.get_child(1).text = "Speed x%d" % speed

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
