"""LLM tool definitions for the generation pipeline.

PHASE1_TOOLS: Used during discovery phases (search + add mods).
PHASE2_TOOLS: Used during the final compatibility patches phase.
"""

PHASE1_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_nexus",
            "description": (
                "Search Nexus Mods for mods matching a query. "
                "Use varied, specific search terms for different mod categories. "
                "Try different sort orders to discover hidden gems beyond the most popular."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term (e.g. 'texture overhaul', 'combat', 'UI')"},
                    "sort_by": {
                        "type": "string",
                        "enum": ["endorsements", "updated"],
                        "description": "Sort order. Use 'updated' to find newer mods.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_mod_details",
            "description": "Get full details and description for a specific mod. Use this to read about a mod before deciding to include it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mod_id": {"type": "integer", "description": "Nexus mod ID"},
                },
                "required": ["mod_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_modlist",
            "description": "Add a mod to the modlist. Only add mods you've reviewed and believe fit the user's playstyle and hardware.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mod_id": {"type": "integer", "description": "Nexus mod ID"},
                    "name": {"type": "string"},
                    "author": {"type": "string"},
                    "summary": {"type": "string", "description": "Short summary of the mod"},
                    "reason": {"type": "string", "description": "Why this mod fits the user's playstyle"},
                    "load_order": {"type": "integer", "description": "Position in load order"},
                    "estimated_size_mb": {"type": "integer", "description": "Estimated download size in MB"},
                },
                "required": ["mod_id", "name", "reason", "load_order"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finalize",
            "description": "Call when you are done with this phase. Do not call this until you have added all desired mods for this phase.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

PHASE2_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_mod_description",
            "description": (
                "Get the full description of a mod page. "
                "Check this FIRST for patch links and compatibility notes before searching."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "mod_id": {"type": "integer", "description": "Nexus mod ID"},
                },
                "required": ["mod_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_patches",
            "description": "Search Nexus for compatibility patches between mods.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term (e.g. 'SkyUI USSEP patch')"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_patch",
            "description": "Add a compatibility patch mod to the modlist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mod_id": {"type": "integer", "description": "Nexus mod ID of the patch"},
                    "name": {"type": "string"},
                    "author": {"type": "string"},
                    "patches_mods": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Names of the mods this patches",
                    },
                    "reason": {"type": "string"},
                    "load_order": {"type": "integer"},
                },
                "required": ["mod_id", "name", "patches_mods", "reason", "load_order"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "flag_user_knowledge",
            "description": (
                "Flag a compatibility issue where no patch exists yet. "
                "This helps the user know where future AI-generated patches may be needed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "mod_a": {"type": "string", "description": "First mod name"},
                    "mod_b": {"type": "string", "description": "Second mod name"},
                    "issue": {"type": "string", "description": "Description of the compatibility issue"},
                    "severity": {
                        "type": "string",
                        "enum": ["warning", "critical"],
                    },
                },
                "required": ["mod_a", "mod_b", "issue", "severity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finalize_review",
            "description": "Call when you are done reviewing all mods for patches.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]
