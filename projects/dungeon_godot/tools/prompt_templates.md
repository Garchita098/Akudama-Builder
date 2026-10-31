# Prompt templates for Living Dungeon

Paste one block into the image generator. Keep the lines. Replace the `{BRACKETS}`. The generator runs outside this repo. Save a PNG and run `tools/ingest_ai.py` (see `tools/README.md`).

These prompts match `art/STYLE_BIBLE.md`:

- 3/4 view, facing right, orthographic. The game is still an orthogonal grid. Do not ask for isometric diamonds.
- Flat magenta `#FF00FF` behind the subject. No floor, no scenery, no cast shadow.
- Hard pixel clusters, no anti-aliasing, no gradients, no dithering, no text.
- Key light from the upper right. One-pixel near-black outline on characters, props, and buildings.
- Colors from the master palette only: indigo and violet stone, azure / crimson / verdant factions, cyan magic, orange fire, gold trim, bone.

Ingest reduces the PNG to the size in the template. A 1024px image of a 16×28 figure is the expected input. Do not draw the final 16×28 file by hand inside a huge canvas with a thick border of empty pixels around a tiny sprite; let the figure fill most of the frame, with magenta around it.

## Shared prefix

Put this at the top of every prompt:

```
Living Dungeon pixel art, dark fantasy. Hard-edged clusters of flat color, no anti-aliasing, no soft brush, no gradients, no dithering, no bloom, no photo texture, no text, no watermark, no frame, no label.

Palette only: near-black indigo #04040C, abyss #090A18, dusk #191A32, violet floor #3B2C37, slate #242C59, steel #3C4B8C, ice #90A3D0, azure #475EA1 and #7A9AD5, violet crystal #2C0E4A #51108D #B153E7, cyan magic #0F6673 #4BD7DE #6BEDF1, crimson #5A241D #903720 #C85C24, fire #A44624 #D56B1E #FFCE6B #FFF7BF, gold trim #634C2E #B59465, verdant #1B2918 #405B22 #6D8C36 #B1C781, bone #574B44 #9F9281 #D8D6C1 #FAFAEB.

Key light from the upper right. Lit planes face up-right. Form shadow on the lower left, one step darker, no second shadow color. At most four shades on a material. One-pixel specular only on metal, crystal, wet bone, and fire.

Background is one flat color, pure magenta #FF00FF, every pixel that is not the subject. The subject does not touch the image edge. No ground plane, no floor tile, no cast shadow, no contact shadow, no oval shadow, no scenery, no fog overlay.
```

## Shared negative block

Append this when the generator has a separate negative prompt:

```
isometric diamond, oblique floor grid, side scroller, front portrait, turnaround sheet, 3d render, painterly, oil paint, smooth gradient, anti-aliasing, soft shadow, drop shadow, ground, grass, stone floor, scenery, background scene, text, letters, numbers, watermark, border, frame, UI chrome, magenta fringe, pink outline, colored outline other than near-black
```

## Unit, four idle frames

Canvas after ingest: 16×28, feet on the bottom row. `--kind units --faction {FACTION} --name {ROLE}_idle --size 16x28 --anchor feet --outline`

```
{PREFIX}

A horizontal strip of exactly 4 frames of one {FACTION} {ROLE}, same character, same scale, same height, feet on one shared baseline. Frames separated by at least 80 pixels of pure magenta #FF00FF. Left to right: standing idle, breathing (chest and weapon up one pixel), weight shifted, standing idle again. No labels, no numbers, no boxes around frames.

Three-quarter view from slightly above and in front, orthographic, facing right. Not isometric. The whole figure, including the weapon, fits in a tall portrait cell about twice as tall as it is wide. Chunky readable shapes. One-pixel near-black outline.

{FACTION LOOK}
```

Faction look lines:

