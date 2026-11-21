# mccostcalc

Calculate the material cost of a Minecraft Java Edition build, down to raw
materials, fuel, and (optionally) how many mobs you would need to kill.

Live version: [https://mccostcalc.pages.dev](https://mccostcalc.pages.dev)

The original PHP app targeted 1.13/1.14 and is kept under `legacy/`. This
rewrite is a static web app, so it can run on Cloudflare Pages without a
server, and it can switch between multiple official game versions.

## Using it

1. Pick a Minecraft version (defaults to the latest Java release).
2. Search or browse craftable items, click to add them, and enter quantities.
3. Choose a fuel type and whether mob drops should be converted into kill counts.
4. Hit Calculate to see raw materials, stacks, and chests.

The selected version is stored in the URL (`?v=1.16.5`) and in `localStorage`.

## Recipe data

Recipes are extracted from the official Minecraft client jar published by
Mojang (`data/minecraft/recipe` or, before 1.21, `data/minecraft/recipes`).
Crafting, smelting, smithing (netherite upgrades), and brewing are included.
Stonecutter recipes are used only when there is no crafting/smelting recipe,
and mined blocks such as cobblestone stay as base materials.

A few convenience "sets" from the original app are still included: full armor
stands, an enchanting room, a nether portal, a max-size conduit frame, and a
wither fight breakdown for the nether star.

## Regenerating data for a new Minecraft version

You need Python 3.9+ and [Pillow](https://pillow.readthedocs.io/) (for potion
icons). Jars are downloaded from Mojang's version manifest and cached.

```bash
# Show the current latest release
python3 scripts/generate_data.py --list

# Add or refresh one version, then rebuild the version index
python3 scripts/generate_data.py --versions 26.4

# Rebuild the default set of major versions (1.13.2 through latest)
python3 scripts/generate_data.py
```

Output files:

- `data/versions.json` — list of bundled versions and which one is latest
- `data/<version>.json` — recipes, names, fuel, and mob rates for that version
- `icons/` — 16×16 item textures extracted from the same jars

The generator cache defaults to `/tmp/mc-jars`. Override with `--cache-dir`.

Default versions bundled today: 1.13.2, 1.14.4, 1.15.2, 1.16.5, 1.17.1,
1.18.2, 1.19.4, 1.20.1, 1.20.6, 1.21.1, 1.21.4, 1.21.11, 26.1.2, 26.2, and
26.3 (or whatever the manifest reports as the latest release).

## Local preview

This is a static site. From the repository root:

```bash
python3 -m http.server 8080
```

Then open `http://localhost:8080`.

## Deploy

Publish the repository root as a Cloudflare Pages site (no build command).
The live project name is `mccostcalc`.

```bash
npx wrangler pages deploy . --project-name mccostcalc --branch main
```

Do not upload `legacy/`, `scripts/`, or `.git` if you are assembling a
hand-built folder; they are not required at runtime.

## License

See `LICENSE.md` for the project license. Minecraft assets and recipe data
remain the property of Mojang / Microsoft and are used here only to drive
the calculator.
