extends Node
## Runs Living Dungeon, lets the simulation advance, then writes PNG frames.
## Launch through tools/screenshot.sh. The game scene is unchanged.

const VIEW_SIZE := Vector2i(720, 1280)
const TILE := 30.0

var world
var args := {}
var default_camera_pos := Vector2.ZERO
var default_camera_zoom := Vector2.ONE


func _ready() -> void:
    _boot()


func _boot() -> void:
    args = _parse_args()
    _configure_window()
    var packed: PackedScene = load("res://Main.tscn")
    if packed == null:
        push_error("Failed to load res://Main.tscn")
        get_tree().quit(1)
        return
    world = packed.instantiate()
    add_child(world)
    if world.camera == null:
        push_error("Game camera was not created")
        get_tree().quit(1)
        return
    default_camera_pos = world.camera.position
    default_camera_zoom = world.camera.zoom
    var seed_text := _opt("seed", "LIVING_DUNGEON_SEED", "12047")
    if seed_text != "random":
        world.rng.seed = int(seed_text)
        world.generate()
    print("SCREENSHOT world_seed=", world.seed_value)
    print("SCREENSHOT viewport=", get_viewport().get_visible_rect().size)
    print("SCREENSHOT adapter=", RenderingServer.get_video_adapter_name())
    var frame_target := int(_opt("frames", "LIVING_DUNGEON_FRAMES", "0"))
    if frame_target > 0:
        for _i in frame_target:
            await get_tree().process_frame
        print("SCREENSHOT waited_frames=", frame_target)
    else:
        var seconds := float(_opt("seconds", "LIVING_DUNGEON_SECONDS", "3"))
        var accum := 0.0
        var guard := 0
        while accum < seconds and guard < 20000:
            await get_tree().process_frame
            accum += get_process_delta_time()
            guard += 1
        print("SCREENSHOT simulated_seconds=", snapped(accum, 0.01), " frames=", guard)
    world.speed = 0
    var out_dir := _opt("out", "LIVING_DUNGEON_OUT", ProjectSettings.globalize_path("res://screenshots"))
    if out_dir.begins_with("res://"):
        out_dir = ProjectSettings.globalize_path(out_dir)
    DirAccess.make_dir_recursive_absolute(out_dir)
    var failed := false
    for preset in _presets(_opt("preset", "LIVING_DUNGEON_PRESET", "all")):
        if not await _capture_preset(preset, out_dir):
            failed = true
    get_tree().quit(1 if failed else 0)


func _configure_window() -> void:
    var root := get_tree().root
    root.mode = Window.MODE_WINDOWED
    root.borderless = true
    root.position = Vector2i(0, 0)
    root.size = VIEW_SIZE
    DisplayServer.window_set_position(Vector2i(0, 0))
    DisplayServer.window_set_size(VIEW_SIZE)


func _presets(name: String) -> PackedStringArray:
    if name == "all":
        return PackedStringArray(["overview", "settlement", "units", "ui"])
    if name == "minimap":
        return PackedStringArray(["ui"])
    return PackedStringArray([name])


func _capture_preset(preset: String, out_dir: String) -> bool:
    if not _apply_preset(preset):
        return false
    var img: Image = null
    var stats := Vector3i.ZERO
    for _attempt in 4:
        await get_tree().process_frame
        await RenderingServer.frame_post_draw
        img = get_viewport().get_texture().get_image()
        if img == null or img.is_empty():
            continue
        if img.get_format() != Image.FORMAT_RGBA8:
            img.convert(Image.FORMAT_RGBA8)
        stats = _stats(img)
        if stats.x >= 4 and stats.y >= 8 and img.get_width() >= 320 and img.get_height() >= 480:
            break
    if img == null or img.is_empty():
        push_error("Viewport image was empty for preset " + preset)
        return false
    var path := out_dir.path_join(preset + ".png")
    var err := img.save_png(path)
    if err != OK:
        push_error("save_png failed for %s (%s)" % [path, err])
        return false
    print("SCREENSHOT_OK ", path, " ", img.get_width(), "x", img.get_height(), " colors=", stats.x, " bright=", stats.y, " mean=", stats.z)
    if stats.x < 4 or stats.y < 8 or img.get_width() < 320 or img.get_height() < 480:
        push_error("Screenshot looks blank: " + path)
        return false
    return true


func _stats(img: Image) -> Vector3i:
    var colors := {}
    var bright := 0
    var total := 0
    var sum_l := 0
    for y in range(0, img.get_height(), 4):
        for x in range(0, img.get_width(), 4):
            var c := img.get_pixel(x, y)
            var key := (int(c.r * 31.0) << 10) | (int(c.g * 31.0) << 5) | int(c.b * 31.0)
            colors[key] = true
            var luminance := int((c.r + c.g + c.b) * 255.0)
            sum_l += luminance
            if luminance > 140:
                bright += 1
            total += 1
    var mean := 0
    if total > 0:
        mean = sum_l / total
    return Vector3i(colors.size(), bright, mean)


