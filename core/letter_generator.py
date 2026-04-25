"""
Cover letter generation with streaming output and quality scoring.
"""

import re
from datetime import datetime

from utils.nvidia_client import NvidiaLLM
from utils.helpers import cyan, info

from config.settings import (
    GENERATION_TEMPERATURE,
    MAX_TOKENS_GENERATION,
    MIN_LETTER_WORDS,
    MAX_LETTER_WORDS,
    TARGET_LETTER_WORDS,
)


class CoverLetterGenerator:
    """Generate hyper-personalised cover letters using NVIDIA Nemotron."""

    def __init__(self, llm: NvidiaLLM):
        self.llm = llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate(
        self,
        user_profile: dict,
        job_data: dict,
        research: dict,
        style: str = "professional",
    ) -> dict:
        """Generate a cover letter, stream it to the terminal, and evaluate quality."""
        prompt = self._build_prompt(user_profile, job_data, research, style)
        system_prompt = self._system_prompt(style)

        print(f"\n  {cyan('Generating personalised cover letter…')}\n")

        letter = self.llm.generate_streaming(
            prompt,
            system_prompt=system_prompt,
            temperature=GENERATION_TEMPERATURE,
            max_tokens=MAX_TOKENS_GENERATION,
        )

        quality = self._evaluate_quality(letter, job_data, research)
        word_count = len(letter.split())

        return {
            "letter": letter,
            "quality_score": quality["score"],
            "quality": quality,
            "word_count": word_count,
            "generated_at": datetime.now().isoformat(),
        }

    def generate_stream(
        self,
        user_profile: dict,
        job_data: dict,
        research: dict,
        style: str = "professional",
    ):
        """Yield chunks of the generated cover letter, then yield a final payload with quality metrics."""
        prompt = self._build_prompt(user_profile, job_data, research, style)
        system_prompt = self._system_prompt(style)

        full_letter = ""
        # llm.generate with stream=True returns a generator yielding pieces
        stream_gen = self.llm.generate(
            prompt,
            system_prompt=system_prompt,
            temperature=GENERATION_TEMPERATURE,
            max_tokens=MAX_TOKENS_GENERATION,
            stream=True,
        )

        for chunk in stream_gen:
            full_letter += chunk
            # Yield text chunks clearly marked
            yield {"type": "content", "content": chunk}
            
        # Final evaluation
        quality = self._evaluate_quality(full_letter, job_data, research)
        word_count = len(full_letter.split())
        
        final_payload = {
            "type": "done",
            "letter": full_letter,
            "quality_score": quality["score"],
            "quality": quality,
            "word_count": word_count,
            "generated_at": datetime.now().isoformat(),
        }
        yield final_payload

    def regenerate(
        self,
        previous_letter: str,
        feedback: str,
        user_profile: dict,
        job_data: dict,
        research: dict,
    ) -> dict:
        """Regenerate with user feedback."""
        base_prompt = self._build_prompt(user_profile, job_data, research, "professional")

        prompt = f"""{base_prompt}

--- PREVIOUS LETTER ---
{previous_letter}

--- USER FEEDBACK ---
{feedback}

Write an improved version of the cover letter that addresses the user's feedback.
Keep the researched company details and personalisation. Only change what the feedback requests.
"""
        system_prompt = self._system_prompt("professional")

        print(f"\n  {cyan('Regenerating cover letter…')}\n")

        letter = self.llm.generate_streaming(
            prompt,
            system_prompt=system_prompt,
            temperature=GENERATION_TEMPERATURE,
            max_tokens=MAX_TOKENS_GENERATION,
        )

        quality = self._evaluate_quality(letter, job_data, research)
        word_count = len(letter.split())

        return {
            "letter": letter,
            "quality_score": quality["score"],
            "quality": quality,
            "word_count": word_count,
            "generated_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------
    def _build_prompt(
        self,
        user_profile: dict,
        job_data: dict,
        research: dict,
        style: str,
    ) -> str:
        """Assemble the generation prompt from profile, job, and research data."""
        # --- User info (relevant subset only) ---
        personal = user_profile.get("personal_info", {})
        name = personal.get("name", "the applicant")
        summary = user_profile.get("summary", "")

        # Select most relevant experience
        experience_lines = []
        for exp in user_profile.get("experience", []):
            experience_lines.append(f"  {exp.get('title', '')} at {exp.get('company', '')} ({exp.get('duration', '')})")
            for ach in exp.get("achievements", []):
                experience_lines.append(f"    • {ach}")
        experience_text = "\n".join(experience_lines) if experience_lines else "No experience listed."

        # Matching skills
        user_skills = set()
        skills_dict = user_profile.get("skills", {})
        for category in skills_dict.values():
            if isinstance(category, list):
                user_skills.update(category)

        job_skills = set(job_data.get("required_skills", []) + job_data.get("tech_stack", []))
        overlap = user_skills & job_skills
        overlap_text = ", ".join(sorted(overlap)) if overlap else "Various relevant technologies"

        # --- Company research ---
        momentum = research.get("company_momentum", "")
        culture_kw = ", ".join(research.get("cultural_keywords", []))
        pain_points = "\n".join(f"  • {p}" for p in research.get("pain_points", []))
        initiatives = "\n".join(f"  • {i}" for i in research.get("recent_initiatives", []))
        angles = "\n".join(f"  • {a}" for a in research.get("connection_angles", []))
        tech_found = ", ".join(research.get("tech_stack_found", []))

        # --- Job details ---
        company = job_data.get("company_name", "the company")
        position = job_data.get("position_title", "the position")
        role_desc = job_data.get("role_description", "")

        prompt = f"""Write a cover letter for {name} applying to the {position} role at {company}.

=== APPLICANT PROFILE ===
Name: {name}
Summary: {summary}

Experience:
{experience_text}

Matching skills with this role: {overlap_text}

=== JOB DETAILS ===
Company: {company}
Position: {position}
Role description: {role_desc}
Required skills: {', '.join(job_data.get('required_skills', []))}
Tech stack: {', '.join(job_data.get('tech_stack', []))}
Experience required: {job_data.get('experience_years', 'Not specified')}

=== COMPANY RESEARCH (use this to personalise) ===
Company momentum: {momentum}
Cultural keywords: {culture_kw}
Technologies they use: {tech_found}

Pain points to address:
{pain_points}

Recent initiatives to reference:
{initiatives}

Connection angles:
{angles}

=== INSTRUCTIONS ===
Write a {TARGET_LETTER_WORDS}-word cover letter with exactly 3 paragraphs:

PARAGRAPH 1 — THE HOOK:
• Open with a specific recent company achievement, news item, or initiative from the research above
• Do NOT use generic openers like "I am writing to express my interest" or "Dear Sir/Madam"
• Show immediate, specific knowledge of the company
• Naturally transition to why {name} is interested

PARAGRAPH 2 — THE PROOF:
• Match 2-3 of {name}'s specific achievements (with real numbers/metrics) to {company}'s needs
• Reference their tech stack where {name} has overlapping skills
• Address one of their pain points with evidence of similar problem-solving
• Be specific — use the actual numbers from the experience section

PARAGRAPH 3 — THE CLOSE:
• Demonstrate cultural fit using the cultural keywords (woven in naturally, not listed)
• State a specific value proposition: what {name} will accomplish in the first 90 days
• Confident but not arrogant call to action
• Brief, punchy ending

STYLE:
• Professional but human — sounds like a real person, not a template
• NO buzzwords: "passionate", "leverage", "synergy", "dynamic", "thrilled"
• NO filler: "I believe", "I think", "I feel"
• Vary sentence length — mix short punchy with longer ones
• Use specific nouns and verbs, not abstract ones
• Address to "Dear Hiring Team at {company}," (not "Dear Sir/Madam")
• Sign off with "Sincerely,\n{name}"

Write ONLY the letter. No commentary, no explanations, no subject line.
"""
        return prompt

    @staticmethod
    def _system_prompt(style: str) -> str:
        if style == "casual":
            return (
                "You are a professional career writer known for warm, approachable cover letters "
                "that still feel polished. Write conversationally but confidently."
            )
        if style == "formal":
            return (
                "You are a professional career writer known for elegant, formal cover letters. "
                "Use sophisticated vocabulary and a respectful, traditional tone."
            )
        return (
            "You are an elite career writer who creates cover letters that sound like "
            "a talented human spent 45 minutes researching the company and writing a thoughtful, "
            "specific letter. Every letter you write is unique and deeply personalised. "
            "You never produce generic content."
        )

    # ------------------------------------------------------------------
    # Quality evaluation (programmatic, no API call)
    # ------------------------------------------------------------------
    def _evaluate_quality(self, letter: str, job_data: dict, research: dict) -> dict:
        """Score the letter on multiple dimensions. Returns dict with score, checks, recommendations."""
        checks: dict[str, bool] = {}
        recommendations: list[str] = []

        # 1. References company news / initiatives
        initiatives = research.get("recent_initiatives", []) + [research.get("company_momentum", "")]
        news_keywords = set()
        for item in initiatives:
            if item:
                words = [w.lower() for w in item.split() if len(w) > 4]
                news_keywords.update(words)
        letter_lower = letter.lower()
        news_matches = sum(1 for kw in news_keywords if kw in letter_lower)
        checks["references_company_news"] = news_matches >= 2
        if not checks["references_company_news"]:
            recommendations.append("Include more specific references to recent company news or initiatives")

        # 2. Includes metrics
        metric_pattern = r"\d+[%KMB]?|\$\d+|\d+,\d+"
        metrics_found = len(re.findall(metric_pattern, letter))
        checks["includes_metrics"] = metrics_found >= 2
        if not checks["includes_metrics"]:
            recommendations.append("Add more specific metrics from your experience (numbers, percentages)")

        # 3. Matches tech stack
        tech = [t.lower() for t in job_data.get("tech_stack", []) + job_data.get("required_skills", [])]
        tech_matches = sum(1 for t in tech if t in letter_lower)
        checks["matches_tech_stack"] = tech_matches >= 2
        if not checks["matches_tech_stack"]:
            tech_str = ", ".join(job_data.get("tech_stack", [])[:5])
            recommendations.append(f"Mention more of their tech stack ({tech_str})")

        # 4. Uses cultural keywords
        culture_kw = [k.lower() for k in research.get("cultural_keywords", [])]
        culture_matches = sum(1 for k in culture_kw if k in letter_lower)
        checks["uses_cultural_keywords"] = culture_matches >= 2
        if not checks["uses_cultural_keywords"]:
            recommendations.append("Weave in more cultural keywords naturally")

        # 5. Appropriate length
        word_count = len(letter.split())
        checks["appropriate_length"] = MIN_LETTER_WORDS <= word_count <= MAX_LETTER_WORDS
        if not checks["appropriate_length"]:
            recommendations.append(f"Adjust length ({word_count} words, target {MIN_LETTER_WORDS}-{MAX_LETTER_WORDS})")

        # 6. No generic openers
        generic_openers = [
            "i am writing to",
            "dear sir/madam",
            "to whom it may concern",
            "i am excited to apply",
            "i am writing to express",
        ]
        has_generic = any(opener in letter_lower[:200] for opener in generic_openers)
        checks["no_generic_openers"] = not has_generic
        if not checks["no_generic_openers"]:
            recommendations.append("Replace the generic opener with a specific company reference")

        # Score: ~16 points per check, total 0-100
        passed = sum(1 for v in checks.values() if v)
        total = len(checks)
        score = int((passed / total) * 100) if total > 0 else 0

        # Small bonus for strong metrics
        if metrics_found >= 4:
            score = min(100, score + 5)
        if tech_matches >= 4:
            score = min(100, score + 3)

        return {
            "score": score,
            "checks": checks,
            "recommendations": recommendations,
            "word_count": word_count,
        }
