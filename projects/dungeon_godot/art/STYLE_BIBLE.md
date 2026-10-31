# Living Dungeon style bible

Approved target: `art/style/reference/concept_target.jpg` (portrait 720×1280). Parent explorations are `concept_a.jpg` and `concept_b.jpg`. `player_reference.jpg` is a mood reference for density and darkness. Do not trace it and do not copy its UI chrome.

The master palette is 40 colors in `art/style/palette.png`, `art/style/palette.gpl` (GIMP, named), and `art/style/palette.hex` (one `RRGGBB` per line, same order). `tools/ingest_ai.py` quantizes to this palette. Godot ignores `art/style/` (`.gdignore`); the game does not load these files.

This document does not change gameplay, the tile grid, or the renderer.

## What the target is

Dark-fantasy pixel art. Indigo and violet stone, teal fog, orange fire as the warm accent. Three factions read at a glance: blue knights and crystal keep, red orc camp with braziers, green elf mushroom grove. A violet necromancer portal with skeletons, a stone golem, a cyan magic circle, and a fireball sit in the same scene. UI is near-black panels with gold trim. The m5x7 font already in `fonts/m5x7.ttf` is the interface font.

## Projection

The approved picture is isometric (2:1 diamonds, camera looking down the north edge of each cell). The running game is not.

`world.gd` keeps an orthogonal grid, `TILE := 32`. Floors and walls are 16×16 textures stretched into that 32×32 cell. Sprites go through `_draw_sprite`, which draws the texture at 2× and pins the foot to the bottom center of the cell (`TILE * 0.5`, `TILE - 1`). Pathfinding, territory, the minimap, light pools, and input all index square cells. An isometric renderer would replace drawing, depth sort, and diamond picking. That migration is out of scope here.

**Recommendation: keep the orthogonal grid and paint 3/4-view sprites on top of top-down square tiles.**

That is the projection `tools/prompt_templates.md` asks the generator for, and the projection `ingest_ai.py` pads for.

| Approach | What it buys | What it costs |
| --- | --- | --- |
| Orthogonal grid, 3/4 sprites (use this) | Fits `TILE`, `_draw_sprite`, autotiles, and the existing art paths. Faction silhouettes, palette, fire, and fog still carry the target. | Floors stay squares. The diamond ground plane in the concept is not reproduced. |
| True 2:1 isometric | Matches the target camera. A later migration would use 64×32 world diamonds (2 source pixels per world pixel, same density as today) or 32×16 source diamonds if the 2× sprite scale remains. | New tile mesh, painter's algorithm, and pick tests. Autotiles, shadows, and the minimap all change. Do not start that in an art-ingest change. |
| Orthogonal logic with diamonds drawn on top | The simulation could stay on square cells while the picture becomes iso. | Picking and depth sort still have to become diamond-aware. Same class of renderer change. |

Until that migration, do not generate isometric diamond tiles. They will not fit the 16×16 floor slot.

## Pixel density and canvas sizes

One texel in `art/tiles`, `art/units`, `art/buildings`, and `art/fx` is drawn at 2× into the 32-unit cell. Author those files at the sizes below. Do not pre-scale them to 32.

UI skins are the exception. `art/ui/panel.png` (48×48, 8px nine-slice) and `art/ui/button.png` (32×32, 6px nine-slice) are `StyleBoxTexture`s. They are not passed through `_draw_sprite`, so one texel is one screen pixel at the 720×1280 viewport.

| Slot | PNG size | Anchor | Notes |
| --- | --- | --- | --- |
| Floor / wall cell | 16×16 | full-bleed | No outline. Edges must tile. Wall autotile cells stay `wall_{col}_{row}.png`. |
| Prop on a cell (crate, rock, mushroom, skull) | 16×16 | feet | May be transparent around the object. |
| Humanoid (knight, orc, elf, mage, worker, guard, necromancer) | 16×28 | feet, bottom row | Same canvas for every faction. Bulk and height live inside the canvas so feet share a baseline. |
| Small creature (goblin, skeleton) | 16×16 | feet | |
| Boss (golem, demon) | 32×36 | feet | Matches the existing large-monster slot. |
| Settlement | tier 0: 48×48, tier 1: 64×64, tier 2: 96×80 | feet | One file per faction: `buildings/tier{N}_{azure\|crimson\|verdant}.png`. |
| Combat FX, torch, portal | 16×16, 4 frames | center | Torch and portal are `fx/{name}_{0..3}.png`. |
| Light blob | 64×64 | center | `fx/glow.png`. Soft in shape, hard in alpha (0 or 255 only). |
| UI icon | 16×16 | center | Drawn later at 2× inside a button, or 32×32 if a skin uses it at 1:1. |
| Panel / button | 48×48 and 32×32 | nine-slice | Keep the current margin widths if a skin is replaced. |

