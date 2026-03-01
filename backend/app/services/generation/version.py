"""Version compatibility maps and classification logic."""

# Maps game version → set of compatible mod version_support values
VERSION_COMPAT = {
    "SE": {"all", "se_only"},
    "AE": {"all", "ae_required", "ae_recommended"},
    "Standard": {"all", "pre_nextgen"},
    "Next-Gen": {"all", "nextgen_only", "nextgen_recommended"},
}

VERSION_NOTES = {
    "SE": "User is on Skyrim SE (not Anniversary Edition). Do NOT include AE-only mods or Creation Club content mods.",
    "AE": "User is on Skyrim AE (Anniversary Edition) with all Creation Club content. Include AE-specific fixes and enhancements where relevant.",
    "Standard": "User is on classic Fallout 4 (pre-Next-Gen Update). Use classic F4SE and Buffout 4 (not NG versions). Some newer mods may not be compatible.",
    "Next-Gen": "User is on Fallout 4 Next-Gen Update. Use Next-Gen compatible F4SE and Buffout 4 NG. Some older mods may need NG-compatible versions.",
}

# VRAM thresholds that map to hardware tier minimums
TIER_MIN_VRAM = {"low": 0, "mid": 6144, "high": 10240, "ultra": 16384}


def is_version_compatible(mod_version_support: str, user_version: str | None) -> bool:
    """Check if a mod's version support tag is compatible with the user's game version."""
    if not user_version:
        return True
    if mod_version_support == "all":
        return True
    return mod_version_support in VERSION_COMPAT.get(user_version, set())
