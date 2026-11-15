"""AI and LLM endpoints — resume bullet rewriting, skill extraction, model switching, and streaming."""

import logging
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

from app.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.llm import (
    BulletRewriteRequest,
    BulletRewriteResponse,
    LLMSkillExtractionRequest,
    LLMSkillExtractionResponse,
    ModelListResponse,
)
from app.schemas.cover_letter import AiCoverLetterRequest, AiCoverLetterResponse
from app.schemas.generator import (
    BulletsGenerateRequest,
    BulletsGenerateResponse,
    ResumeDraftRequest,
    ResumeDraftResponse,
    SuggestSkillsRequest,
    SuggestSkillsResponse,
    SummaryGenerateRequest,
    SummaryGenerateResponse,
)
from app.services.llm_service import (
    call_openrouter,
    stream_openrouter,
    rewrite_bullet_point,
    extract_skills_llm,
    generate_cover_letter,
    generate_bullets,
    generate_resume_draft,
    generate_summary_variants,
    suggest_skill_groups,
)

logger = logging.getLogger(__name__)

router = APIRouter()

RECOMMENDED_MODELS = [
    {
        "id": "mistralai/mistral-7b-instruct:free",
        "name": "Mistral 7B Instruct (Free)",
        "provider": "Mistral",
        "description": "Fast and lightweight open-weight model with free tier.",
    },
    {
        "id": "meta-llama/llama-3.3-70b-instruct:free",
        "name": "Llama 3.3 70B Instruct (Free)",
        "provider": "Meta",
        "description": "State-of-the-art open model with high reasoning capability.",
    },
    {
        "id": "google/gemini-2.0-flash-exp:free",
        "name": "Gemini 2.0 Flash (Free)",
        "provider": "Google",
        "description": "Ultra-fast multimodal model with high quality generation.",
    },
    {
        "id": "openai/gpt-4o-mini",
        "name": "GPT-4o Mini",
        "provider": "OpenAI",
        "description": "Fast, affordable, high intelligence model from OpenAI.",
    },
    {
        "id": "anthropic/claude-3.5-sonnet",
        "name": "Claude 3.5 Sonnet",
        "provider": "Anthropic",
        "description": "Top-tier writing and nuance, ideal for resume crafting.",
    },
]


@router.get(
    "/models",
    response_model=ModelListResponse,
    summary="List available and recommended LLM models",
)
async def list_models(current_user: User = Depends(get_current_user)):
    """List popular OpenRouter models available for dynamic model switching."""
    return ModelListResponse(
        default_model=settings.openrouter_default_model,
        recommended_models=RECOMMENDED_MODELS,
    )


@router.post(
    "/rewrite-bullet",
    response_model=BulletRewriteResponse,
    summary="Rewrite a resume bullet point into a strong, quantified achievement",
)
async def rewrite_bullet(
    payload: BulletRewriteRequest,
    current_user: User = Depends(get_current_user),
):
    """Rewrite a weak or vague resume bullet into a high-impact, quantified statement

    utilizing the Google X-Y-Z formula and seamlessly integrating target technologies.
    """
    result = await rewrite_bullet_point(
        bullet_point=payload.bullet,
        job_context=payload.target_job,
        missing_skills=payload.missing_skills,
        model=payload.model,
    )
    return BulletRewriteResponse(
        original_bullet=result["original_bullet"],
        rewrite_content=result["rewrite_content"],
        model_used=result["model_used"],
        fallback_used=result["fallback_used"],
    )


@router.post(
    "/extract-skills",
    response_model=LLMSkillExtractionResponse,
    summary="Extract technical skills from text using LLM",
)
async def extract_skills(
    payload: LLMSkillExtractionRequest,
    current_user: User = Depends(get_current_user),
):
    """Context-aware technical skill extraction using LLM natural language understanding."""
    result = await extract_skills_llm(
        text=payload.text,
        model=payload.model,
    )
    return LLMSkillExtractionResponse(
        skills=result["skills"],
        count=result["count"],
        model_used=result["model_used"],
        fallback_used=result["fallback_used"],
    )


@router.post(
    "/stream",
    summary="Stream LLM generation token-by-token (SSE)",
)
async def stream_ai_generation(
    prompt: str = Query(..., description="Prompt to complete"),
    model: str | None = Query(None, description="Model to use"),
    current_user: User = Depends(get_current_user),
):
    """Stream response tokens in real-time using Server-Sent Events (SSE)."""
    async def event_generator():
        async for token in stream_openrouter(prompt=prompt, model=model):
            # Send standard SSE format
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"

    import json
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post(
    "/cover-letter",
    response_model=AiCoverLetterResponse,
    summary="Generate cover letter paragraphs from resume + job text (stateless)",
)
async def cover_letter(
    payload: AiCoverLetterRequest,
    current_user: User = Depends(get_current_user),
):
    """Stateless generation (roadmap §8). To get a saved, editable letter in
    one step, use POST /cover-letters/generate instead."""
    result = await generate_cover_letter(
        resume_text=payload.resume_text,
        job_text=payload.job_text,
        job_title=payload.job_title,
        company=payload.company,
        tone=payload.tone,
        model=payload.model,
    )
    return AiCoverLetterResponse(
        paragraphs=result["paragraphs"],
        model_used=result["model_used"],
        fallback_used=result["fallback_used"],
    )


@router.post(
    "/generate-summary",
    response_model=SummaryGenerateResponse,
    summary="Generate 3 professional summary variants (pick-to-insert)",
)
async def generate_summary(
    payload: SummaryGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    result = await generate_summary_variants(
        title=payload.title,
        years=payload.years_experience,
        skills=payload.skills,
        target_role=payload.target_role,
        model=payload.model,
    )
    return SummaryGenerateResponse(**result)


@router.post(
    "/generate-bullets",
    response_model=BulletsGenerateResponse,
    summary="Turn rough notes into achievement bullets (facts are the user's; form is the AI's)",
)
async def generate_bullets_endpoint(
    payload: BulletsGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    result = await generate_bullets(
        role=payload.role,
        company=payload.company,
        notes=payload.notes,
        model=payload.model,
    )
    return BulletsGenerateResponse(**result)


@router.post(
    "/suggest-skills",
    response_model=SuggestSkillsResponse,
    summary="Suggest grouped skills for a role description or JD (dictionary-grounded)",
)
async def suggest_skills(
    payload: SuggestSkillsRequest,
    current_user: User = Depends(get_current_user),
):
    result = await suggest_skill_groups(text=payload.text, model=payload.model)
    return SuggestSkillsResponse(**result)


@router.post(
    "/generate-resume-draft",
    response_model=ResumeDraftResponse,
    summary="Generate a complete resume document skeleton from a job title",
)
async def generate_resume_draft_endpoint(
    payload: ResumeDraftRequest,
    current_user: User = Depends(get_current_user),
):
    result = await generate_resume_draft(
        title=payload.title,
        level=payload.level,
        skills_text=payload.skills,
        model=payload.model,
    )
    return ResumeDraftResponse(**result)