Animation frames use the game's suffix: `warrior_idle_0.png` … `warrior_idle_3.png`, then `warrior_run_0` … `warrior_run_3`. A single attack frame is `warrior_hit_0.png` (`presentation.gd` looks for that name). Four frames is the clip length already loaded for idle and run.

## Palette

Extracted from `concept_target.jpg`. Each swatch is the median of the pixels in that hue and value band. `floor` and `ember` use the upper part of their band (72nd percentile) so they stay separable from `stone` and `crimson_lit`. `azure_bright` is the nearest real pixel to the bright-armor cluster. Neighbors that collapsed into the same swatch (a second near-black, a teal darker than `cyan_shadow`, and a gold hotter than `flame`) were dropped. No dithering. Forty colors.

Shading is four steps on a material: shadow, base, lit, and a one-pixel specular. Do not invent in-between mixes. Fire and gold share `flame` as the hot yellow; a separate gold highlight sat on top of the fire core and collapsed into it.

### Dungeon neutrals

| Name | Hex | Use |
| --- | --- | --- |
| void | `#04040C` | Outline, deepest shadow, empty background |
| abyss | `#090A18` | First indigo step, panel field |
| dusk | `#191A32` | Wall base, azure deep shadow |
| floor | `#3B2C37` | Floor tile body (violet stone) |
| slate | `#242C59` | Cool wall light, azure shadow |
| steel | `#3C4B8C` | Metal mid, azure base in shadow |
| ice | `#90A3D0` | Metal specular, helm glint |
| stone | `#2C2D2C` | Neutral prop shadow |
| ash | `#5A5559` | Neutral prop, mortar |
| fog | `#877A81` | Distant fog |
| haze | `#BEB1B8` | Fog highlight, smoke |

### Azure (knights, banners, crystal keep)

Ramp: `dusk` → `slate` → `azure` → `azure_bright` → `ice`.

| Name | Hex | Use |
| --- | --- | --- |
| azure | `#475EA1` | Armor and banner base |
| azure_bright | `#7A9AD5` | Armor lit plane |

Crystal and the keep's magic use the violet ramp, not a second blue.

### Violet (crystals, portal, necromancer)

| Name | Hex | Use |
| --- | --- | --- |
| violet_shadow | `#1A0F21` | Portal stone, robe shadow |
| violet | `#2C0E4A` | Crystal base, portal arch |
| violet_lit | `#51108D` | Crystal face |
| violet_hot | `#B153E7` | Crystal specular, portal core |

### Cyan (magic circle, spells)

| Name | Hex | Use |
| --- | --- | --- |
| cyan_shadow | `#112E39` | Circle shadow, deep water |
| cyan | `#0F6673` | Circle ring |
| cyan_hot | `#4BD7DE` | Ring lit |
| cyan_core | `#6BEDF1` | Circle center |

### Crimson (orcs) and fire

Orc ramp: `crimson_shadow` → `crimson` → `crimson_lit` → `crimson_hot`. Fire is a separate ramp so a brazier does not recolor the faction.

| Name | Hex | Use |
| --- | --- | --- |
| crimson_shadow | `#2F0F0E` | Orc shadow, dried blood |
| crimson | `#5A241D` | Skin shadow, banner |
| crimson_lit | `#903720` | Skin base, mushroom cap |
| crimson_hot | `#C85C24` | Skin lit by fire |
| ember | `#A44624` | Brazier bowl, deep flame |
| fire | `#D56B1E` | Flame body |
| flame | `#FFCE6B` | Flame hot, gold glint |
| spark | `#FFF7BF` | Flame core, one pixel |

### Gold UI

| Name | Hex | Use |
| --- | --- | --- |
| gold_dark | `#634C2E` | Trim shadow |
| gold | `#B59465` | Panel and button trim |

The brightest gold pixel uses `flame`. Do not add another yellow.

### Verdant (elves, moss, mushrooms)

| Name | Hex | Use |
| --- | --- | --- |
| verdant_shadow | `#1B2918` | Foliage shadow, cloak |
| verdant | `#405B22` | Cloak and leaf base |
| verdant_lit | `#6D8C36` | Leaf lit |
| verdant_hot | `#B1C781` | Moss highlight, spore |

Mushroom caps use `crimson_lit`. Stems use the bone ramp.

### Bone (skeletons, skulls, golem chips)

