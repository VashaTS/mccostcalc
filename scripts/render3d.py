"""Isometric inventory-style renderer for Minecraft block models (Pillow + numpy)."""
from __future__ import annotations
import io, json, math
import numpy as np
from PIL import Image

SIZE = 64
DEFAULT_GUI = {"rotation": [30, 225, 0], "translation": [0, 0, 0], "scale": [0.625, 0.625, 0.625]}
SHADE = {"up": 1.0, "down": 0.5, "north": 0.8, "south": 0.8, "east": 0.6, "west": 0.6}
NORMALS = {"up": (0, 1, 0), "down": (0, -1, 0), "north": (0, 0, -1), "south": (0, 0, 1),
           "east": (1, 0, 0), "west": (-1, 0, 0)}
TINT = np.array([0.50, 0.74, 0.30])  # generic grass/foliage green
FLAT_PARENTS = {"item/generated", "item/handheld", "item/handheld_rod", "builtin/generated",
                "builtin/entity", "item/handheld_mace"}


def ns(s):
    return s.split(":", 1)[1] if ":" in s else s


def load_chain(zf, names, model):
    """Return list of model dicts from child to root, or None if flat/unresolvable."""
    chain, cur = [], ns(model)
    for _ in range(12):
        if cur in FLAT_PARENTS:
            return None
        path = f"assets/minecraft/models/{cur}.json"
        if path not in names:
            return chain or None
        d = json.loads(zf.read(path))
        chain.append(d)
        if "parent" not in d:
            break
        cur = ns(d["parent"])
    return chain


CHEST_TEXTURE = {
    "chest": "entity/chest/normal",
    "trapped_chest": "entity/chest/trapped",
    "ender_chest": "entity/chest/ender",
    "copper_chest": "entity/chest/copper",
    "exposed_copper_chest": "entity/chest/copper_exposed",
    "weathered_copper_chest": "entity/chest/copper_weathered",
    "oxidized_copper_chest": "entity/chest/copper_oxidized",
    "waxed_copper_chest": "entity/chest/copper",
    "waxed_exposed_copper_chest": "entity/chest/copper_exposed",
    "waxed_weathered_copper_chest": "entity/chest/copper_weathered",
    "waxed_oxidized_copper_chest": "entity/chest/copper_oxidized",
}


def item_model_name(zf, names, base):
    if base in CHEST_TEXTURE or base.replace("waxed_", "") in CHEST_TEXTURE:
        return "__chest__:" + CHEST_TEXTURE.get(base, CHEST_TEXTURE.get(base.replace("waxed_", ""), "entity/chest/normal"))
    p = f"assets/minecraft/items/{base}.json"
    if p in names:
        def leaf(m):
            if isinstance(m, dict):
                typ = ns(m.get("type", "") or "")
                if typ == "chest" and m.get("texture"):
                    tex = ns(m["texture"])
                    return "__chest__:entity/chest/" + tex
                if typ in {"model", "minecraft:model"} or typ.endswith("model") and typ != "special":
                    if isinstance(m.get("model"), str):
                        return m["model"]
                for k in ("fallback", "on_false", "on_true", "model"):
                    if k in m:
                        r = leaf(m[k])
                        if r:
                            return r
                for e in m.get("cases", []) + m.get("entries", []):
                    r = leaf(e)
                    if r:
                        return r
            return None
        r = leaf(json.loads(zf.read(p)))
        if r:
            return r
    if f"assets/minecraft/models/item/{base}.json" in names:
        return f"item/{base}"
    return None


def rot_matrix(rx, ry, rz):
    rx, ry, rz = map(math.radians, (rx, ry, rz))
    X = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]])
    Y = np.array([[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]])
    Z = np.array([[math.cos(rz), -math.sin(rz), 0], [math.sin(rz), math.cos(rz), 0], [0, 0, 1]])
    return X @ Y @ Z


def face_corners(face, f, t):
    x0, y0, z0 = f; x1, y1, z1 = t
    c = {
        "up":    ((x0, y1, z0), (x1, y1, z0), (x0, y1, z1), [x0, z0, x1, z1]),
        "down":  ((x0, y0, z1), (x1, y0, z1), (x0, y0, z0), [x0, 16 - z1, x1, 16 - z0]),
        "north": ((x1, y1, z0), (x0, y1, z0), (x1, y0, z0), [16 - x1, 16 - y1, 16 - x0, 16 - y0]),
        "south": ((x0, y1, z1), (x1, y1, z1), (x0, y0, z1), [x0, 16 - y1, x1, 16 - y0]),
        "west":  ((x0, y1, z0), (x0, y1, z1), (x0, y0, z0), [z0, 16 - y1, z1, 16 - y0]),
        "east":  ((x1, y1, z1), (x1, y1, z0), (x1, y0, z1), [16 - z1, 16 - y1, 16 - z0, 16 - y0]),
    }
    return c[face]


