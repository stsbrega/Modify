from fastapi import APIRouter

from app.schemas.specs import SpecsInput, SpecsParseResponse
from app.services.spec_parser import parse_specs
from app.services.tier_classifier import classify_tier

router = APIRouter()


@router.post("/parse", response_model=SpecsParseResponse)
async def parse_hardware_specs(input: SpecsInput):
    specs, method = await parse_specs(input.raw_text)
    specs.tier = classify_tier(specs)
    return SpecsParseResponse(specs=specs, raw_text=input.raw_text, parse_method=method)