- Azure knight: narrow armored human, heater shield and upright sword, straight back. Armor azure `#475EA1` and `#7A9AD5`, helm glint ice `#90A3D0`, one gold `#B59465` buckle. No cape that hides the shield.
- Azure guard: same armor, spear upright, narrower shield.
- Azure worker: same faction colors, hood and hammer, no plate helm.
- Azure mage: slimmer robe in azure and dusk `#191A32`, short staff, one violet `#51108D` crystal.
- Crimson orc warrior: wide hunched body, big arms, low head, heavy axe. Skin crimson `#5A241D` to `#C85C24`, armor crimson_shadow and stone. Wider than the knight, shorter inside the same canvas.
- Crimson guard: same orc, cleaver and a small round shield.
- Crimson worker: same orc, pickaxe, no shield.
- Crimson mage: hunched orc in a dark red wrap, skull staff, one ember pixel.
- Verdant elf warrior: slim, pointed ears or hood, leaf cloak verdant `#405B22` and `#6D8C36`, slim blade.
- Verdant guard: same elf, bow or spear, cloak narrower than the orc.
- Verdant worker: same elf, basket or sickle.
- Verdant mage: same elf, staff topped with a mushroom cap `#903720`.
- Necromancer (`--faction shared --name necro_idle`): triangle robe in violet `#2C0E4A` and `#51108D`, bone staff, skull face in bone `#D8D6C1`.
- Skeleton (`--faction shared --name undead_idle`, ingest `--size 16x16`): thin skull and ribs, bone ramp only, eye is one `void` pixel. Short canvas.
- Goblin (`--faction monsters --name goblin_idle`, `--size 16x16`): small, wide ears, verdant skin, crude knife.
- Chort (`--faction monsters --name chort_idle`, `--size 16x28`): stocky horned beast, crimson and ember.
- Demon boss (`--faction monsters --name demon_idle`, `--size 32x36`): much larger than a humanoid, wings or horns inside the canvas, crimson and violet.
- Golem boss (`--name golem_idle`, `--size 32x36`, `--faction monsters`): wide stone body `#2C2D2C` and `#5A5559`, gold `#B59465` cracks, small bone teeth. Not a human silhouette.

## Unit, four run frames

Same flags with `--name {ROLE}_run`.

```
{PREFIX}

A horizontal strip of exactly 4 run-cycle frames of the same {FACTION} {ROLE} already established for Living Dungeon. Same scale, same baseline, facing right, three-quarter view, orthographic, not isometric. Frames separated by at least 80 pixels of pure magenta #FF00FF. Left to right: contact, passing, contact opposite, passing. Arms and weapon move. The body does not slide up and down between frames. No labels, no dust cloud, no shadow.

{FACTION LOOK}

One-pixel near-black outline.
```

## Unit, one attack frame

`--force-index` so the file is `{ROLE}_hit_0.png`.

```
{PREFIX}

One frame only. The same {FACTION} {ROLE}, three-quarter view facing right, orthographic, caught mid-swing. Weapon extended toward the right. Same scale as the idle. Feet planted. Pure magenta #FF00FF background, no shadow, no hit spark (the spark is a separate effect). One-pixel near-black outline.

{FACTION LOOK}
```

## Floor tile

Full-bleed. Ingest with `--key none --kind tiles --size 16x16 --anchor center`. Do not pass `--outline`.

```
{PREFIX}

One square top-down floor tile, orthographic, seen straight from above. Not isometric, not a diamond, not 3/4. The tile fills the entire image edge to edge. No magenta, no border, no outline, no props, no character. Seamless on all four edges: the left edge continues the right edge, the top continues the bottom.

Motif: {MOTIF}
```

Motifs: `violet dungeon flagstones #3B2C37 and #191A32`, `cracked stone with one ash mortar line`, `mossy verdant crack on the same stone`, `ember-lit flagstone with one fire pixel in a crack`.

## Wall or prop

Props may be transparent. Walls that autotile must be full-bleed 16×16 with `--key none`.

```
{PREFIX}

One game prop, {SUBJECT}, three-quarter view, facing right, orthographic, sitting with its base at the bottom of the frame. It will be reduced to 16x16 pixels. Pure magenta #FF00FF background. No floor, no shadow. One-pixel near-black outline. Readable silhouette at a glance.

Subject detail: {DETAIL}
```

