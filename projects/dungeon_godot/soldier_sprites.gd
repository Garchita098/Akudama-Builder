extends RefCounted
# Original sampled soldier artwork, encoded losslessly as palette-index pixels.
const PALETTES = [["#4a4540","#5a5550","#6a6560","#7a7560","#3a3530","#8a8570","#ffeedd","#2a2520","#1a1510","#9a9580","#0a0a0a","#1a1a1a","#2a2a2a","#3a3a3a","#4a4a4a"],["#5a4030","#6a5040","#7a6050","#8a7060","#4a3020","#9a8070","#ffeedd","#3a2010","#2a1000","#aa9080","#0a0a0a","#1a1a1a","#2a2a2a","#3a3a3a","#4a4a4a"],["#3a4a30","#4a5a40","#5a6a50","#6a7a60","#2a3a20","#7a8a70","#ffeedd","#1a2a10","#0a1a00","#8a9a80","#0a0a0a","#1a1a1a","#2a2a2a","#3a3a3a","#4a4a4a"]]
const PIXELS = ["ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff4444ffffffffffffffff4444ffffffffffffffff3333ffffffffffffffff3663ffffffffffffffff3333fffffffffffffff133331ffffffffffffff111111fffffffffffff11111111ffffffffffff11111111ffffffffffff11111111ffffffffffff11111111fffffffffffff111111ffffffffffffff222222ffffffffffffff222222ffffffffffffff202202fffffffffffffff0ff0ffffffffffffffff0ff0ffffffffffffffff0ff0ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff","ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff4444ffffffffffffffff4444ffffffffffffffff3333ffffffffffffffff3663ffffffffffffffff3333fffffffffffffff133331ffffffffffffff111111f5fffffffffff111111115fffffffffff111111115fffffffffff111111115fffffffffff11111111fffffffffffff111111ffffffffffffff222222ffffffffffffff222222ffffffffffffff202202fffffffffffffff0ff0ffffffffffffffff0ff0ffffffffffffffff0ff0ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff","ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff4444ffffffffffffffff4444ffffffffffffffff3333ffffffffffffffff3663ffffffffffffffff3333fffffffffffffff133331ffffffffffffff111111fffffffffffff11111111ffffffffffff11111111ffffffffffff11111111ffffffffffff11111111fffffffffffff111111ffffffffffffff222222ffffffffffffff222222ffffffffffffff202202fffffffffffffff0ff0ffffffffffffffff0ff0ffffffffffffffff0ff0ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"]

static func build() -> Array[Texture2D]:
    var result: Array[Texture2D] = []
    for i in range(3):
        var image := Image.create(20,26,false,Image.FORMAT_RGBA8)
        var pixels: String = PIXELS[i]
        for y in range(26):
            for x in range(20):
                var c: String = pixels.substr(y*20+x,1)
                if c == "f":
                    image.set_pixel(x,y,Color.TRANSPARENT)
                else:
                    var id: int = "0123456789abcde".find(c)
                    image.set_pixel(x,y,Color.html(PALETTES[i][id]))
        result.append(ImageTexture.create_from_image(image))
    return result
