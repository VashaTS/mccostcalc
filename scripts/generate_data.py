#!/usr/bin/env python3
"""Regenerate mccostcalc recipe data from official Minecraft client jars.

Downloads client jars from Mojang's version manifest, extracts crafting /
smelting / smithing / brewing recipes, and writes JSON + item icons consumed
by the static web app.

Usage:
  python3 scripts/generate_data.py                  # default major versions
  python3 scripts/generate_data.py --versions 26.3  # one version
  python3 scripts/generate_data.py --list           # show latest release
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import render3d
except ImportError:  # pragma: no cover
    render3d = None

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
USER_AGENT = "mccostcalc-data-generator/1.0 (https://github.com/VashaTS/mccostcalc)"

# Last version of each major line the original app's era, plus every major
# since, plus the latest release. --versions can override.
DEFAULT_VERSIONS = [
    "1.13.2",  # version the original PHP app targeted
    "1.14.4",
    "1.15.2",
    "1.16.5",
    "1.17.1",
    "1.18.2",
    "1.19.4",
    "1.20.1",
    "1.20.6",
    "1.21.1",
    "1.21.4",
    "1.21.11",
    "26.1.2",
    "26.2",
    "26.3",
]

PREFERRED_TAG_ITEMS = [
    "oak_planks",
    "oak_log",
    "oak_wood",
    "oak_slab",
    "oak_stem",
    "cobblestone",
    "cobbled_deepslate",
    "stone",
    "sand",
    "red_sand",
    "white_wool",
    "white_dye",
    "white_bed",
    "glass",
    "stick",
    "iron_ingot",
]

COLORS = [
    "white", "orange", "magenta", "light_blue", "yellow", "lime", "pink",
    "gray", "light_gray", "grey", "light_grey", "cyan", "purple", "blue",
    "brown", "green", "red", "black",
]

COLORED_KINDS = (
    "glass", "terracotta", "concrete", "wool", "banner", "carpet", "bed",
    "candle", "shulker", "harness", "stained",
)

# Smelting these results from ores / raw metals should not be used: the
# calculator treats the ingot/gem itself as the gathered material.
MINERAL_RESULTS = {
    "iron_ingot", "gold_ingot", "copper_ingot", "diamond", "emerald", "coal",
    "redstone", "lapis_lazuli", "quartz", "gold_nugget", "iron_nugget",
    "copper_nugget", "redstone_dust",
}

# Default burn times in furnace operations (200 ticks = 1).
DEFAULT_FUEL = {
    "coal": 8,
    "charcoal": 8,
    "coal_block": 80,
    "lava_bucket": 100,
    "blaze_rod": 12,
    "oak_planks": 1.5,
    "oak_log": 1.5,
    "stick": 0.5,
    "oak_sapling": 0.5,
}

# Mob drop rates: kills needed per 1 item (same philosophy as the original
# app). Looting III column is optional.
MOB_DROPS = {
    "rabbit_foot": ("rabbit", 40, 18.1818),
    "rabbit_hide": ("rabbit", 2, 0.5),
    "beef": ("cow", 0.5, 0.2857),
    "raw_beef": ("cow", 0.5, 0.2857),
    "leather": ("cow", 1, 0.4),
    "ghast_tear": ("ghast", 2, 0.5),
    "gunpowder": ("creeper", 1, 0.4),
    "slime_ball": ("tiny_slime", 1, 0.4),
    "porkchop": ("pig", 0.5, 0.2857),
    "raw_porkchop": ("pig", 0.5, 0.2857),
    "feather": ("chicken", 1, 0.4),
    "chicken": ("chicken", 1, 0.5),
    "raw_chicken": ("chicken", 1, 0.5),
    "rabbit": ("rabbit", 1, 0.5),
    "raw_rabbit": ("rabbit", 1, 0.5),
    "ink_sac": ("squid", 0.5, 0.2857),
    "prismarine_crystals": ("guardian", 4.9, 1.984),
    "prismarine_shard": ("guardian", 2.45, 0.992),
    "string": ("spider", 1, 0.4),
    "spider_eye": ("spider", 3, 1.2165),
    "mutton": ("sheep", 0.6667, 0.6667),
    "raw_mutton": ("sheep", 0.6667, 0.6667),
    "blaze_rod": ("blaze", 2, 0.5),
    "bone": ("skeleton", 1, 0.4),
    "ender_pearl": ("enderman", 2, 0.5),
    "wither_skeleton_skull": ("wither_skeleton", 40, 18.1818),
    "iron_ingot": ("iron_golem", 0.25, 0.25),
    "glowstone_dust": ("witch", 2.58, 1.57),
    "redstone": ("witch", 2.58, 1.57),
    "cod": ("guardian", 2.45, 0.992),
    "raw_fish": ("guardian", 2.45, 0.992),
    "shulker_shell": ("shulker", 2, 1.4545),
    "totem_of_undying": ("evoker", 1, 1),
    "emerald": ("vindicator", 2, 0.5),
    "nautilus_shell": ("drowned", 6.666, 6.666),
    "phantom_membrane": ("phantom", 2, 0.5),
    "trident": ("drowned", 8.673, 5.6465),
    "breeze_rod": ("breeze", 2, 0.5),
    "rotten_flesh": ("zombie", 1, 0.4),
    "gold_nugget": ("zombified_piglin", 1.667, 0.407),
    "gold_ingot": ("zombified_piglin", 15, 3.667),
}

# Gold from zombie pigmen used the combined ingots+nuggets rate in the
# original app. Keep that on gold_ingot; nuggets still expand to ingots.

STACK_1_EXACT = {
    "saddle", "shears", "flint_and_steel", "fishing_rod", "bow", "crossbow",
    "trident", "mace", "shield", "elytra", "totem_of_undying", "spyglass",
    "brush", "bundle", "goat_horn", "carrot_on_a_stick",
    "warped_fungus_on_a_stick", "milk_bucket", "lava_bucket", "water_bucket",
    "cake", "armor_stand",
}
STACK_1_SUFFIX = (
    "_sword", "_pickaxe", "_axe", "_shovel", "_hoe", "_helmet", "_chestplate",
    "_leggings", "_boots", "_horse_armor", "_boat", "_minecart", "_bucket",
    "_bed", "_shulker_box", "_stew", "_soup",
)
STACK_16_EXACT = {
    "ender_pearl", "egg", "snowball", "armor_stand", "written_book",
    "honey_bottle", "sign",
}
STACK_16_SUFFIX = ("_sign", "_hanging_sign", "_banner")

TOOL_SUFFIX = (
    "_sword", "_pickaxe", "_axe", "_shovel", "_hoe", "_helmet", "_chestplate",
    "_leggings", "_boots", "_horse_armor",
)

# These are gathered in the world (or are the base unit of a material).
# Never assign a recipe even if the jar has a stonecutter / unpack path.
FORCE_TERMINAL = {
    "cobblestone", "cobbled_deepslate", "dirt", "gravel",
    "sand", "red_sand", "netherrack", "end_stone", "obsidian", "soul_sand",
    "soul_soil", "clay", "ice", "andesite", "diorite",
    "granite", "tuff", "calcite", "dripstone_block",
    "blackstone", "basalt", "nether_wart", "warped_nylium", "crimson_nylium",
    "sculk", "raw_iron", "raw_gold", "raw_copper", "ancient_debris",
}

CUSTOM_SETS = {
    "full_diamond_armor": {
        "name": "Full Diamond Armor",
        "recipe": {
            "diamond_helmet": 1,
            "diamond_chestplate": 1,
            "diamond_leggings": 1,
            "diamond_boots": 1,
        },
    },
    "full_iron_armor": {
        "name": "Full Iron Armor",
        "recipe": {
            "iron_helmet": 1,
            "iron_chestplate": 1,
            "iron_leggings": 1,
            "iron_boots": 1,
        },
    },
    "full_golden_armor": {
        "name": "Full Golden Armor",
        "recipe": {
            "golden_helmet": 1,
            "golden_chestplate": 1,
            "golden_leggings": 1,
            "golden_boots": 1,
        },
    },
    "full_netherite_armor": {
        "name": "Full Netherite Armor",
        "recipe": {
            "netherite_helmet": 1,
            "netherite_chestplate": 1,
            "netherite_leggings": 1,
            "netherite_boots": 1,
        },
    },
    "full_leather_armor": {
        "name": "Full Leather Armor",
        "recipe": {
            "leather_helmet": 1,
            "leather_chestplate": 1,
            "leather_leggings": 1,
            "leather_boots": 1,
        },
    },
    "enchanting_room": {
        "name": "Enchanting Room",
        "recipe": {"bookshelf": 15, "enchanting_table": 1},
    },
    "nether_portal": {
        "name": "Nether Portal",
        "recipe": {"obsidian": 14, "flint_and_steel": 1},
    },
    "conduit_power_frame": {
        "name": "Max Conduit Frame",
        "recipe": {"prismarine": 42, "conduit": 1},
    },
}

# Vanilla brewing graph used when the jar has no brewing recipes (pre-1.21-ish).
# Each entry: output_potion_id -> (input_potion_id, reagent, bottle="potion")
# Potion ids here are the effect id only (water, awkward, regeneration, long_*, strong_*).
CLASSIC_BREWS = [
    ("awkward", "water", "nether_wart"),
    ("regeneration", "awkward", "ghast_tear"),
    ("swiftness", "awkward", "sugar"),
    ("fire_resistance", "awkward", "magma_cream"),
    ("poison", "awkward", "spider_eye"),
    ("healing", "awkward", "glistering_melon_slice"),
    ("night_vision", "awkward", "golden_carrot"),
    ("weakness", "water", "fermented_spider_eye"),
    ("strength", "awkward", "blaze_powder"),
    ("leaping", "awkward", "rabbit_foot"),
    ("water_breathing", "awkward", "pufferfish"),
    ("turtle_master", "awkward", "turtle_helmet"),
    ("slow_falling", "awkward", "phantom_membrane"),
    ("invisibility", "night_vision", "fermented_spider_eye"),
    ("invisibility", "long_night_vision", "fermented_spider_eye"),
    ("slowness", "swiftness", "fermented_spider_eye"),
    ("slowness", "long_swiftness", "fermented_spider_eye"),
    ("slowness", "leaping", "fermented_spider_eye"),
    ("harming", "healing", "fermented_spider_eye"),
    ("harming", "poison", "fermented_spider_eye"),
    ("harming", "strong_healing", "fermented_spider_eye"),
    ("harming", "strong_poison", "fermented_spider_eye"),
    ("long_regeneration", "regeneration", "redstone"),
    ("long_swiftness", "swiftness", "redstone"),
    ("long_fire_resistance", "fire_resistance", "redstone"),
    ("long_poison", "poison", "redstone"),
    ("long_night_vision", "night_vision", "redstone"),
    ("long_weakness", "weakness", "redstone"),
    ("long_strength", "strength", "redstone"),
    ("long_leaping", "leaping", "redstone"),
    ("long_water_breathing", "water_breathing", "redstone"),
    ("long_turtle_master", "turtle_master", "redstone"),
    ("long_slow_falling", "slow_falling", "redstone"),
    ("long_invisibility", "invisibility", "redstone"),
    ("long_slowness", "slowness", "redstone"),
    ("strong_regeneration", "regeneration", "glowstone_dust"),
    ("strong_swiftness", "swiftness", "glowstone_dust"),
    ("strong_poison", "poison", "glowstone_dust"),
    ("strong_healing", "healing", "glowstone_dust"),
    ("strong_strength", "strength", "glowstone_dust"),
    ("strong_leaping", "leaping", "glowstone_dust"),
    ("strong_turtle_master", "turtle_master", "glowstone_dust"),
    ("strong_harming", "harming", "glowstone_dust"),
    ("strong_slowness", "slowness", "glowstone_dust"),
]

# Healing used glistering_melon in older ids.
MELON_ALIASES = ("glistering_melon_slice", "glistering_melon", "speckled_melon")
TURTLE_ALIASES = ("turtle_helmet", "turtle_shell", "scute")


def log(msg: str) -> None:
    print(msg, flush=True)


def request_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def request_json(url: str):
    return json.loads(request_bytes(url).decode("utf-8"))


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(cache_dir: Path) -> dict:
    path = cache_dir / "version_manifest_v2.json"
    try:
        data = request_json(MANIFEST_URL)
        path.write_text(json.dumps(data))
        return data
    except Exception as exc:
        if path.exists():
            log(f"Warning: using cached manifest ({exc})")
            return json.loads(path.read_text())
        raise


def download_client_jar(version: str, manifest: dict, cache_dir: Path) -> Path:
    info = next((v for v in manifest["versions"] if v["id"] == version), None)
    if not info:
        raise SystemExit(f"Version {version} not found in Mojang manifest")
    meta_path = cache_dir / f"{version}.json"
    if not meta_path.exists():
        meta_path.write_bytes(request_bytes(info["url"]))
    meta = json.loads(meta_path.read_text())
    client = meta["downloads"]["client"]
    jar_path = cache_dir / f"{version}-client.jar"
    if jar_path.exists() and sha1_file(jar_path) == client["sha1"]:
        return jar_path
    log(f"  downloading client jar {version} ({client['size'] // (1024*1024)} MB)")
    jar_path.write_bytes(request_bytes(client["url"]))
    digest = sha1_file(jar_path)
    if digest != client["sha1"]:
        jar_path.unlink(missing_ok=True)
        raise SystemExit(f"SHA1 mismatch for {version}: {digest} != {client['sha1']}")
    return jar_path


def strip_ns(s: str) -> str:
    if not s:
        return s
    if s.startswith("#"):
        body = s[1:]
        return body.split(":", 1)[1] if ":" in body else body
    return s.split(":", 1)[1] if ":" in s else s


def is_tag(s: str) -> bool:
    return isinstance(s, str) and s.startswith("#")


def tag_key(s: str) -> str:
    return strip_ns(s)


def pick_preferred(options: list[str], tags: dict[str, list[str]] | None = None) -> str | None:
    flat: list[str] = []
    for opt in options:
        if not opt:
            continue
        if is_tag(opt):
            resolved = resolve_tag(opt, tags or {})
            if resolved:
                flat.append(resolved)
        else:
            flat.append(strip_ns(opt) if not opt.startswith("#") else opt)
    if not flat:
        return None
    decorated = ("chiseled_", "smooth_", "cracked_", "cut_", "polished_", "mossy_", "stripped_")
    plain = [x for x in flat if not x.startswith(decorated)]
    pool = plain or flat
    for pref in PREFERRED_TAG_ITEMS:
        if pref in pool:
            return pref
    for pref in PREFERRED_TAG_ITEMS:
        matches = [x for x in pool if x.startswith(pref.split("_")[0] + "_") or x == pref]
        if matches:
            return matches[0]
    return pool[0]


def resolve_tag(tag: str, tags: dict[str, list[str]], seen: set[str] | None = None) -> str | None:
    key = tag_key(tag)
    seen = seen or set()
    if key in seen:
        return None
    seen.add(key)
    values = tags.get(key) or []
    items, nested = [], []
    for v in values:
        if is_tag(v) or (isinstance(v, str) and v.startswith("#")):
            nested.append(v)
        else:
            items.append(strip_ns(v))
    chosen = pick_preferred(items)
    if chosen:
        return chosen
    for n in nested:
        chosen = resolve_tag(n, tags, seen)
        if chosen:
            return chosen
    return None


def load_tags(zf: ZipFile) -> dict[str, list[str]]:
    tags: dict[str, list[str]] = {}
    for name in zf.namelist():
        if not name.endswith(".json"):
            continue
        if not (
            name.startswith("data/minecraft/tags/item/")
            or name.startswith("data/minecraft/tags/items/")
            or name.startswith("data/minecraft/tags/block/")
            or name.startswith("data/minecraft/tags/blocks/")
        ):
            continue
        key = Path(name).stem
        try:
            data = json.loads(zf.read(name))
        except Exception:
            continue
        values = []
        for v in data.get("values", []):
            if isinstance(v, str):
                values.append(v)
            elif isinstance(v, dict) and "id" in v:
                values.append(v["id"])
        # Don't overwrite item tags with block tags of the same name unless empty.
        if key not in tags or name.startswith("data/minecraft/tags/item"):
            tags[key] = values
    return tags


def parse_item_ref(ref, tags: dict[str, list[str]]) -> str | None:
    if ref is None:
        return None
    if isinstance(ref, str):
        if ref.startswith("#"):
            return resolve_tag(ref, tags) or None
        return strip_ns(ref)
    if isinstance(ref, list):
        opts = [parse_item_ref(x, tags) for x in ref]
        return pick_preferred([o for o in opts if o], tags)
    if isinstance(ref, dict):
        if "item" in ref:
            return strip_ns(ref["item"])
        if "id" in ref:
            return strip_ns(ref["id"])
        if "tag" in ref:
            return resolve_tag(ref["tag"], tags)
        if "ingredient" in ref:
            return parse_item_ref(ref["ingredient"], tags)
    return None


def parse_result(obj) -> tuple[str | None, int]:
    if obj is None:
        return None, 1
    if isinstance(obj, str):
        return strip_ns(obj), 1
    if isinstance(obj, dict):
        ident = obj.get("id") or obj.get("item") or obj.get("result")
        count = obj.get("count", 1) or 1
        if ident:
            return strip_ns(ident), int(count)
    return None, 1


def recipe_type_name(t: str) -> str:
    return strip_ns(t or "")


def is_ore_like(item: str) -> bool:
    if item.endswith("_ore") or item.startswith("raw_"):
        return True
    if item in {"ancient_debris"}:
        return False
    return False


def is_tool_or_armor(item: str) -> bool:
    return item.endswith(TOOL_SUFFIX) or "chainmail_" in item


def is_storage_unpack(ingredients: dict[str, float], result: str, out_count: int) -> bool:
    """Skip recipes that unpack a storage block into its base unit.

    1 log -> 4 planks is a real crafting recipe and must be kept. 1 iron
    block -> 9 ingots is just the reverse of packing, so the ingot should
    stay a base material.
    """
    if len(ingredients) != 1:
        return False
    in_name, in_count = next(iter(ingredients.items()))
    if in_count != 1:
        return False
    if result.endswith("_nugget"):
        return False
    if out_count == 9:
        return True
    if out_count >= 4 and in_name.endswith("_block") and not result.endswith("_block"):
        return True
    return False


def add_ing(dest: dict[str, float], item: str | None, amount: float) -> None:
    if not item or amount == 0:
        return
    dest[item] = dest.get(item, 0) + amount


def parse_shaped(obj, tags) -> tuple[dict[str, float], tuple[str | None, int]] | None:
    keys = {}
    for k, v in (obj.get("key") or {}).items():
        keys[k] = parse_item_ref(v, tags)
    ings: dict[str, float] = {}
    for row in obj.get("pattern") or []:
        for ch in row:
            if ch == " ":
                continue
            add_ing(ings, keys.get(ch), 1)
    result, count = parse_result(obj.get("result"))
    if not result or not ings:
        return None
    return ings, (result, count)


def parse_shapeless(obj, tags) -> tuple[dict[str, float], tuple[str | None, int]] | None:
    ings: dict[str, float] = {}
    ingredients = obj.get("ingredients") or obj.get("ingredient") or []
    if isinstance(ingredients, dict) or isinstance(ingredients, str):
        ingredients = [ingredients]
    for ref in ingredients:
        add_ing(ings, parse_item_ref(ref, tags), 1)
    result, count = parse_result(obj.get("result"))
    if not result or not ings:
        return None
    return ings, (result, count)


def parse_cooking(obj, tags, include_fuel=True):
    ings: dict[str, float] = {}
    add_ing(ings, parse_item_ref(obj.get("ingredient"), tags), 1)
    result, count = parse_result(obj.get("result"))
    if not result or not ings:
        return None
    if include_fuel:
        ings["fuel"] = ings.get("fuel", 0) + 1
    return ings, (result, count)


def parse_stonecutting(obj, tags):
    ings: dict[str, float] = {}
    add_ing(ings, parse_item_ref(obj.get("ingredient"), tags), 1)
    result, count = parse_result(obj.get("result"))
    if not result or not ings:
        return None
    return ings, (result, count)


def parse_smithing(obj, tags):
    ings: dict[str, float] = {}
    for field in ("template", "base", "addition"):
        add_ing(ings, parse_item_ref(obj.get(field), tags), 1)
    result, count = parse_result(obj.get("result"))
    if not result or not ings:
        return None
    return ings, (result, count)


def recipe_kind_priority(kind: str) -> int:
    order = {
        "crafting_shaped": 0,
        "crafting_shapeless": 1,
        "smithing_transform": 2,
        "smithing": 2,
        "smelting": 3,
        "stonecutting": 4,
    }
    return order.get(kind, 9)


def should_skip_cooking(ings: dict[str, float], result: str) -> bool:
    items = [k for k in ings if k != "fuel"]
    if not items:
        return True
    ing = items[0]
    if is_ore_like(ing) and result in MINERAL_RESULTS:
        return True
    if is_ore_like(ing) and result.endswith("_ingot"):
        return True
    if is_tool_or_armor(ing):
        return True
    # Charcoal is handled specially later (no fuel, to avoid loops).
    return False


def collect_raw_recipes(zf: ZipFile, tags: dict) -> list[dict]:
    raw = []
    for name in zf.namelist():
        if not name.endswith(".json"):
            continue
        if not (
            name.startswith("data/minecraft/recipe/")
            or name.startswith("data/minecraft/recipes/")
        ):
            continue
        if "/brewing/" in name:
            continue
        try:
            obj = json.loads(zf.read(name))
        except Exception:
            continue
        kind = recipe_type_name(obj.get("type", ""))
        category = obj.get("category") or obj.get("group") or ""
        parsed = None
        if kind == "crafting_shaped":
            parsed = parse_shaped(obj, tags)
        elif kind == "crafting_shapeless":
            parsed = parse_shapeless(obj, tags)
        elif kind == "smelting":
            parsed = parse_cooking(obj, tags, include_fuel=True)
            if parsed and should_skip_cooking(parsed[0], parsed[1][0]):
                parsed = None
        elif kind in {"stonecutting", "smithing_transform", "smithing"}:
            if kind == "stonecutting":
                parsed = parse_stonecutting(obj, tags)
            else:
                parsed = parse_smithing(obj, tags)
        else:
            continue
        if not parsed:
            continue
        ings, (result, count) = parsed
        if not result or result in ings:
            continue  # duplication / self-referential
        if is_storage_unpack(ings, result, count):
            continue
        # 9 nuggets -> 1 ingot would cycle with 1 ingot -> 9 nuggets.
        if (
            len(ings) == 1
            and count == 1
            and result.endswith("_ingot")
            and next(iter(ings)).endswith("_nugget")
            and list(ings.values())[0] >= 4
        ):
            continue
        # Charcoal: drop the fuel cost so choosing charcoal as fuel cannot loop.
        if result == "charcoal" and "fuel" in ings:
            ings = dict(ings)
            ings.pop("fuel", None)
        # Normalize amounts per 1 output.
        per = {k: v / count for k, v in ings.items()}
        raw.append({
            "result": result,
            "ingredients": per,
            "kind": kind,
            "category": category,
            "source": name,
        })
    return raw


def _sort_options(options: list[dict]) -> list[dict]:
    return sorted(
        options,
        key=lambda r: (
            recipe_kind_priority(r["kind"]),
            len(r["ingredients"]),
            sum(r["ingredients"].values()),
            r["source"],
        ),
    )


def pick_canonical(raw: list[dict]) -> dict[str, dict]:
    by_result: dict[str, list[dict]] = defaultdict(list)
    for r in raw:
        by_result[r["result"]].append(r)
    for result in by_result:
        by_result[result] = _sort_options(by_result[result])

    chosen: dict[str, dict] = {}
    remaining = set(by_result)
    changed = True
    while changed:
        changed = False
        for result in list(remaining):
            for opt in by_result[result]:
                ings = [i for i in opt["ingredients"] if i != "fuel"]
                if all(ing not in remaining for ing in ings):
                    chosen[result] = opt
                    remaining.remove(result)
                    changed = True
                    break

    # Leftovers only have cyclic recipes. Prefer keeping "unpack" recipes
    # (nuggets from ingots, bottles from blocks) and drop the reverse.
    for result in list(remaining):
        for opt in by_result[result]:
            ings = [i for i in opt["ingredients"] if i != "fuel"]
            # Allow ingredients that will be treated as terminal.
            if result not in ings:
                chosen[result] = opt
                remaining.remove(result)
                # If an ingredient is also leftover and this is a 1->many unpack,
                # do not also keep the reverse pack recipe.
                break

    # Drop any recipe that still immediately cycles with another chosen recipe.
    def has_direct_cycle(a, b):
        ra, rb = chosen.get(a), chosen.get(b)
        return bool(ra and rb and b in ra["ingredients"] and a in rb["ingredients"])

    for a in list(chosen):
        for b in list(chosen.get(a, {}).get("ingredients", {})):
            if a == b:
                chosen.pop(a, None)
                break
            if has_direct_cycle(a, b):
                rec_a, rec_b = chosen[a], chosen[b]
                # Keep the smaller unit (more output per 1 ingredient) if any.
                a_out = 1 / (rec_a["ingredients"][b] or 1)
                b_out = 1 / (rec_b["ingredients"][a] or 1)
                drop = a if a_out <= b_out else b
                # Prefer dropping the pack (many -> 1), i.e. the result that is "bigger"
                if rec_a["ingredients"][b] >= 4 and rec_b["ingredients"][a] <= 1:
                    drop = a
                elif rec_b["ingredients"][a] >= 4 and rec_a["ingredients"][b] <= 1:
                    drop = b
                chosen.pop(drop, None)
    return chosen


def potion_item_id(bottle: str, potion: str) -> str:
    return f"{strip_ns(bottle)}/{strip_ns(potion)}"


def parse_potion_contents(obj) -> str | None:
    if not isinstance(obj, dict):
        return None
    pc = obj.get("potion_contents") or obj.get("components", {}).get("minecraft:potion_contents") or {}
    if isinstance(pc, str):
        return strip_ns(pc)
    if not isinstance(pc, dict):
        return None
    val = pc.get("potion") or pc.get("potions")
    if isinstance(val, list) and val:
        val = val[0]
    if isinstance(val, dict):
        val = val.get("potion") or val.get("id")
    return strip_ns(val) if val else None


def collect_brewing(zf: ZipFile) -> list[dict]:
    recipes = []
    found = False
    for name in zf.namelist():
        if not (name.startswith("data/minecraft/recipe/brewing/") and name.endswith(".json")):
            continue
        found = True
        try:
            obj = json.loads(zf.read(name))
        except Exception:
            continue
        if recipe_type_name(obj.get("type", "")) != "brewing":
            continue
        inp = obj.get("input") or {}
        out = obj.get("output") or {}
        reagent = parse_item_ref(obj.get("reagent"), {})
        in_bottle = parse_item_ref(inp, {}) or strip_ns(inp.get("item", "") if isinstance(inp, dict) else "")
        out_bottle = parse_item_ref(out, {}) or strip_ns(
            (out.get("id") or out.get("item") or "") if isinstance(out, dict) else ""
        )
        in_potion = parse_potion_contents(inp)
        out_potion = parse_potion_contents(out)
        if not (reagent and in_bottle and out_bottle and in_potion and out_potion):
            continue
        result = potion_item_id(out_bottle, out_potion)
        source = potion_item_id(in_bottle, in_potion)
        # One brew stand operation processes 3 bottles and burns 1 blaze powder
        # (which itself fuels 20 operations) — same accounting as the original app.
        recipes.append({
            "result": result,
            "ingredients": {
                source: 1,
                reagent: 1 / 3,
                "blaze_powder": 1 / 60,
            },
            "kind": "brewing",
            "category": "potions",
            "source": name,
        })
    return recipes, found


def classic_brewing(available: set[str]) -> list[dict]:
    # Resolve melon / turtle item aliases against what exists in this version.
    def have(item: str) -> str | None:
        if item == "glistering_melon_slice":
            for a in MELON_ALIASES:
                if a in available:
                    return a
        if item == "turtle_helmet":
            for a in TURTLE_ALIASES:
                if a in available:
                    return a
        if item in available or item in {"nether_wart", "redstone", "glowstone_dust",
                                         "gunpowder", "dragon_breath", "blaze_powder",
                                         "fermented_spider_eye"}:
            return item if (item in available or item in {
                "nether_wart", "redstone", "glowstone_dust", "gunpowder",
                "dragon_breath", "blaze_powder", "fermented_spider_eye",
            }) else None
        return item if item in available else None

    recipes = []
    seen = set()

    def add(result_potion, source_potion, reagent, bottle="potion"):
        actual = have(reagent)
        if not actual:
            return
        result = potion_item_id(bottle, result_potion)
        source = potion_item_id(bottle, source_potion)
        key = (result, source, actual)
        if key in seen:
            return
        seen.add(key)
        recipes.append({
            "result": result,
            "ingredients": {source: 1, actual: 1 / 3, "blaze_powder": 1 / 60},
            "kind": "brewing",
            "category": "potions",
            "source": "classic_brewing",
        })

    for out, src, reagent in CLASSIC_BREWS:
        add(out, src, reagent, "potion")

    # Splash and lingering conversions + the same effect tree on those bottles
    # once a splash/lingering water bottle exists.
    all_potions = ["water"] + [out for out, _, _ in CLASSIC_BREWS]
    for potion in all_potions:
        add(potion, potion, "gunpowder", "potion")  # placeholder, fix below

    # Redo splash/lingering properly: gunpowder converts potion X -> splash X,
    # dragon breath converts splash X -> lingering X.
    recipes = [r for r in recipes if r["source"] == "classic_brewing" and "gunpowder" not in r["ingredients"]]
    seen = { (r["result"], list(r["ingredients"])[0], "x") for r in recipes }

    def add_conv(result, source, reagent):
        actual = have(reagent)
        if not actual:
            return
        if result in {r["result"] for r in recipes if actual in r["ingredients"] and source in r["ingredients"]}:
            return
        recipes.append({
            "result": result,
            "ingredients": {source: 1, actual: 1 / 3, "blaze_powder": 1 / 60},
            "kind": "brewing",
            "category": "potions",
            "source": "classic_brewing",
        })

    for out, src, reagent in CLASSIC_BREWS:
        add(out, src, reagent, "potion")
        # Also allow brewing the effect directly in splash/lingering bottles.
        add(out, src, reagent, "splash_potion")
        add(out, src, reagent, "lingering_potion")

    for potion in all_potions:
        add_conv(potion_item_id("splash_potion", potion), potion_item_id("potion", potion), "gunpowder")
        add_conv(potion_item_id("lingering_potion", potion), potion_item_id("splash_potion", potion), "dragon_breath")

    return recipes


def display_name(item: str, lang: dict) -> str:
    if item == "fuel":
        return "Fuel"
    if "/" in item:
        bottle, potion = item.split("/", 1)
        key = f"item.minecraft.{bottle}.effect.{potion}"
        if key in lang:
            return lang[key]
        nice_potion = potion.replace("strong_", "").replace("long_", "").replace("_", " ")
        prefix = {"potion": "Potion of", "splash_potion": "Splash Potion of",
                  "lingering_potion": "Lingering Potion of"}.get(bottle, bottle.replace("_", " ").title() + " of")
        extra = ""
        if potion.startswith("strong_"):
            extra = " II"
        elif potion.startswith("long_"):
            extra = " (long)"
        if potion in {"water", "awkward", "mundane", "thick"}:
            base = {"potion": "Potion", "splash_potion": "Splash Potion",
                    "lingering_potion": "Lingering Potion"}.get(bottle, "Potion")
            return f"{base} of {potion.replace('_', ' ').title()}" if potion != "water" else (
                {"potion": "Water Bottle", "splash_potion": "Splash Water Bottle",
                 "lingering_potion": "Lingering Water Bottle"}.get(bottle, "Water Bottle")
            )
        return f"{prefix} {nice_potion.title()}{extra}"
    for key in (f"item.minecraft.{item}", f"block.minecraft.{item}"):
        if key in lang:
            return lang[key]
    return item.replace("_", " ").title()


def categorize(item: str, recipe_cat: str) -> str:
    if item.startswith(("potion/", "splash_potion/", "lingering_potion/")):
        return "potions"
    if item in CUSTOM_SETS:
        return "sets"
    for color in COLORS:
        if item == color or item.startswith(color + "_") or f"_{color}_" in item:
            if any(k in item for k in COLORED_KINDS):
                return "colored"
    cat = strip_ns(recipe_cat) if recipe_cat else ""
    if cat in {"building", "redstone", "equipment", "food"}:
        return cat
    if cat in {"misc", "blocks", "tools"}:
        return "other" if cat == "misc" else cat
    return "other"


def stack_size(item: str) -> int:
    base = item.split("/", 1)[0]
    if item.startswith(("potion/", "splash_potion/", "lingering_potion/")):
        return 1
    if base in STACK_1_EXACT or item in STACK_1_EXACT:
        return 1
    if item.endswith(STACK_1_SUFFIX) or base.endswith(STACK_1_SUFFIX):
        return 1
    if base in STACK_16_EXACT or item in STACK_16_EXACT:
        return 16
    if item.endswith(STACK_16_SUFFIX):
        return 16
    return 64


def load_lang(zf: ZipFile) -> dict:
    for path in ("assets/minecraft/lang/en_us.json", "assets/minecraft/lang/en_us.lang"):
        if path in zf.namelist():
            raw = zf.read(path)
            if path.endswith(".json"):
                return json.loads(raw.decode("utf-8"))
            lang = {}
            for line in raw.decode("utf-8", "replace").splitlines():
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                lang[k] = v
            return lang
    return {}


def follow_model_texture(zf: ZipFile, model: str, names: set[str], depth=0) -> str | None:
    if depth > 8 or not model:
        return None
    model = strip_ns(model)
    path = f"assets/minecraft/models/{model}.json"
    if path not in names:
        # try item/ or block/ already included
        return None
    try:
        data = json.loads(zf.read(path))
    except Exception:
        return None
    textures = data.get("textures") or {}
    for key in ("layer0", "all", "side", "end", "top", "front", "particle", "texture"):
        if key in textures:
            tex = textures[key]
            if tex.startswith("#"):
                continue
            png = "assets/minecraft/textures/" + strip_ns(tex) + ".png"
            if png in names:
                return png
    for tex in textures.values():
        if isinstance(tex, str) and not tex.startswith("#"):
            png = "assets/minecraft/textures/" + strip_ns(tex) + ".png"
            if png in names:
                return png
    parent = data.get("parent")
    if parent:
        return follow_model_texture(zf, parent, names, depth + 1)
    return None


def item_model_ref(data) -> str | None:
    if not isinstance(data, dict):
        return None
    model = data.get("model")
    if isinstance(model, str):
        return model
    if isinstance(model, dict):
        if isinstance(model.get("model"), str):
            return model["model"]
        # alternating / condition models: try first leaf
        for key in ("on_false", "on_true", "fallback", "default"):
            if key in model:
                found = item_model_ref({"model": model[key]})
                if found:
                    return found
        entries = model.get("entries") or model.get("cases") or []
        if entries and isinstance(entries, list):
            for e in entries:
                found = item_model_ref(e if isinstance(e, dict) else {"model": e})
                if found:
                    return found
    return None


def find_texture(zf: ZipFile, item: str, names: set[str]) -> str | None:
    base = item.split("/", 1)[0]
    direct = [
        f"assets/minecraft/textures/item/{base}.png",
        f"assets/minecraft/textures/items/{base}.png",
        f"assets/minecraft/textures/block/{base}.png",
        f"assets/minecraft/textures/blocks/{base}.png",
        f"assets/minecraft/textures/item/{item}.png",
        f"assets/minecraft/textures/block/{item}.png",
    ]
    for p in direct:
        if p in names:
            return p
    # 1.21+ items definition
    for p in (f"assets/minecraft/items/{base}.json",):
        if p in names:
            try:
                data = json.loads(zf.read(p))
            except Exception:
                data = {}
            model = item_model_ref(data)
            if model:
                tex = follow_model_texture(zf, model, names)
                if tex:
                    return tex
    for p in (f"assets/minecraft/models/item/{base}.json", f"assets/minecraft/models/block/{base}.json"):
        if p in names:
            tex = follow_model_texture(zf, p[len("assets/minecraft/models/"):-5], names)
            if tex:
                return tex
    # common fallbacks
    for suffix in ("_side", "_top", "_front", "_planks", "s"):
        for folder in ("item", "block", "items", "blocks"):
            p = f"assets/minecraft/textures/{folder}/{base}{suffix}.png"
            if p in names:
                return p
    return None


def potion_color(potion: str) -> tuple[int, int, int]:
    # Approximate vanilla colors; overlay is multiplied over the bottle.
    table = {
        "water": (56, 95, 168),
        "awkward": (56, 95, 168),
        "mundane": (56, 95, 168),
        "thick": (56, 95, 168),
        "regeneration": (205, 92, 171),
        "long_regeneration": (205, 92, 171),
        "strong_regeneration": (205, 92, 171),
        "swiftness": (51, 235, 255),
        "long_swiftness": (51, 235, 255),
        "strong_swiftness": (51, 235, 255),
        "fire_resistance": (255, 154, 58),
        "long_fire_resistance": (255, 154, 58),
        "poison": (135, 163, 59),
        "long_poison": (135, 163, 59),
        "strong_poison": (135, 163, 59),
        "healing": (248, 36, 35),
        "strong_healing": (248, 36, 35),
        "night_vision": (31, 31, 163),
        "long_night_vision": (31, 31, 163),
        "weakness": (72, 77, 72),
        "long_weakness": (72, 77, 72),
        "strength": (147, 36, 35),
        "long_strength": (147, 36, 35),
        "strong_strength": (147, 36, 35),
        "slowness": (90, 108, 129),
        "long_slowness": (90, 108, 129),
        "strong_slowness": (90, 108, 129),
        "leaping": (34, 255, 76),
        "long_leaping": (34, 255, 76),
        "strong_leaping": (34, 255, 76),
        "harming": (67, 10, 9),
        "strong_harming": (67, 10, 9),
        "water_breathing": (46, 82, 153),
        "long_water_breathing": (46, 82, 153),
        "invisibility": (127, 131, 146),
        "long_invisibility": (127, 131, 146),
        "slow_falling": (243, 247, 245),
        "long_slow_falling": (243, 247, 245),
        "turtle_master": (81, 77, 97),
        "long_turtle_master": (81, 77, 97),
        "strong_turtle_master": (81, 77, 97),
        "wind_charged": (180, 200, 220),
        "weaving": (120, 160, 120),
        "oozing": (100, 180, 80),
        "infested": (140, 140, 100),
    }
    if potion in table:
        return table[potion]
    key = potion.replace("long_", "").replace("strong_", "")
    return table.get(key, (150, 80, 200))


def _save_icon(im: "Image.Image", dest: Path) -> None:
    if im.size != (64, 64):
        im = im.resize((64, 64), Image.NEAREST)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, optimize=True)


def extract_icon(zf: ZipFile, item: str, names: set[str], dest: Path, tex_cache=None, skip_existing=True) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if skip_existing and dest.exists():
        return True
    # Prefer an isometric inventory render for block models.
    if (
        render3d is not None
        and Image is not None
        and "/" not in item
        and item not in {"fuel"}
    ):
        try:
            rendered = render3d.render_item(zf, names, item, tex_cache)
        except Exception:
            rendered = None
        if rendered is not None:
            _save_icon(rendered, dest)
            return True
    if item.startswith(("potion/", "splash_potion/", "lingering_potion/")) and Image is not None:
        bottle, potion = item.split("/", 1)
        bottle_tex = {
            "potion": "assets/minecraft/textures/item/potion.png",
            "splash_potion": "assets/minecraft/textures/item/splash_potion.png",
            "lingering_potion": "assets/minecraft/textures/item/lingering_potion.png",
        }.get(bottle)
        overlay_tex = "assets/minecraft/textures/item/potion_overlay.png"
        # older paths
        alt_bottle = bottle_tex.replace("/item/", "/items/") if bottle_tex else None
        alt_overlay = "assets/minecraft/textures/items/potion_overlay.png"
        if bottle_tex and bottle_tex not in names and alt_bottle in names:
            bottle_tex = alt_bottle
        if overlay_tex not in names and alt_overlay in names:
            overlay_tex = alt_overlay
        if bottle_tex in names and overlay_tex in names:
            base = Image.open(io.BytesIO(zf.read(bottle_tex))).convert("RGBA")
            overlay = Image.open(io.BytesIO(zf.read(overlay_tex))).convert("RGBA")
            r, g, b = potion_color(potion)
            tinted = Image.new("RGBA", overlay.size)
            px = overlay.load()
            tp = tinted.load()
            for y in range(overlay.height):
                for x in range(overlay.width):
                    pr, pg, pb, pa = px[x, y]
                    if pa == 0:
                        continue
                    tp[x, y] = (
                        int(pr * r / 255),
                        int(pg * g / 255),
                        int(pb * b / 255),
                        pa,
                    )
            base.alpha_composite(tinted)
            _save_icon(base, dest)
            return True
    tex = find_texture(zf, item, names)
    if not tex:
        return False
    raw = Image.open(io.BytesIO(zf.read(tex))).convert("RGBA")
    # Animated textures: first frame only.
    if raw.height > raw.width:
        raw = raw.crop((0, 0, raw.width, raw.width))
    _save_icon(raw, dest)
    return True



MOB_ICON_FILES = [
    "blaze.png", "chicken.png", "cow.png", "creeper.png", "drowned.png",
    "enderman.png", "evoker.png", "ghast.png", "guardian.png", "iron_golem.png",
    "phantom.png", "pig.png", "rabbit.png", "sheep.png", "shulker.png",
    "skeleton.png", "spider.png", "squid.png", "tiny_slime.png", "vindicator.png",
    "witch.png", "wither_skeleton.png", "zombie_pigmen.png",
]


def copy_mob_icons(icons_dir: Path) -> None:
    gfx = ROOT / "gfx"
    if not gfx.exists():
        return
    for name in MOB_ICON_FILES:
        src = gfx / name
        dest = icons_dir / name
        if src.exists() and not dest.exists():
            dest.write_bytes(src.read_bytes())
    src = gfx / "zombie_pigmen.png"
    dest = icons_dir / "zombified_piglin.png"
    if src.exists() and not dest.exists():
        dest.write_bytes(src.read_bytes())
    copy_custom_set_icons(icons_dir)



def write_armor_icon_preview(icons_dir: Path) -> None:
    if Image is None:
        return
    from PIL import ImageDraw
    names = [
        "full_diamond_armor", "full_netherite_armor", "full_iron_armor",
        "full_golden_armor", "full_leather_armor",
        "enchanting_room", "nether_portal", "conduit_power_frame",
        "netherite_helmet", "netherite_chestplate", "netherite_leggings", "netherite_boots",
        "netherite_sword", "netherite_pickaxe", "netherite_axe", "netherite_shovel",
        "netherite_hoe", "netherite_ingot", "netherite_block",
        "diamond_helmet", "diamond_chestplate", "diamond_leggings", "diamond_boots",
        "iron_helmet", "iron_chestplate", "iron_leggings", "iron_boots",
        "golden_helmet", "golden_chestplate", "golden_leggings", "golden_boots",
        "leather_helmet", "leather_chestplate", "leather_leggings", "leather_boots",
        "chainmail_helmet", "chainmail_chestplate", "chainmail_leggings", "chainmail_boots",
    ]
    cols, cell, label = 8, 80, 22
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell, rows * (cell + label)), (36, 28, 22, 255))
    draw = ImageDraw.Draw(sheet)
    for i, name in enumerate(names):
        path = icons_dir / f"{name}.png"
        x, y = (i % cols) * cell, (i // cols) * (cell + label)
        if path.exists():
            im = Image.open(path).convert("RGBA").resize((64, 64), Image.NEAREST)
            sheet.alpha_composite(im, (x + 8, y + 6))
        draw.text((x + 4, y + cell - 2), name.replace("_", " ")[:16], fill=(240, 220, 160))
    sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)
    dest = Path("/tmp/mccostcalc-armor-preview.png")
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest)
    local = Path(__file__).resolve().parent / "armor_icon_preview.png"
    sheet.save(local)
    log(f"  wrote armor icon preview {dest}")


def write_icon_preview(icons_dir: Path, dest: Path) -> None:
    if Image is None:
        return
    names = [
        "oak_planks", "oak_slab", "oak_stairs",
        "bricks", "brick_slab", "brick_stairs", "brick_wall", "oak_fence",
        "glass", "grass_block", "piston", "chest",
        "furnace", "crafting_table", "acacia_planks", "acacia_slab",
    ]
    cols, cell, label = 8, 80, 20
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell, rows * (cell + label)), (36, 28, 22, 255))
    try:
        from PIL import ImageDraw
        draw = ImageDraw.Draw(sheet)
    except Exception:
        draw = None
    for i, name in enumerate(names):
        path = icons_dir / f"{name}.png"
        x, y = (i % cols) * cell, (i // cols) * (cell + label)
        if path.exists():
            im = Image.open(path).convert("RGBA").resize((64, 64), Image.NEAREST)
            sheet.alpha_composite(im, (x + 8, y + 6))
        if draw:
            draw.text((x + 6, y + cell - 2), name, fill=(240, 220, 160))
    sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest)
    # Also keep a copy next to the generator for easy inspection.
    local = Path(__file__).resolve().parent / "icon_preview.png"
    sheet.save(local)
    log(f"  wrote icon preview {dest}")
    write_armor_icon_preview(icons_dir)

ARMOR_SET_PIECES = {
    "full_diamond_armor": ["diamond_helmet", "diamond_chestplate", "diamond_leggings", "diamond_boots"],
    "full_iron_armor": ["iron_helmet", "iron_chestplate", "iron_leggings", "iron_boots"],
    "full_golden_armor": ["golden_helmet", "golden_chestplate", "golden_leggings", "golden_boots"],
    "full_leather_armor": ["leather_helmet", "leather_chestplate", "leather_leggings", "leather_boots"],
    "full_netherite_armor": ["netherite_helmet", "netherite_chestplate", "netherite_leggings", "netherite_boots"],
}

# Icons to extract even when the item is not in the recipe graph (e.g. chainmail).
EXTRA_ICON_ITEMS = [
    "chainmail_helmet", "chainmail_chestplate", "chainmail_leggings", "chainmail_boots",
]


def compose_armor_set_icons(icons_dir: Path) -> None:
    """Build 2x2 set icons from the four armor-piece sprites (helmet, chest, legs, boots)."""
    if Image is None:
        return
    for set_id, pieces in ARMOR_SET_PIECES.items():
        paths = [icons_dir / f"{p}.png" for p in pieces]
        if not all(path.exists() for path in paths):
            continue
        size = 64
        half = size // 2
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        for i, path in enumerate(paths):
            im = Image.open(path).convert("RGBA").resize((half, half), Image.NEAREST)
            canvas.alpha_composite(im, ((i % 2) * half, (i // 2) * half))
        canvas.save(icons_dir / f"{set_id}.png", optimize=True)


def copy_custom_set_icons(icons_dir: Path) -> None:
    gfx = ROOT / "gfx"
    legacy_gfx = ROOT / "legacy" / "gfx"
    src_dir = gfx if gfx.exists() else legacy_gfx
    # Always compose armor sets from the current piece icons when possible,
    # so Full Netherite Armor cannot fall back to the diamond composite.
    compose_armor_set_icons(icons_dir)
    if not src_dir.exists():
        return
    mapping = {
        "enchanting_room.png": "enchanting_room.png",
        "nether_portal.png": "nether_portal.png",
        "conduit_power_frame.png": "conduit_power_frame.png",
    }
    for src_name, dest_name in mapping.items():
        src = src_dir / src_name
        dest = icons_dir / dest_name
        if src.exists() and not dest.exists():
            dest.write_bytes(src.read_bytes())


def icon_filename(item: str) -> str:
    return item.replace("/", "__") + ".png"


def build_version(version: str, zf: ZipFile, icons_dir: Path) -> dict:
    names = set(zf.namelist())
    tex_cache: dict = {}
    tags = load_tags(zf)
    lang = load_lang(zf)
    raw = collect_raw_recipes(zf, tags)
    brew, has_brew = collect_brewing(zf)
    # Items that exist in this jar (for classic brewing reagent checks).
    available = set()
    for r in raw:
        available.add(r["result"])
        available.update(r["ingredients"])
    # Also textures / item models as a hint that an item exists
    for n in names:
        m = re.match(r"assets/minecraft/(?:items|textures/item|textures/items|textures/block)/([a-z0-9_]+)\.", n)
        if m:
            available.add(m.group(1))

    if has_brew:
        raw.extend(brew)
    else:
        raw.extend(classic_brewing(available))

    # Custom wither / nether star breakdown (the nether star is not crafted).
    if "nether_star" in available or any(r["result"] == "beacon" for r in raw):
        raw.append({
            "result": "nether_star",
            "ingredients": {"wither_skeleton_skull": 3, "soul_sand": 4},
            "kind": "custom",
            "category": "other",
            "source": "custom_wither",
        })
        available.update({"nether_star", "wither_skeleton_skull", "soul_sand"})

    # Official id for soul sand / enchanting table may vary slightly; also
    # older soulsand typo is not in jars.
    for set_id, info in CUSTOM_SETS.items():
        rec = dict(info["recipe"])
        # If a piece is missing (e.g. netherite in 1.13), skip the set.
        if all((k in available) or (k in CUSTOM_SETS) or any(r["result"] == k for r in raw)
               or k in rec for k in rec):
            # Check each ingredient exists as an item/recipe or natural block
            missing = [k for k in rec if k not in available and not any(r["result"] == k for r in raw)]
            # Natural blocks like obsidian, prismarine may only appear as ingredients
            if missing and set_id != "full_netherite_armor" and set_id != "conduit_power_frame":
                # still add if names look vanilla; they're often terminals
                pass
            if set_id == "full_netherite_armor" and "netherite_helmet" not in available and not any(
                r["result"] == "netherite_helmet" for r in raw
            ):
                continue
            if set_id == "enchanting_room":
                # 1.12 used enchantment_table; 1.13+ enchanting_table
                if "enchanting_table" not in available and not any(r["result"] == "enchanting_table" for r in raw):
                    if "enchantment_table" in available or any(r["result"] == "enchantment_table" for r in raw):
                        rec = {"bookshelf": 15, "enchantment_table": 1}
                    else:
                        continue
            if set_id == "conduit_power_frame":
                if "conduit" not in available and not any(r["result"] == "conduit" for r in raw):
                    continue
            raw.append({
                "result": set_id,
                "ingredients": rec,
                "kind": "set",
                "category": "sets",
                "source": "custom_set",
            })

    # Mob drops are base materials even if a craft recipe exists
    # (e.g. 4 rabbit hide -> 1 leather).
    terminal = FORCE_TERMINAL | set(MOB_DROPS)
    raw = [r for r in raw if r["result"] not in terminal]
    canonical = pick_canonical(raw)

    items = {}
    referenced = set(canonical)
    for rec in canonical.values():
        referenced.update(rec["ingredients"])

    # Always include fuel as a pseudo-item (terminal).
    referenced.add("fuel")

    for item in sorted(referenced):
        rec = canonical.get(item)
        entry = {
            "name": CUSTOM_SETS.get(item, {}).get("name") or display_name(item, lang),
            "category": rec["category"] if rec and rec["kind"] in {"brewing", "set"} else categorize(
                item, rec["category"] if rec else ""
            ),
            "stackSize": stack_size(item),
            "icon": "icons/" + icon_filename(item),
        }
        if rec:
            entry["recipe"] = {k: round(v, 6) if isinstance(v, float) else v for k, v in rec["ingredients"].items()}
            entry["recipeType"] = rec["kind"]
            if rec["kind"] not in {"brewing", "set"}:
                entry["category"] = categorize(item, rec.get("category") or "")
            else:
                entry["category"] = "potions" if rec["kind"] == "brewing" else "sets"
        else:
            entry["category"] = "raw"
        items[item] = entry
        extract_icon(zf, item, names, icons_dir / icon_filename(item), tex_cache)

    for extra in EXTRA_ICON_ITEMS:
        extract_icon(zf, extra, names, icons_dir / icon_filename(extra), tex_cache)

    copy_custom_set_icons(icons_dir)

    fuel = {k: v for k, v in DEFAULT_FUEL.items() if k in items or k in referenced}
    # lava_bucket vs older name
    if "lava_bucket" not in fuel and "lava" in items:
        fuel["lava"] = 100
    # generic planks / log if oak_* missing
    if "oak_planks" not in fuel:
        for alt in ("planks", "spruce_planks", "birch_planks"):
            if alt in items:
                fuel[alt] = 1.5
                break
    if "oak_log" not in fuel:
        for alt in ("log", "oak_wood", "spruce_log"):
            if alt in items:
                fuel[alt] = 1.5
                break
    if "oak_sapling" not in fuel:
        for alt in ("sapling", "oak_sapling"):
            if alt in items:
                fuel[alt] = 0.5
                break

    mobs = {}
    mobs_looting = {}
    # Gold: original used combined rate on "gold" ingot from zombie pigmen.
    gold_mob = "zombified_piglin" if "zombified_piglin" in lang.values() or "zombified_piglin" else "zombie_pigman"
    # Prefer official entity name based on version presence of the item/entity.
    if "zombified_piglin_spawn_egg" in available or version_gte(version, "1.16"):
        gold_entity = "zombified_piglin"
    else:
        gold_entity = "zombie_pigman"

    for item, (entity, kills, kills_l3) in MOB_DROPS.items():
        if item not in items:
            continue
        ent = entity
        if entity in {"zombified_piglin", "zombie_pigman"}:
            ent = gold_entity
        if item == "gold_ingot":
            ent = gold_entity
        mobs[item] = {"entity": ent, "kills": kills}
        mobs_looting[item] = {"entity": ent, "kills": kills_l3}

    return {
        "version": version,
        "itemCount": len(items),
        "craftableCount": sum(1 for v in items.values() if "recipe" in v),
        "items": items,
        "fuel": fuel,
        "mobs": mobs,
        "mobsLooting3": mobs_looting,
    }


def version_gte(a: str, b: str) -> bool:
    def parts(v):
        # 26.3 and 1.21.11 and 26.1.2
        nums = []
        for p in v.split("."):
            try:
                nums.append(int(p))
            except ValueError:
                nums.append(0)
        # Treat 26.x as newer than 1.x
        if nums and nums[0] >= 20 and (not v.startswith("1.")):
            nums = [2, 99] + nums  # after 1.21
        return tuple(nums + [0, 0, 0])[:5]
    return parts(a) >= parts(b)


def craft(item: str, qty: float, items: dict, fuel_type: str, fuel: dict, stack=None) -> dict[str, float]:
    """Expand a crafted item to raw materials (mirrors the web app)."""
    out: dict[str, float] = defaultdict(float)
    rec = items.get(item, {})
    recipe = rec.get("recipe")
    stack = stack or []
    if not recipe or item in stack:
        out[item] += qty
        return out
    stack = stack + [item]
    for ing, amount in recipe.items():
        need = amount * qty
        if ing == "fuel":
            burn = fuel.get(fuel_type) or 1
            out[fuel_type] += need / burn
        else:
            for k, v in craft(ing, need, items, fuel_type, fuel, stack).items():
                out[k] += v
    return dict(out)


def verify(data: dict) -> None:
    items, fuel = data["items"], data["fuel"]
    fuel_type = "coal" if "coal" in fuel else next(iter(fuel))
    for name in ("piston", "sticky_piston", "beacon"):
        if name not in items or "recipe" not in items[name]:
            log(f"  VERIFY {name}: missing")
            continue
        cost = craft(name, 1, items, fuel_type, fuel)
        pretty = ", ".join(f"{k}={v:.4g}" for k, v in sorted(cost.items(), key=lambda kv: kv[0]))
        log(f"  VERIFY {name}: {pretty}")


def write_versions_index(data_dir: Path, versions: list[str], latest: str) -> None:
    existing = []
    for ver in versions:
        path = data_dir / f"{ver}.json"
        if path.exists():
            payload = json.loads(path.read_text())
            existing.append({
                "id": ver,
                "itemCount": payload.get("itemCount"),
                "craftableCount": payload.get("craftableCount"),
            })
    (data_dir / "versions.json").write_text(json.dumps({
        "latest": latest if any(v["id"] == latest for v in existing) else (existing[-1]["id"] if existing else latest),
        "versions": existing,
    }, indent=2) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate mccostcalc data from official Minecraft jars")
    parser.add_argument("--versions", default="", help="Comma-separated version ids (default: major set)")
    parser.add_argument("--cache-dir", default=str(Path("/tmp/mc-jars")), help="Client jar cache directory")
    parser.add_argument("--data-dir", default=str(ROOT / "data"), help="Output JSON directory")
    parser.add_argument("--icons-dir", default=str(ROOT / "icons"), help="Output icon directory")
    parser.add_argument("--list", action="store_true", help="Print latest release and exit")
    args = parser.parse_args(argv)

    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    icons_dir = Path(args.icons_dir)
    icons_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(cache_dir)
    latest = manifest["latest"]["release"]
    if args.list:
        print(f"latest release: {latest}")
        print(f"latest snapshot: {manifest['latest']['snapshot']}")
        return 0

    versions = [v.strip() for v in args.versions.split(",") if v.strip()] or list(DEFAULT_VERSIONS)
    # If the configured latest alias drifted, make sure the real latest is included.
    if latest not in versions:
        log(f"Adding latest release {latest} to the version list")
        versions.append(latest)

    # Wipe stale 16x16 icons, then rebuild latest-first so older versions
    # reuse the newest isometric renders.
    preserve = {"x.png"}
    for old_icon in icons_dir.glob("*"):
        if old_icon.name not in preserve and old_icon.is_file():
            old_icon.unlink()

    for version in reversed(versions):
        log(f"== {version} ==")
        jar = download_client_jar(version, manifest, cache_dir)
        with ZipFile(jar) as zf:
            data = build_version(version, zf, icons_dir)
        out = data_dir / f"{version}.json"
        out.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n")
        log(f"  wrote {out} ({data['craftableCount']} craftable / {data['itemCount']} items)")
        verify(data)

    write_versions_index(data_dir, versions, latest)
    copy_mob_icons(icons_dir)
    write_icon_preview(icons_dir, Path("/tmp/mccostcalc-icon-preview.png"))
    log(f"versions index written, latest={latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
