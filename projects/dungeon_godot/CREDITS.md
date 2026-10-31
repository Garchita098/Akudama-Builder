# Art credits

Living Dungeon draws sliced and, where noted, recolored copies of these assets.
The tile simulation, save format, and combat rules do not depend on the pictures.

## DungeonTileset II v1.7

- Author: Robert (0x72). The tileset page also credits GrafxKid for recolor help.
- License: [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/)
- Source: https://0x72.itch.io/dungeontileset-ii
- Local copy: `third_party/0x72/` (sheet, low-wall autotile atlas, frame list, README)
- Used for floors, wall autotiles, characters (knight, elf, orc, wizard, dwarf, necromancer, skeleton), monsters (goblin, chort, big demon), props (crate, skull, door, banners, columns), and settlement pieces.
- `tools/build_visual_art.py` punches the autotile's flat void color so the floor shows through, builds a solid interior brick from the same palette, and recolors dwarf and wizard cloth toward the three faction hues. Knights, elves, and orcs keep their original colors.

## m5x7

- Author: Daniel Linssen
- License: [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/)
- Source: https://managore.itch.io/m5x7
- File: `fonts/m5x7.ttf`
- Used for the on-screen interface. Attribution is not required; it is recorded here anyway.

## Original pieces

Torches, portal frames, rocks, mushrooms, moss, puddles, embers, bones, spell bursts, the light gradient, shadows, the selection ring, and the panel and button skins are original pixel art painted for this project in `tools/build_visual_art.py`. They use the dungeon palette so they sit next to the tileset.