func _apply_preset(preset: String) -> bool:
    var cam: Camera2D = world.camera
    cam.enabled = true
    cam.make_current()
    if preset == "ui" or preset == "minimap":
        cam.position = default_camera_pos
        cam.zoom = default_camera_zoom
        world.queue_redraw()
        return true
    if preset == "custom":
        var zoom := float(_opt("zoom", "LIVING_DUNGEON_ZOOM", "1.6"))
        var world_point := _custom_world_point()
        cam.zoom = Vector2(zoom, zoom)
        cam.position = _camera_for(world_point, _view_center(), cam.zoom)
        world.queue_redraw()
        return true
    var zoom := 1.0
    var world_point := default_camera_pos
    match preset:
        "overview":
            zoom = 0.48
            world_point = Vector2(30, 28) * TILE + Vector2(TILE * 0.5, TILE * 0.5)
        "settlement":
            if world.settlements.is_empty():
                push_error("No settlement to frame")
                return false
            zoom = 1.7
            var base = world.settlements[0].p
            world_point = Vector2(base) * TILE + Vector2(TILE * 0.5, TILE * 0.25)
        "units":
            zoom = 2.3
            world_point = _unit_focus()
        _:
            push_error("Unknown screenshot preset: " + preset)
            return false
    cam.zoom = Vector2(zoom, zoom)
    cam.position = _camera_for(world_point, _view_center(), cam.zoom)
    world.queue_redraw()
    return true


func _view_center() -> Vector2:
    return get_viewport().get_visible_rect().size * 0.5


func _camera_for(world_point: Vector2, screen_point: Vector2, zoom: Vector2) -> Vector2:
    var viewport_size := get_viewport().get_visible_rect().size
    return world_point - (screen_point - viewport_size * 0.5) / zoom


func _custom_world_point() -> Vector2:
    if args.has("tile"):
        var tile := _parse_vec(str(args["tile"]))
        return tile * TILE + Vector2(TILE * 0.5, TILE * 0.5)
    if args.has("camera"):
        return _parse_vec(str(args["camera"]))
    var env_tile := OS.get_environment("LIVING_DUNGEON_TILE")
    if env_tile != "":
        var tile_from_env := _parse_vec(env_tile)
        return tile_from_env * TILE + Vector2(TILE * 0.5, TILE * 0.5)
    return _parse_vec(_opt("camera", "LIVING_DUNGEON_CAMERA", "900,900"))


func _unit_focus() -> Vector2:
    var fallback := Vector2(15, 15)
    if not world.settlements.is_empty():
        fallback = Vector2(world.settlements[0].p)
    var best_p := fallback
    var best_score := -1
    var fighters: Array = world.fighters
    for index in fighters.size():
        var fighter: Dictionary = fighters[index]
        if int(fighter.get("hp", 0)) <= 0:
            continue
        var score := 0
        var fp: Vector2i = fighter.p
        for other_index in fighters.size():
            if other_index == index:
                continue
            var other: Dictionary = fighters[other_index]
            if int(other.get("hp", 0)) <= 0:
                continue
            var op: Vector2i = other.p
            var dist := absi(op.x - fp.x) + absi(op.y - fp.y)
            if dist > 0 and dist <= 5:
                score += 1
        if score > best_score:
            best_score = score
            best_p = Vector2(fp)
    return best_p * TILE + Vector2(TILE * 0.5, TILE * 0.4)


func _parse_vec(text: String) -> Vector2:
    var parts := text.split(",")
    if parts.size() != 2:
        push_error("Expected x,y coordinates, got: " + text)
        return Vector2.ZERO
    return Vector2(float(parts[0]), float(parts[1]))


func _opt(key: String, env_name: String, default_value: String) -> String:
    if args.has(key) and str(args[key]) != "":
        return str(args[key])
    var env_val := OS.get_environment(env_name)
    if env_val != "":
        return env_val
    return default_value


func _parse_args() -> Dictionary:
    var out := {}
    var raw := OS.get_cmdline_user_args()
    var i := 0
    while i < raw.size():
        var token := str(raw[i])
        if token.begins_with("--"):
            var body := token.substr(2)
            var eq := body.find("=")
            if eq >= 0:
                out[body.substr(0, eq)] = body.substr(eq + 1)
            elif i + 1 < raw.size() and not str(raw[i + 1]).begins_with("--"):
                out[body] = str(raw[i + 1])
                i += 1
            else:
                out[body] = "true"
        i += 1
    print("SCREENSHOT args=", out)
    return out
