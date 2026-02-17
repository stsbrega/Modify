import json
import re
import logging

from app.schemas.specs import HardwareSpecs

logger = logging.getLogger(__name__)

# GPU patterns
GPU_PATTERNS = [
    re.compile(r"(NVIDIA\s+GeForce\s+[A-Z]{2,3}\s+\d{3,4}\s*(?:Ti\s*(?:SUPER)?|SUPER|XT)?)", re.IGNORECASE),
    re.compile(r"(GeForce\s+[A-Z]{2,3}\s+\d{3,4}\s*(?:Ti\s*(?:SUPER)?|SUPER|XT)?)", re.IGNORECASE),
    re.compile(r"(AMD\s+Radeon\s+RX\s+\d{3,4}\s*(?:XT|XTX)?)", re.IGNORECASE),
    re.compile(r"(Radeon\s+RX\s+\d{3,4}\s*(?:XT|XTX)?)", re.IGNORECASE),
    re.compile(r"(Intel\s+Arc\s+[A-Z]\d{3,4}[A-Z]?)", re.IGNORECASE),
    # Catch NVIDIA RTX/GTX without GeForce prefix
    re.compile(r"((?:RTX|GTX)\s+\d{3,4}\s*(?:Ti\s*(?:SUPER)?|SUPER)?)", re.IGNORECASE),
]

# VRAM patterns
VRAM_PATTERNS = [
    re.compile(r"(\d+)\s*GB\s*(?:GDDR\d[A-Z]?|VRAM|Video\s*(?:RAM|Memory))", re.IGNORECASE),
    re.compile(r"(?:VRAM|Video\s*(?:RAM|Memory)|Dedicated\s*(?:GPU|Video)\s*Memory)\s*[:=]?\s*(\d+)\s*(?:GB|MB)", re.IGNORECASE),
    re.compile(r"(\d{4,})\s*MB\s*(?:GDDR|VRAM|Video|Dedicated)", re.IGNORECASE),
    re.compile(r"(?:GDDR\d[A-Z]?)\s*[:=]?\s*(\d+)\s*(?:GB|MB)", re.IGNORECASE),
]

# CPU patterns
CPU_PATTERNS = [
    re.compile(r"(Intel\s+Core\s+(?:Ultra\s+)?\d?\s*i\d[- ]\d{4,5}[A-Z]{0,3})", re.IGNORECASE),
    re.compile(r"(Intel\s+Core\s+i\d[- ]\d{4,5}[A-Z]{0,3})", re.IGNORECASE),
    re.compile(r"(AMD\s+Ryzen\s+\d\s+\d{4}X?\d?[A-Z]*(?:\s*3D)?)", re.IGNORECASE),
    re.compile(r"(Intel\s+Core\s+Ultra\s+\d\s+\d{3}[A-Z]?)", re.IGNORECASE),
    re.compile(r"(AMD\s+Ryzen\s+\d\s+\d{3,4}[A-Z]*)", re.IGNORECASE),
    # Catch processor lines from system info
    re.compile(r"(?:Processor|CPU)\s*[:=]?\s*(.+?)(?:\s*@|\s*\d+\.\d+\s*GHz|\n|$)", re.IGNORECASE),
]

# RAM patterns
RAM_PATTERNS = [
    re.compile(r"(\d{1,3})\s*GB\s*(?:DDR\d|RAM|System\s*Memory|Memory)", re.IGNORECASE),
    re.compile(r"(?:RAM|Memory|System\s*Memory|Installed\s*(?:Physical\s*)?Memory|Total\s*Physical\s*Memory)\s*[:=]?\s*(\d{1,3})\s*GB", re.IGNORECASE),
    re.compile(r"(\d{1,3})\s*GB\s*(?:installed|total|physical)", re.IGNORECASE),
    re.compile(r"(\d{1,3})\s*,?\d*\s*GB\s*(?:usable)?", re.IGNORECASE),
]


LLM_PARSE_PROMPT = """Extract hardware specifications from the following text.
Return ONLY a JSON object with these fields (use null if not found):
{
  "gpu": "GPU model name (e.g. NVIDIA GeForce RTX 4070 Ti)",
  "vram_mb": VRAM in megabytes as integer (e.g. 12288 for 12GB),
  "cpu": "CPU model name (e.g. AMD Ryzen 7 7800X3D)",
  "ram_gb": RAM in gigabytes as integer (e.g. 32)
}

Text to parse:
"""


def _extract_first_match(text: str, patterns: list[re.Pattern]) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def _parse_vram(text: str) -> int | None:
    for pattern in VRAM_PATTERNS:
        match = pattern.search(text)
        if match:
            value = int(match.group(1))
            if value >= 1024:
                return value
            return value * 1024
    return None


def _parse_ram(text: str) -> int | None:
    for pattern in RAM_PATTERNS:
        match = pattern.search(text)
        if match:
            return int(match.group(1))
    return None


def parse_specs_regex(raw_text: str) -> HardwareSpecs:
    """Parse hardware specs using regex patterns."""
    return HardwareSpecs(
        gpu=_extract_first_match(raw_text, GPU_PATTERNS),
        vram_mb=_parse_vram(raw_text),
        cpu=_extract_first_match(raw_text, CPU_PATTERNS),
        ram_gb=_parse_ram(raw_text),
    )


async def parse_specs_llm(raw_text: str) -> HardwareSpecs | None:
    """Fallback: use LLM to extract specs from freeform text."""
    try:
        from app.llm.provider import LLMProviderFactory

        llm = LLMProviderFactory.create()
        response = await llm.generate(
            system_prompt="You are a hardware specification parser. Extract PC hardware details and return ONLY valid JSON.",
            user_prompt=LLM_PARSE_PROMPT + raw_text,
        )

        # Try to extract JSON from response
        response = response.strip()
        if response.startswith("```"):
            # Strip markdown code block
            lines = response.split("\n")
            response = "\n".join(
                line for line in lines if not line.strip().startswith("```")
            )

        data = json.loads(response)
        return HardwareSpecs(
            gpu=data.get("gpu"),
            vram_mb=data.get("vram_mb"),
            cpu=data.get("cpu"),
            ram_gb=data.get("ram_gb"),
        )
    except Exception as e:
        logger.warning(f"LLM spec parsing failed: {e}")
        return None


async def parse_specs(raw_text: str) -> tuple[HardwareSpecs, str]:
    """Parse hardware specs from freeform text.

    Uses regex first, falls back to LLM if regex can't find GPU or CPU.
    Returns (specs, method) where method is 'regex', 'llm', or 'regex_partial'.
    """
    specs = parse_specs_regex(raw_text)

    # If regex found at least GPU or CPU, we're good
    if specs.gpu or specs.cpu:
        return specs, "regex"

    # Fallback to LLM
    llm_specs = await parse_specs_llm(raw_text)
    if llm_specs and (llm_specs.gpu or llm_specs.cpu):
        return llm_specs, "llm"

    # Return partial regex results
    return specs, "regex_partial"
