# Living Dungeon graphics tools

Tooling for iterating on Living Dungeon art. The game still draws the encoded placeholders in `art_tiles.gd` and `soldier_sprites.gd`, and buildings are still drawn in `world.gd`. Nothing here changes gameplay.

Godot **4.4.1** matches `project.godot` and the `Build Living Dungeon Godot APK` workflow.

## Iteration loop

1. Export or drop source images into a folder that mirrors `art/` (see below).
2. Run `assets.py` to slice, resize, quantize, and write `art/` plus Godot `.import` files.
3. When those textures are wired into a scene later, call `LivingDungeonPixelArt.configure(sprite)` so sampling stays nearest-neighbor.
4. Run `screenshot.sh`, then look at `screenshots/*.png`.
5. Repeat. The capture uses a fixed seed, so the same command frames the same world.

```bash
cd projects/dungeon_godot
python3 tools/assets.py self-test
tools/screenshot.sh --preset all --seconds 3 --seed 12047
```

Screenshots land in `projects/dungeon_godot/screenshots/`. That folder has a `.gdignore` file, so Godot does not import or export the PNGs.

## Screenshot tool

`tools/screenshot.sh` runs `tools/screenshot_capture.tscn`. The scene instances the normal game, lets the simulation advance, pauses it, moves the camera, and saves the viewport. It does not use `godot --headless`, because headless mode does not render. On a machine with no display (a Linux VM or GitHub Actions) the script wraps Godot in Xvfb and forces llvmpipe.

Install once on a plain Ubuntu VM:

```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  xvfb unzip ca-certificates curl python3 \
  libfontconfig1 libx11-6 libxcursor1 libxext6 libxfixes3 libxi6 \
  libxinerama1 libxrandr2 libxrender1 libgl1 libgl1-mesa-dri
projects/dungeon_godot/tools/screenshot.sh --install-godot
```

`--install-godot` downloads the official 4.4.1 Linux editor into `projects/dungeon_godot/.cache/godot/` (gitignored). You can also point `GODOT` at a binary already on the machine.

```bash
# Four review frames: overview, settlement, units, ui
projects/dungeon_godot/tools/screenshot.sh

# One preset, longer simulation
projects/dungeon_godot/tools/screenshot.sh --preset settlement --seconds 8

# Exactly 40 process frames (at the script's fixed 20 fps that is 2 seconds)
projects/dungeon_godot/tools/screenshot.sh --preset units --frames 40

# Frame a tile. Coordinates are tile x,y. Zoom is the Camera2D zoom.
projects/dungeon_godot/tools/screenshot.sh --preset custom --tile 15,15 --zoom 2

# Frame a world-pixel position instead of a tile
projects/dungeon_godot/tools/screenshot.sh --preset custom --camera 465,450 --zoom 2

# Random world, written somewhere else
projects/dungeon_godot/tools/screenshot.sh --seed random --out /tmp/dungeon-shots
```

| Preset | What it frames |
| --- | --- |
| `overview` | Wide view around tile (30, 28), zoom 0.48, so the Azure capital and a large stretch of dungeon are visible between the HUD panels. |
| `settlement` | Close view of the first settlement (Azure, tile 15,15), zoom 1.7. |
| `units` | Close view of the living soldier with the most neighbors within 5 tiles, zoom 2.3. |
| `ui` | The game's own startup camera (zoom 0.93). Header, minimap, and bottom panel are part of the shot. `minimap` is an alias of `ui`. |
| `custom` | `--tile x,y` or `--camera x,y` at `--zoom`. |
| `all` | `overview`, `settlement`, `units`, and `ui`. This is the default. |

Default seed is `12047`. The capture scene assigns that seed and calls `generate()` again, so the world is deterministic. `--seed random` keeps the seed chosen in `world.gd`.

After Godot exits, the script rejects a PNG that is tiny, nearly a single color, or missing bright pixels. A blank GL framebuffer fails the run.

Useful environment variables: `GODOT`, `LIVING_DUNGEON_PRESET`, `LIVING_DUNGEON_SECONDS`, `LIVING_DUNGEON_FRAMES`, `LIVING_DUNGEON_SEED`, `LIVING_DUNGEON_OUT`, `LIVING_DUNGEON_CAMERA`, `LIVING_DUNGEON_TILE`, `LIVING_DUNGEON_ZOOM`.

## Asset pipeline

`tools/assets.py` reads 8-bit PNGs (RGBA, RGB, gray, or indexed, not interlaced) and writes:

```text
art/
  tiles/<name>.png
  tiles/<sheet>_00.png
  units/<faction>/<animation>.png
  units/<faction>/<animation>_00.png
  buildings/<name>.png
  fx/<name>.png
  fx/<sheet>_00.png
  palette.png                 # only with --write-palette
```

Suggested faction folder names match the three teams: `azure`, `crimson`, `verdant`. A sheet named `walk.png` sliced into four cells becomes `walk_00.png` … `walk_03.png`, left to right, top to bottom. Pass `--names grass,dirt` to name frames yourself. One cell keeps the source file name (`idle.png` stays `idle.png`).

```bash
# One 16x16 sheet into 32x32 tiles, quantized to 24 colors
python3 projects/dungeon_godot/tools/assets.py slice \
  --input pack/terrain.png \
  --kind tiles \
  --grid 16x16 \
  --resize 32x32 \
  --colors 24

# Soldiers for one faction, using a shared palette image
python3 projects/dungeon_godot/tools/assets.py slice \
  --input pack/azure_walk.png \
  --kind units \
  --faction azure \
  --grid 32x32 \
  --palette pack/palette.png

# A whole drop that already mirrors the output tree
python3 projects/dungeon_godot/tools/assets.py batch \
  --src art_src \
  --grid 16x16 \
  --colors 32 \
  --write-palette
```

`batch` reads this source layout:

```text
art_src/
  palette.png            # optional shared palette
  tiles/*.png
  units/<faction>/*.png
  buildings/*.png
  fx/*.png
```

`--grid` slices every image that can hold at least one cell. Omit `--grid` when the files are already individual sprites. `--resize WxH` uses nearest-neighbor, so integer scales stay crisp. `--colors N` builds one median-cut palette from the opaque pixels and remaps every frame to it. `--palette file.png` uses that image's opaque colors instead. Fully transparent pixels stay transparent.

Each written PNG gets a sibling `.png.import` for the Godot 4.4 texture importer:

- `compress/mode=0` (lossless)
- `mipmaps/generate=false`
- `detect_3d/compress_to=0` (do not let Godot switch the texture to VRAM compression and mipmaps)
- `process/fix_alpha_border=false` (do not bleed RGB into transparent texels)

Godot 4.4 does not store the canvas sampling filter in `.import`. Mipmaps and lossy compression are what blur an imported texture. When a sprite is added to a scene, set nearest sampling:

```gdscript
LivingDungeonPixelArt.configure(sprite)
```

That helper lives in `tools/pixel_filter.gd`. The current dungeon does not call it. Turning nearest on for the whole project is this `project.godot` line, and it is intentionally **not** set yet because it would also resample the placeholder art:

```ini
[rendering]
textures/canvas_textures/default_texture_filter=0
```

`0` is Nearest. The engine default is `1` (Linear).

```bash
python3 projects/dungeon_godot/tools/assets.py self-test
python3 projects/dungeon_godot/tools/assets.py check-screenshot screenshots/*.png
```

## Legacy encoded art

`tools/build_assets.py` is unchanged. If `assets_payload/*.b85` exists, it zlib-decodes those payloads into flat `art/<name>.png` files. The new pipeline writes subfolders (`art/tiles/`, `art/units/<faction>/`, `art/buildings/`, `art/fx/`) and does not remove those flat files. The running game never loads either set; `world.gd` still builds textures from `art_tiles.gd` and `soldier_sprites.gd`.

## CI

`.github/workflows/godot-dungeon.yml` (`Build Living Dungeon Godot APK`) runs on pull requests and on pushes to `main` that touch `projects/dungeon_godot/**` or the workflow file.

- `import-and-screenshots` installs Godot 4.4.1, imports the project, fails on script or parse errors, runs `assets.py self-test` and `screenshot.sh`, and uploads `Living-Dungeon-Screenshots`.
- `export-android` is the existing debug APK job on `barichello/godot-ci:4.4.1`. It generates a debug keystore in the runner, exports `build/living-dungeon-godot.apk`, and uploads `Living-Dungeon-Godot-APK`. No repository secrets are required.

## Limits

- Screenshot capture needs OpenGL 3.3 (llvmpipe is fine). `godot --headless` will not produce an image.
- The capture viewport is the game's 720×1280 portrait window, including HUD.
- Interlaced PNGs and bit depths other than 8 are rejected by `assets.py`.
- The debug APK is signed with a CI-generated debug keystore, so it is not a stable update key for installed builds.
- Android export still depends on the Godot CI image (JDK, Android SDK, and the 4.4.1 export templates). A machine with only the editor binary cannot export an APK.
