"""Code generation API — /code/*."""

from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter, HTTPException

from app.code_generator import code_generator

router = APIRouter(tags=["code"])


@router.post("/code/generate")
async def generate_code(body: dict) -> dict:
    """Generuje kod w wybranym języku programowania."""
    description = body.get("description", "")
    language = body.get("language", "python")
    context = body.get("context")
    include_tests = body.get("include_tests", False)

    if not description:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Field 'description' is required",
        )

    return await code_generator.generate_code(
        description=description,
        language=language,
        context=context,
        include_tests=include_tests,
    )


@router.get("/code/languages")
async def get_supported_languages() -> dict:
    """Lista obsługiwanych języków programowania."""
    languages = code_generator.get_supported_languages()
    return {
        "languages": languages,
        "info": {lang: code_generator.get_language_info(lang) for lang in languages},
    }