Examples for `{DETAIL}`: `wooden crate, iron bands in ash and gold_dark`, `gray rock, stone and ash`, `red-cap mushroom #903720 with bone stem`, `skull in bone ramp, facing right`, `pile of bones`, `small puddle using cyan_shadow only`.

## Building

`--kind buildings --name tier{N}_{FACTION} --size {SIZE} --anchor feet --outline`

Sizes: tier 0 `48x48`, tier 1 `64x64`, tier 2 `96x80`.

```
{PREFIX}

One settlement building for the {FACTION} faction, three-quarter view facing right, orthographic, not isometric. The base of the building sits on the bottom of the frame. Pure magenta #FF00FF background. No ground, no troops, no shadow. One-pixel near-black outline. It will be reduced to {SIZE} pixels.

{BUILDING}
```

Buildings:

- Azure tier 0: small stone gatehouse, dusk walls, azure banner, one gold trim.
- Azure tier 1: taller keep, battlements, azure banners, one violet crystal.
- Azure tier 2: fortress with two crystal spires `#B153E7`, blue banners, gold emblem. Still one building, not a whole castle scene.
- Crimson tier 0: low camp hut, hide and timber, one brazier of fire colors.
- Crimson tier 1: palisade hall, ragged red banner, two braziers.
- Crimson tier 2: war camp keep, tusks or spikes, braziers, crimson banners. Wider than the azure keep.
- Verdant tier 0: stump shrine and one red mushroom cap.
- Verdant tier 1: living hall of trunks and moss, green banners.
- Verdant tier 2: grove tower grown from trees, several mushroom caps, verdant banners.

## Effect, four frames

`--kind fx --name {NAME} --size 16x16 --anchor center`. No `--outline`. Names the game already loads: `torch`, `portal`, `fire`, `plague`, `bless`, `dust`, `hex`.

```
{PREFIX}

A horizontal strip of exactly 4 frames of one effect, {EFFECT}, centered in each cell, same scale. Cells separated by at least 64 pixels of pure magenta #FF00FF. No character, no floor, no shadow, no outline in near-black. The darkest pixel is the darkest step of this effect's own ramp. No labels.

{EFFECT DETAIL}
```

Details:

- `torch`: a small flame only, ember bowl implied in two pixels, loop of `fire`, `flame`, `spark`.
- `portal`: a narrow violet arch with a brighter core, four frames of the core flickering. No skeletons.
- `fire`: a fireball burst, ember to spark, four frames of expansion. No smoke except `ash`.
- `plague`: a compact cloud of verdant and rose, four frames.
- `bless`: a small upright glint of `flame` and `ice`, four frames.
- `dust`: a low puff of `ash` and `haze`, four frames.
- `hex`: a violet spark, four frames, no circle (the circle is its own texture).

Cyan circle, one frame, `--name circle --size 16x16 --anchor center`:

```
{PREFIX}

One cyan magic circle, seen from above, centered, concentric rings only: #112E39, #0F6673, #4BD7DE, #6BEDF1. No rune text, no character, no floor. Pure magenta #FF00FF outside the circle. It will be reduced to 16x16. No black outline.
```

## UI icon and skins

Icon: `--kind ui --name {NAME} --size 16x16 --anchor center --outline`

```
{PREFIX}

One interface icon of {ICON}, centered, three-quarter or straight symbol, readable at 16x16. Pure magenta #FF00FF background. One-pixel near-black outline. Gold #B59465 and flame #FFCE6B on an abyss #090A18 shape. No text. No button behind it.
```

Icons that match the target bar: backpack, crossed swords, skull, eagle, crossed axes, hammer, gear.

Panel skin (only if a panel is being replaced): full-bleed 48×48, `--key none --size 48x48`, nine-slice with 8 pixels of corner that must survive stretching. Field `abyss`, 1px `gold` outer edge, 1px `dusk` inner edge. No icon in the center.

Button skin: full-bleed 32×32, `--key none`, 6 pixels of corner. Same trim. Pressed state is the same skin one step darker.