def texture_ref(v):
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return v.get("sprite") or v.get("id") or v.get("texture")
    return None


def load_tex(zf, names, ref, cache):
    ref = texture_ref(ref)
    if not ref:
        return None
    key = ns(ref)
    if key in cache:
        return cache[key]
    path = f"assets/minecraft/textures/{key}.png"
    arr = None
    if path in names:
        im = Image.open(io.BytesIO(zf.read(path))).convert("RGBA")
        w = im.width
        if im.height > w:  # animated strip: first frame
            im = im.crop((0, 0, w, w))
        arr = np.asarray(im).astype(np.float32)
    cache[key] = arr
    return arr


def render_model(zf, names, model, tex_cache=None):
    tex_cache = {} if tex_cache is None else tex_cache
    chain = load_chain(zf, names, model)
    if not chain:
        return None
    return _render_resolved(zf, names, chain, tex_cache)


def _render_resolved(zf, names, chain, tex_cache):
    textures, elements, gui = {}, None, None
    for d in reversed(chain):  # root first, child overrides
        textures.update(d.get("textures", {}))
        if "elements" in d:
            elements = d["elements"]
        if "display" in d and "gui" in d["display"]:
            gui = d["display"]["gui"]
    if not elements:
        return None
    gui = {**DEFAULT_GUI, **(gui or {})}

    def resolve(v, depth=0):
        v = texture_ref(v) or v
        while isinstance(v, str) and v.startswith("#") and depth < 10:
            v = texture_ref(textures.get(v[1:]))
            depth += 1
        return v if isinstance(v, str) else None

    R = rot_matrix(*gui["rotation"])
    sc = np.array(gui["scale"], dtype=float)
    tr = np.array(gui.get("translation", [0, 0, 0]), dtype=float)
    px = SIZE / 16.0

    color = np.zeros((SIZE, SIZE, 4), np.float32)
    zbuf = np.full((SIZE, SIZE), -1e9, np.float32)
    ys, xs = np.mgrid[0:SIZE, 0:SIZE]
    pts = np.stack([xs + 0.5, ys + 0.5], -1).reshape(-1, 2)

    def project(p):
        v = (np.array(p, float) - 8.0) * sc
        v = R @ v + tr
        return np.array([SIZE / 2 + v[0] * px, SIZE / 2 - v[1] * px]), v[2]

    drew = False
    for el in elements:
        f, t = el["from"], el["to"]
        erot = el.get("rotation")
        for face, fd in (el.get("faces") or {}).items():
            if face not in NORMALS:
                continue
            n = R @ np.array(NORMALS[face], float)
            if erot is None and n[2] <= 1e-6:
                continue
            tex = load_tex(zf, names, resolve(fd.get("texture", "")) or "", tex_cache)
            if tex is None:
                continue
            tl, trc, bl, duv = face_corners(face, f, t)
            corners3 = [tl, trc, bl]
            if erot:  # element rotation around origin
                ax, ang = erot.get("axis", "y"), erot.get("angle", 0)
                org = np.array(erot.get("origin", [8, 8, 8]), float)
                M = rot_matrix(*(ang if a == ax else 0 for a in "xyz"))
                corners3 = [M @ (np.array(c, float) - org) + org for c in corners3]
                nn = R @ (M @ np.array(NORMALS[face], float))
                if nn[2] <= 1e-6:
                    continue
            (a, za), (b, zb), (c, zc) = [project(p) for p in corners3]
            e1, e2 = b - a, c - a
            det = e1[0] * e2[1] - e1[1] * e2[0]
            if abs(det) < 1e-6:
                continue
            d = pts - a
            u = (d[:, 0] * e2[1] - d[:, 1] * e2[0]) / det
            v = (e1[0] * d[:, 1] - e1[1] * d[:, 0]) / det
            inside = (u >= 0) & (u < 1) & (v >= 0) & (v < 1)
            if not inside.any():
                continue
            uv = fd.get("uv", duv)
            rot = int(fd.get("rotation", 0)) % 360
            uu, vv = u[inside], v[inside]
            for _ in range(rot // 90):
                uu, vv = vv, 1 - uu
            th, tw = tex.shape[:2]
            su = (uv[0] + (uv[2] - uv[0]) * uu) / 16 * tw
            sv = (uv[1] + (uv[3] - uv[1]) * vv) / 16 * th
            ti = np.clip(sv.astype(int), 0, th - 1); tj = np.clip(su.astype(int), 0, tw - 1)
            samp = tex[ti, tj].copy()
            keep = samp[:, 3] > 8
            if not keep.any():
                continue
            shade = SHADE[face]
            samp[:, :3] *= shade
            if "tintindex" in fd:
                samp[:, :3] *= TINT
            depth = za + (zb - za) * u[inside] + (zc - za) * v[inside]
            idx = np.nonzero(inside)[0][keep]
            depth = depth[keep]; samp = samp[keep]
            yy, xx = idx // SIZE, idx % SIZE
            better = depth >= zbuf[yy, xx] - 1e-4
            yy, xx = yy[better], xx[better]
            zbuf[yy, xx] = depth[better]
            color[yy, xx] = samp[better]
            drew = True
    if not drew:
        return None
    return Image.fromarray(np.clip(color, 0, 255).astype(np.uint8), "RGBA")


def chest_elements():
    """Approximate vanilla chest (14x14x14 inset box + lid + latch), UVs in 0-16 for a 64px texture."""
    def uv(x, y, w, h):
        return [x / 4, y / 4, (x + w) / 4, (y + h) / 4]

    body = {
        "from": [1, 0, 1], "to": [15, 10, 15],
        "faces": {
            "down":  {"uv": uv(28, 19, 14, 14), "texture": "#0", "rotation": 180},
            "up":    {"uv": uv(14, 19, 14, 14), "texture": "#0"},
            "north": {"uv": uv(42, 33, 14, 10), "texture": "#0"},
            "south": {"uv": uv(14, 33, 14, 10), "texture": "#0"},
            "west":  {"uv": uv(0, 33, 14, 10), "texture": "#0"},
            "east":  {"uv": uv(28, 33, 14, 10), "texture": "#0"},
        },
    }
    lid = {
        "from": [1, 9, 1], "to": [15, 14, 15],
        "faces": {
            "down":  {"uv": uv(14, 0, 14, 14), "texture": "#0"},
            "up":    {"uv": uv(28, 0, 14, 14), "texture": "#0"},
            "north": {"uv": uv(42, 14, 14, 5), "texture": "#0"},
            "south": {"uv": uv(14, 14, 14, 5), "texture": "#0"},
            "west":  {"uv": uv(0, 14, 14, 5), "texture": "#0"},
            "east":  {"uv": uv(28, 14, 14, 5), "texture": "#0"},
        },
    }
    latch = {
        "from": [7, 7, 15], "to": [9, 11, 16],
        "faces": {
            "up":    {"uv": uv(1, 0, 2, 1), "texture": "#0"},
            "down":  {"uv": uv(3, 0, 2, 1), "texture": "#0"},
            "north": {"uv": uv(1, 1, 2, 4), "texture": "#0"},
            "south": {"uv": uv(3, 1, 2, 4), "texture": "#0"},
            "west":  {"uv": uv(0, 1, 1, 4), "texture": "#0"},
            "east":  {"uv": uv(3, 1, 1, 4), "texture": "#0"},
        },
    }
    return [body, lid, latch]


def render_chest(zf, names, texture, tex_cache=None):
    tex_cache = {} if tex_cache is None else tex_cache
    model = {
        "parent": "block/block",
        "textures": {"0": texture},
        "elements": chest_elements(),
        "display": {"gui": DEFAULT_GUI},
    }
    # Inject a temporary in-memory model by writing into a side channel
    return render_model_from_dict(zf, names, model, tex_cache)


def render_model_from_dict(zf, names, data, tex_cache=None):
    """Render a model dict (used for synthetic chests) using the same pipeline."""
    # Build a fake chain: only this dict, but inherit display from block/block if needed.
    import zipfile
    # Reuse render_model by pointing at a virtual parent. Easier to temporarily
    # copy the main loop — call render_model on a private wrapper via textures/elements injection.
    return _render_resolved(zf, names, [data], tex_cache or {})


# Split out the core of render_model so both paths can use it. We wrap by
# monkeypatching load_chain for the chest case via a marker model name.
def render_item(zf, names, base, tex_cache=None):
    model = item_model_name(zf, names, base)
    if not model:
        model = f"block/{base}"
    if isinstance(model, str) and model.startswith("__chest__:"):
        tex = model.split(":", 1)[1]
        if f"assets/minecraft/textures/{tex}.png" in names:
            return render_chest(zf, names, tex, tex_cache)
        return None
    return render_model(zf, names, model, tex_cache)
