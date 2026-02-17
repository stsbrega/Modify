"""Script to seed the database with initial game data, playstyles, and mods."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, engine, Base
from app.models.game import Game
from app.models.playstyle import Playstyle
from app.models.mod import Mod
from app.models.playstyle_mod import PlaystyleMod
from app.models.compatibility import CompatibilityRule
from app.seeds.seed_data import (
    GAMES,
    PLAYSTYLES,
    SKYRIM_MODS,
    FALLOUT4_MODS,
    SKYRIM_COMPATIBILITY,
    FALLOUT4_COMPATIBILITY,
    SKYRIM_PLAYSTYLE_MODS,
    FALLOUT4_PLAYSTYLE_MODS,
)


async def seed_games(session: AsyncSession) -> dict[str, int]:
    """Seed games table, return slug -> id mapping."""
    game_map = {}
    for game_data in GAMES:
        existing = await session.execute(
            select(Game).where(Game.slug == game_data["slug"])
        )
        game = existing.scalar_one_or_none()
        if not game:
            game = Game(**game_data)
            session.add(game)
            await session.flush()
        game_map[game.slug] = game.id
    return game_map


async def seed_playstyles(
    session: AsyncSession, game_map: dict[str, int]
) -> dict[str, dict[str, int]]:
    """Seed playstyles table, return game_slug -> {playstyle_slug -> id}."""
    ps_map: dict[str, dict[str, int]] = {}
    for game_slug, playstyle_list in PLAYSTYLES.items():
        game_id = game_map.get(game_slug)
        if not game_id:
            continue
        ps_map[game_slug] = {}
        for ps_data in playstyle_list:
            existing = await session.execute(
                select(Playstyle).where(
                    Playstyle.game_id == game_id,
                    Playstyle.slug == ps_data["slug"],
                )
            )
            ps = existing.scalar_one_or_none()
            if not ps:
                ps = Playstyle(game_id=game_id, **ps_data)
                session.add(ps)
                await session.flush()
            ps_map[game_slug][ps.slug] = ps.id
    return ps_map


async def seed_mods(
    session: AsyncSession,
    mod_list: list[tuple],
    nexus_game_domain: str,
) -> dict[str, int]:
    """Seed mods table, return mod_name -> id mapping."""
    mod_map = {}
    for nexus_id, name, author, summary, category, impact, vram in mod_list:
        existing = await session.execute(
            select(Mod).where(
                Mod.nexus_mod_id == nexus_id,
                Mod.nexus_game_domain == nexus_game_domain,
            )
        )
        mod = existing.scalar_one_or_none()
        if not mod:
            mod = Mod(
                nexus_mod_id=nexus_id,
                nexus_game_domain=nexus_game_domain,
                name=name,
                author=author,
                summary=summary,
                category=category,
                performance_impact=impact,
                vram_requirement_mb=vram,
                source="nexus",
                external_url=f"https://www.nexusmods.com/{nexus_game_domain}/mods/{nexus_id}",
            )
            session.add(mod)
            await session.flush()
        mod_map[name] = mod.id
    return mod_map


async def seed_compatibility(
    session: AsyncSession,
    rules: list[tuple],
    mod_map: dict[str, int],
):
    """Seed compatibility rules."""
    for mod1_name, mod2_name, rule_type, notes in rules:
        mod1_id = mod_map.get(mod1_name)
        mod2_id = mod_map.get(mod2_name)
        if not mod1_id or not mod2_id:
            print(f"  Warning: Could not find mod for rule: {mod1_name} -> {mod2_name}")
            continue

        existing = await session.execute(
            select(CompatibilityRule).where(
                CompatibilityRule.mod_id == mod1_id,
                CompatibilityRule.related_mod_id == mod2_id,
                CompatibilityRule.rule_type == rule_type,
            )
        )
        if not existing.scalar_one_or_none():
            rule = CompatibilityRule(
                mod_id=mod1_id,
                related_mod_id=mod2_id,
                rule_type=rule_type,
                notes=notes,
            )
            session.add(rule)


async def seed_playstyle_mods(
    session: AsyncSession,
    playstyle_mod_map: dict[str, list[tuple]],
    ps_map: dict[str, int],
    mod_map: dict[str, int],
):
    """Seed playstyle_mods junction table."""
    for ps_slug, mods in playstyle_mod_map.items():
        ps_id = ps_map.get(ps_slug)
        if not ps_id:
            continue
        for mod_name, priority, tier_min in mods:
            mod_id = mod_map.get(mod_name)
            if not mod_id:
                print(f"  Warning: Could not find mod: {mod_name}")
                continue

            existing = await session.execute(
                select(PlaystyleMod).where(
                    PlaystyleMod.playstyle_id == ps_id,
                    PlaystyleMod.mod_id == mod_id,
                )
            )
            if not existing.scalar_one_or_none():
                pm = PlaystyleMod(
                    playstyle_id=ps_id,
                    mod_id=mod_id,
                    priority=priority,
                    hardware_tier_min=tier_min,
                )
                session.add(pm)


async def main():
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        print("Seeding games...")
        game_map = await seed_games(session)
        print(f"  Games: {list(game_map.keys())}")

        print("Seeding playstyles...")
        ps_map = await seed_playstyles(session, game_map)
        for game_slug, styles in ps_map.items():
            print(f"  {game_slug}: {list(styles.keys())}")

        print("Seeding Skyrim mods...")
        skyrim_mod_map = await seed_mods(
            session, SKYRIM_MODS, "skyrimspecialedition"
        )
        print(f"  Skyrim mods: {len(skyrim_mod_map)}")

        print("Seeding Fallout 4 mods...")
        fo4_mod_map = await seed_mods(session, FALLOUT4_MODS, "fallout4")
        print(f"  Fallout 4 mods: {len(fo4_mod_map)}")

        print("Seeding Skyrim compatibility rules...")
        await seed_compatibility(session, SKYRIM_COMPATIBILITY, skyrim_mod_map)

        print("Seeding Fallout 4 compatibility rules...")
        await seed_compatibility(session, FALLOUT4_COMPATIBILITY, fo4_mod_map)

        print("Seeding Skyrim playstyle-mod assignments...")
        await seed_playstyle_mods(
            session, SKYRIM_PLAYSTYLE_MODS, ps_map.get("skyrimse", {}), skyrim_mod_map
        )

        print("Seeding Fallout 4 playstyle-mod assignments...")
        await seed_playstyle_mods(
            session, FALLOUT4_PLAYSTYLE_MODS, ps_map.get("fallout4", {}), fo4_mod_map
        )

        await session.commit()
        print("Seed complete!")


if __name__ == "__main__":
    asyncio.run(main())
