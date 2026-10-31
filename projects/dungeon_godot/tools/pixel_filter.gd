extends RefCounted
class_name LivingDungeonPixelArt
## Nearest-neighbor sampling for textures written by tools/assets.py.
## Godot 4.4 stores this on the CanvasItem, not in the PNG .import file.
## The running game does not call this; placeholder art is unchanged.

static func configure(item: CanvasItem) -> void:
    item.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