| Name | Hex | Use |
| --- | --- | --- |
| bone_shadow | `#574B44` | Socket, underside |
| bone | `#9F9281` | Bone base |
| bone_lit | `#D8D6C1` | Bone lit |
| bone_hot | `#FAFAEB` | Tooth or skull specular |
| rose | `#65434F` | Dusty cloth, dried gore, portal mortar |

## Light

Key light comes from the **upper right**. Lit planes face up and to the right. Form shadow sits on the lower left. One step darker is the shadow; do not stack two shadow colors on a 16px figure.

Practical lights are local and use colors already on the ramp:

- Torch and brazier: `ember`, `fire`, `flame`, `spark`.
- Portal and crystals: violet ramp.
- Magic circle: cyan ramp.
- Fog: `fog` and `haze` only, in the upper background, never as a flat overlay on a unit.

No cast shadow baked into a sprite. The game draws `art/fx/shadow.png` under feet. A shadow painted into the generator's background becomes a halo after the chroma key.

## Outline, shading, clusters

- Characters, monsters, props, and buildings: **1px `void` outline** on the outside of the silhouette. The outline is part of the canvas, and the feet outline is the baseline.
- Floor tiles, wall autotiles, and full-bleed UI nine-slices: **no outline**. An outline seams.
- Fire, the magic circle, glow, and other FX: no void outline. The darkest step of that ramp is the rim.
- Alpha is 0 or 255. No antialiased fringe, no semi-transparent edge, no magenta spill.
- On a 16px unit, 1px is legal for an eye, a tooth, a weapon edge, or a specular. Larger surfaces (armor, cloak, mushroom cap, wall) are flat clusters of one ramp color.
- Do not dither. The ingest default is nearest color, dither off.

## Faction silhouettes

Readable at 16×28, before color. Color then confirms it.

| Faction | Silhouette | Color | Keep |
| --- | --- | --- | --- |
| Azure | Narrow human, shield and upright weapon, straight back | `azure` armor, `ice` glint, `gold` trim, violet crystal on the keep | Tall rectilinear fort, banner, crystal spires |
| Crimson | Wide hunched body, big arms, low head, heavy weapon | `crimson` skin, dark armor from `crimson_shadow` and `stone`, fire on the camp | Low camp, braziers, ragged banners |
| Verdant | Slim, hood or pointed ears, staff or bow, cloak narrower than the orc | `verdant` cloth, mushroom caps in `crimson_lit` | Grove, trunks, red and green caps |
| Undead | Skull reads as `bone_hot` on `bone_shadow`. Thin limbs. Necromancer is a triangle robe in `violet` with a staff. | Bone ramp, violet cloth | Portal arch, not a faction keep |
| Golem | Much wider than a humanoid. `stone` and `ash` body, `gold` cracks, small `bone_hot` teeth. Uses the 32×36 boss canvas. | Stone ramp plus gold | Not a settlement tier |

Teams in code stay `azure`, `crimson`, and `verdant`. Shared undead and necromancer stay under `art/units/shared/`. Monsters stay under `art/units/monsters/`.

## FX

Hard-edged clusters, 4 frames, 16×16, centered. The loop (torch, portal, fire, plague, bless, dust, hex) already loads `{name}_0` … `{name}_3`.

- Fireball: `ember` → `fire` → `flame` → one `spark` pixel. No smoke color outside `ash` / `haze`.
- Cyan circle: concentric rings of `cyan_shadow`, `cyan`, `cyan_hot`, `cyan_core`.
- Portal: `violet` arch with a `violet_hot` core. Skeletons are units, not part of the FX frame.
- Select ring and ground shadow stay separate textures so units do not carry them.

## UI

- Field: `abyss`. Outer trim: 1px `gold`. Inner line: `dusk` or `gold_dark`.
- Title and primary text: m5x7, color near `flame` / the current `#e6dcc8` labels. Secondary text: `ash` or `haze`.
- Do not antialias the font. Do not replace m5x7 in this art pass.
- Buttons keep a 6px nine-slice. Pressed state is the same skin one step darker, icon shifted one pixel down.
- Minimap frame uses the same trim. No glossy gradients, no roundrects smoother than the pixel grid.

## Ingest rules that follow from this

`tools/ingest_ai.py` is how a generated PNG becomes a file the game can load:

1. Flat chroma background, default pure magenta `#FF00FF`. No floor and no cast shadow in that background.
2. Mode-pool down to the canvas size above. No bilinear filter.
3. Quantize to `art/style/palette.png` with dithering off.
4. Optional 1px `void` outline on units, props, and buildings.
5. Alpha forced to 0 or 255. Feet sit on the bottom row of the unit canvas.

Prompts that match these rules are in `tools/prompt_templates.md`. The command loop is in `tools/README.md`.
