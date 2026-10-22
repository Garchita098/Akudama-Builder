extends RefCounted
# Original sampled soldier artwork, encoded losslessly as palette-index pixels.
const PALETTES = [
["#979295","#776f72","#5b545b","#573f31","#2d3b5c","#3d281e","#29282c","#2b1b12","#111b32","#0f0c0c","#060303","#010102","#000103","#000100","#000000"],
["#a28267","#825f47","#744633","#763020","#3d2e1f","#81100f","#3f140c","#1e1510","#130805","#3e0104","#060101","#020101","#020000","#000100","#000000"],
["#938067","#4a5d3f","#63442a","#2b412b","#4a2d18","#2f2b1f","#2e190e","#152419","#171610","#0c0c07","#060402","#010201","#000100","#000001","#000000"]]
const PIXELS = [
"fffffff44444444fffffffffffff944448fffffffffffffff7447fffffffffffffffff33fffffffffffffffffffffffffffffffffffff3ffffffffffffffffff814ffffffffffffffff91008fffffffffffffff84004fff6fffffffff7752424fff31ffffffff77932159ff906ffffff823846699f5340ffffff2039416fff15906fff93242569faf016922ffff7331733371221a61fff336595212932117906ff615ff8414f33205f13ff449ff9848f73326f22f525ff95577ff3743a42f733ff86737ff53837f475637f4478839f399ff4ff12773364651f757ff6f906f73658362ffffffff60fffffff757ffffffff20ff97fff997ffffffff10ff39ffff539ffffff",
"fffffff95533555fffffffffffff955556fffffffffffffff6555fffffffffffffffff55fffffffffffffffffffffffffffffffffffff47ffffffffffffffffff518ffffffffffffffff5005fffffffffffffff750059fffffffffffff4425337fffffffffffff2f210188ff43fffffff917444489f103ffffff90348214f700964ffff43534877f4003564ffff7231342480151164fff724447432921554437ff7127ff552841301466ff9567f8955871311366ff226ff8777ff1351467f7424f667448f335446682444f5558769f295466ff414f6355534f449747ff00ff4465541ff2473fff04f88ff6676ff8326ff70ff87ffff86ffffffff40f847aff863fffffff",
"fffffff3371333ffffffffffffff83737ffffffffffffffff433ffffffffffffffffff2ffffffffffffffffffffffffffffffffffffff46fffffffffffffffff831fffffffffffffffff3003fffffffffffffff83003fffffffffffff62621118ffffffffffff82f120264ffffffffff3108333764f42ffffff9301491186a3026fffff217124ffff10474ffffff24054221002372ffff4059651150071054ffff5028f971321100266fff116ffff9f40100286ff504fff6646f0330276ff4225f77826f2431486f64526f32678f6273286fff01482243349257566ff505f81643369628768ff10ff89ff78fff4252ffa00ff8fffff8fff624ff801f85fffff85fffffff"]

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
