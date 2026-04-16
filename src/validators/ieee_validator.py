"""
IEEEValidator — Post-generation IEEE compliance cleaner.

After the paper pipeline produces raw sections this module:
  1. Removes duplicated sections.
  2. Ensures exactly one Abstract exists.
  3. Validates keyword relevance using topic similarity.
  4. Enforces IEEE section numbering (I, II, III …).
  5. Merges all references into one IEEE-formatted list.
  6. Detects missing novelty / contribution statements.
  7. Rewrites weak sections automatically via LLM.
  8. Ensures citation ↔ reference mapping consistency.

Returns a cleaned final paper dict ready for IEEE submission.
"""

import re
import logging
from collections import Counter, OrderedDict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("ieee_validator")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(_h)


# ── Constants ─────────────────────────────────────────────────────────────────

# Roman numeral labels for IEEE sections (excluding Abstract which is unnumbered)
_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]

# Canonical IEEE section order
CANONICAL_ORDER: List[str] = [
    "Abstract",
    "Introduction",
    "Related Work",
    "Proposed Methodology",
    "Implementation & Results",
    "Results & Discussion",
    "Conclusion",
]

# Novelty / contribution signal phrases
NOVELTY_PHRASES: List[str] = [
    "we propose",
    "our contribution",
    "novel approach",
    "key contribution",
    "this paper presents",
    "we introduce",
    "our method",
    "proposed framework",
    "proposed approach",
    "proposed system",
    "our approach",
    "we present",
    "main contribution",
    "contributions of this",
    "novelty of",
    "unique contribution",
    "new method",
    "new approach",
    "newly proposed",
    "first to",
]

# Weak-section heuristic thresholds
MIN_SECTION_WORDS = 200
MIN_ABSTRACT_WORDS = 120
WEAK_VOCABULARY_TTR = 0.30  # type-token ratio below this ⇒ weak


# ── Pydantic result model ────────────────────────────────────────────────────

from pydantic import BaseModel, Field
from typing import List as TList


class IEEECleanupAction(BaseModel):
    """One cleanup action taken by the IEEE validator."""
    action: str = Field(..., description="Short label, e.g. 'removed_duplicate'")
    section: str = Field(default="", description="Section affected")
    detail: str = Field(default="", description="Human-readable explanation")


class IEEEValidationReport(BaseModel):
    """Full report returned alongside the cleaned paper."""
    total_actions: int = Field(0, description="Number of cleanup actions applied")
    actions: TList[IEEECleanupAction] = Field(default_factory=list)
    duplicates_removed: int = Field(0)
    abstracts_consolidated: bool = Field(False)
    keyword_relevance_score: float = Field(0.0, ge=0.0, le=1.0)
    numbering_applied: bool = Field(False)
    references_merged: bool = Field(False)
    reference_count: int = Field(0)
    novelty_detected: bool = Field(False)
    novelty_section: str = Field("")
    weak_sections_rewritten: TList[str] = Field(default_factory=list)
    citation_reference_consistent: bool = Field(False)
    orphan_citations: TList[str] = Field(default_factory=list)
    unused_references: TList[int] = Field(default_factory=list)
    is_ieee_ready: bool = Field(False)


# ── Main class ────────────────────────────────────────────────────────────────


class IEEEValidator:
    """
    Post-generation IEEE compliance cleaner.

    Usage::

        validator = IEEEValidator(model_manager=mm)
        cleaned_sections, report = validator.validate_and_clean(
            sections={"Abstract": "...", "Introduction": "...", ...},
            topic="AI-Driven Zero Trust",
            references=[{"title": "...", "link": "..."}],
        )
    """

    def __init__(
        self,
        model_manager=None,
        rewrite_enabled: bool = True,
    ):
        """
        Args:
            model_manager: Optional ModelManager for LLM-powered rewrites.
                           If None, weak-section rewrite is skipped.
            rewrite_enabled: Master switch for LLM rewrites.
        """
        self.mm = model_manager
        self.rewrite_enabled = rewrite_enabled and (model_manager is not None)

    # ── public API ────────────────────────────────────────────────────────

    def validate_and_clean(
        self,
        sections: Dict[str, str],
        topic: str,
        references: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Dict[str, str], IEEEValidationReport]:
        """
        Run ALL eight IEEE cleanup passes and return
        ``(cleaned_sections, report)``.
        """
        refs = references or []
        actions: List[IEEECleanupAction] = []
        cleaned = OrderedDict(sections)  # preserve insertion order

        # 1. Remove duplicated sections
        cleaned, dup_actions = self._remove_duplicates(cleaned)
        actions.extend(dup_actions)

        # 2. Ensure only one Abstract exists
        cleaned, abs_actions = self._consolidate_abstract(cleaned)
        actions.extend(abs_actions)

        # 3. Validate keyword relevance
        kw_score, kw_actions = self._validate_keywords(cleaned, topic)
        actions.extend(kw_actions)

        # 4. Enforce IEEE section numbering
        cleaned, num_actions = self._apply_numbering(cleaned)
        actions.extend(num_actions)

        # 5. Merge references
        refs, merged_refs, ref_actions = self._merge_references(cleaned, refs)
        actions.extend(ref_actions)

        # 6. Detect novelty contribution
        novelty_found, novelty_sec, nov_actions = self._detect_novelty(cleaned, topic)
        actions.extend(nov_actions)

        # 7. Rewrite weak sections
        cleaned, rw_actions, rewritten_names = self._rewrite_weak_sections(cleaned, topic)
        actions.extend(rw_actions)

        # 8. Citation ↔ reference consistency
        cleaned, orphans, unused, cit_actions = self._fix_citations(cleaned, merged_refs)
        actions.extend(cit_actions)

        # ── Build report ──────────────────────────────────────────────────
        report = IEEEValidationReport(
            total_actions=len(actions),
            actions=actions,
            duplicates_removed=sum(1 for a in actions if a.action == "removed_duplicate"),
            abstracts_consolidated=any(a.action == "consolidated_abstract" for a in actions),
            keyword_relevance_score=kw_score,
            numbering_applied=any(a.action == "applied_numbering" for a in actions),
            references_merged=any(a.action == "merged_references" for a in actions),
            reference_count=len(merged_refs),
            novelty_detected=novelty_found,
            novelty_section=novelty_sec,
            weak_sections_rewritten=rewritten_names,
            citation_reference_consistent=len(orphans) == 0 and len(unused) == 0,
            orphan_citations=orphans,
            unused_references=unused,
            is_ieee_ready=(
                kw_score >= 0.4
                and novelty_found
                and len(orphans) == 0
                and len(rewritten_names) == 0  # all weak ones already fixed
            ),
        )

        logger.info(
            "[IEEE VALIDATOR] Done — %d actions, ieee_ready=%s, score=%.2f",
            report.total_actions, report.is_ieee_ready, kw_score,
        )
        return dict(cleaned), report

    # ══════════════════════════════════════════════════════════════════════
    # Pass 1 — Remove duplicated sections
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _normalise_name(name: str) -> str:
        """Lowercase, strip numbering, trim whitespace."""
        name = re.sub(r"^[IVXLC]+[\.\)]\s*", "", name)  # strip roman prefix
        name = re.sub(r"^\d+[\.\)]\s*", "", name)        # strip digit prefix
        return name.strip().lower()

    def _remove_duplicates(
        self, sections: OrderedDict
    ) -> Tuple[OrderedDict, List[IEEECleanupAction]]:
        actions: List[IEEECleanupAction] = []
        seen: Dict[str, str] = {}  # normalised → first original key
        cleaned = OrderedDict()

        for name, text in sections.items():
            norm = self._normalise_name(name)
            if norm in seen:
                # Keep the longer version
                existing_key = seen[norm]
                if len(text.split()) > len(cleaned[existing_key].split()):
                    actions.append(IEEECleanupAction(
                        action="removed_duplicate",
                        section=existing_key,
                        detail=f"Replaced shorter duplicate '{existing_key}' with '{name}'",
                    ))
                    del cleaned[existing_key]
                    cleaned[name] = text
                    seen[norm] = name
                else:
                    actions.append(IEEECleanupAction(
                        action="removed_duplicate",
                        section=name,
                        detail=f"Dropped duplicate '{name}' (shorter than '{existing_key}')",
                    ))
            else:
                seen[norm] = name
                cleaned[name] = text

        return cleaned, actions

    # ══════════════════════════════════════════════════════════════════════
    # Pass 2 — Ensure only one Abstract
    # ══════════════════════════════════════════════════════════════════════

    def _consolidate_abstract(
        self, sections: OrderedDict
    ) -> Tuple[OrderedDict, List[IEEECleanupAction]]:
        actions: List[IEEECleanupAction] = []
        abstract_keys = [k for k in sections if self._normalise_name(k) == "abstract"]

        if len(abstract_keys) <= 1:
            return sections, actions

        # Merge all abstracts — keep longest as base, append unique sentences
        best_key = max(abstract_keys, key=lambda k: len(sections[k].split()))
        merged_text = sections[best_key]

        for k in abstract_keys:
            if k != best_key:
                extra_sents = self._unique_sentences(sections[k], merged_text)
                if extra_sents:
                    merged_text += " " + " ".join(extra_sents)
                del sections[k]
                actions.append(IEEECleanupAction(
                    action="consolidated_abstract",
                    section=k,
                    detail=f"Merged abstract '{k}' into '{best_key}'",
                ))

        sections[best_key] = merged_text
        # Move abstract to front
        sections.move_to_end(best_key, last=False)
        return sections, actions

    @staticmethod
    def _unique_sentences(source: str, target: str) -> List[str]:
        """Return sentences from *source* that are NOT in *target*."""
        src_sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', source) if s.strip()]
        tgt_lower = target.lower()
        return [s for s in src_sents if s.lower() not in tgt_lower]

    # ══════════════════════════════════════════════════════════════════════
    # Pass 3 — Validate keyword relevance
    # ══════════════════════════════════════════════════════════════════════

    def _validate_keywords(
        self, sections: OrderedDict, topic: str
    ) -> Tuple[float, List[IEEECleanupAction]]:
        actions: List[IEEECleanupAction] = []
        topic_kws = self._extract_keywords(topic)
        if not topic_kws:
            return 1.0, actions

        full_text = " ".join(sections.values()).lower()
        full_words = set(re.findall(r'\b\w+\b', full_text))

        matched = [kw for kw in topic_kws if kw in full_words]
        score = len(matched) / len(topic_kws) if topic_kws else 1.0

        if score < 0.4:
            actions.append(IEEECleanupAction(
                action="low_keyword_relevance",
                detail=f"Only {len(matched)}/{len(topic_kws)} topic keywords found (score={score:.2f}). "
                       f"Missing: {', '.join(set(topic_kws) - set(matched))}",
            ))
        elif score < 0.7:
            actions.append(IEEECleanupAction(
                action="medium_keyword_relevance",
                detail=f"{len(matched)}/{len(topic_kws)} topic keywords found (score={score:.2f})",
            ))

        return round(score, 3), actions

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        stop = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "is", "are", "was", "were", "using",
            "based", "from", "this", "that", "its", "their", "through",
        }
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        return [w for w in words if w not in stop]

    # ══════════════════════════════════════════════════════════════════════
    # Pass 4 — Enforce IEEE section numbering
    # ══════════════════════════════════════════════════════════════════════

    def _apply_numbering(
        self, sections: OrderedDict
    ) -> Tuple[OrderedDict, List[IEEECleanupAction]]:
        actions: List[IEEECleanupAction] = []
        numbered = OrderedDict()
        idx = 0  # roman numeral index (skips Abstract)

        for name, text in sections.items():
            norm = self._normalise_name(name)
            # Abstract is unnumbered in IEEE
            if norm == "abstract":
                numbered["Abstract"] = text
                continue

            # Strip any existing numbering from name
            clean_name = re.sub(r"^[IVXLC]+[\.\)]\s*", "", name)
            clean_name = re.sub(r"^\d+[\.\)]\s*", "", clean_name).strip()

            if idx < len(_ROMAN):
                new_name = f"{_ROMAN[idx]}. {clean_name}"
            else:
                new_name = f"{idx + 1}. {clean_name}"

            numbered[new_name] = text
            idx += 1

        if idx > 0:
            actions.append(IEEECleanupAction(
                action="applied_numbering",
                detail=f"Applied IEEE Roman numeral numbering to {idx} sections",
            ))

        return numbered, actions

    # ══════════════════════════════════════════════════════════════════════
    # Pass 5 — Merge all references
    # ══════════════════════════════════════════════════════════════════════

    def _merge_references(
        self,
        sections: OrderedDict,
        external_refs: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[IEEECleanupAction]]:
        """
        Collect inline references extracted from section text and merge
        them with external (arXiv) references into one deduplicated list.
        """
        actions: List[IEEECleanupAction] = []

        # Extract inline references mentioned in text
        inline_refs: List[Dict[str, Any]] = []
        full_text = "\n".join(sections.values())

        # Pattern: anything that looks like a bibliographic entry in text
        # e.g. [1] Author, "Title", Journal, year.
        bib_pattern = re.compile(
            r'\[(\d+)\]\s*(.+?)(?=\[\d+\]|\Z)', re.DOTALL
        )

        for match in bib_pattern.finditer(full_text):
            num, entry = match.group(1), match.group(2).strip()
            if len(entry) > 20:  # skip very short false positives
                inline_refs.append({
                    "number": int(num),
                    "title": entry[:200],
                    "link": "",
                    "source": "inline",
                })

        # Merge: external refs first, then unique inline refs
        merged: List[Dict[str, Any]] = []
        seen_titles: Set[str] = set()

        for ref in external_refs:
            title_norm = ref.get("title", "").lower().strip()
            if title_norm and title_norm not in seen_titles:
                seen_titles.add(title_norm)
                merged.append(ref)

        for ref in inline_refs:
            title_norm = ref.get("title", "").lower().strip()[:80]
            if title_norm and title_norm not in seen_titles:
                seen_titles.add(title_norm)
                merged.append(ref)

        if len(merged) > len(external_refs):
            actions.append(IEEECleanupAction(
                action="merged_references",
                detail=f"Merged {len(external_refs)} external + {len(inline_refs)} inline → {len(merged)} unique references",
            ))

        return external_refs, merged, actions

    # ══════════════════════════════════════════════════════════════════════
    # Pass 6 — Detect novelty contribution
    # ══════════════════════════════════════════════════════════════════════

    def _detect_novelty(
        self, sections: OrderedDict, topic: str
    ) -> Tuple[bool, str, List[IEEECleanupAction]]:
        actions: List[IEEECleanupAction] = []

        for name, text in sections.items():
            text_lower = text.lower()
            for phrase in NOVELTY_PHRASES:
                if phrase in text_lower:
                    logger.info("[IEEE] Novelty found in '%s': '%s'", name, phrase)
                    return True, name, actions

        # Not found — inject a contribution paragraph into Introduction if LLM available
        actions.append(IEEECleanupAction(
            action="missing_novelty",
            detail="No novelty / contribution statement detected in any section",
        ))

        if self.rewrite_enabled:
            intro_key = self._find_section(sections, "introduction")
            if intro_key:
                injected = self._inject_novelty(sections[intro_key], topic)
                if injected:
                    sections[intro_key] = injected
                    actions.append(IEEECleanupAction(
                        action="injected_novelty",
                        section=intro_key,
                        detail="Injected contribution paragraph via LLM into Introduction",
                    ))
                    return True, intro_key, actions

        return False, "", actions

    def _inject_novelty(self, intro_text: str, topic: str) -> Optional[str]:
        """Use LLM to add a contribution paragraph to an Introduction."""
        if not self.mm:
            return None
        prompt = (
            f"The following is the Introduction of an IEEE paper on '{topic}'.\n\n"
            f"--- CURRENT TEXT ---\n{intro_text}\n--- END ---\n\n"
            "This section is missing a clear novelty / contribution statement.\n"
            "Rewrite the FULL Introduction, adding a paragraph that clearly states "
            "the novel contributions of this paper (use phrases like 'our key contributions', "
            "'we propose', 'the novelty of this work').\n"
            "Output ONLY the rewritten Introduction — no headings, no markdown."
        )
        try:
            return self.mm.generate_with_fallback(
                prompt=prompt,
                system_prompt="You are an IEEE paper editor focused on strengthening contribution statements.",
                max_tokens=2000,
                temperature=0.5,
            )
        except Exception as exc:
            logger.error("[IEEE] Novelty injection failed: %s", exc)
            return None

    # ══════════════════════════════════════════════════════════════════════
    # Pass 7 — Rewrite weak sections
    # ══════════════════════════════════════════════════════════════════════

    def _rewrite_weak_sections(
        self, sections: OrderedDict, topic: str
    ) -> Tuple[OrderedDict, List[IEEECleanupAction], List[str]]:
        actions: List[IEEECleanupAction] = []
        rewritten: List[str] = []

        for name, text in list(sections.items()):
            norm = self._normalise_name(name)
            min_w = MIN_ABSTRACT_WORDS if norm == "abstract" else MIN_SECTION_WORDS
            reason = self._is_weak(text, min_w)
            if reason:
                actions.append(IEEECleanupAction(
                    action="weak_section_detected",
                    section=name,
                    detail=f"Weak: {reason}",
                ))
                if self.rewrite_enabled:
                    improved = self._rewrite_section(name, text, topic)
                    if improved and len(improved.split()) > len(text.split()):
                        sections[name] = improved
                        rewritten.append(name)
                        actions.append(IEEECleanupAction(
                            action="section_rewritten",
                            section=name,
                            detail=f"Rewritten via LLM ({len(text.split())} → {len(improved.split())} words)",
                        ))

        return sections, actions, rewritten

    @staticmethod
    def _is_weak(text: str, min_words: int) -> Optional[str]:
        """Return reason if section is weak, else None."""
        words = text.split()
        wc = len(words)
        if wc < min_words:
            return f"too short ({wc}/{min_words} words)"

        lower_words = [w.lower() for w in words]
        if lower_words:
            ttr = len(set(lower_words)) / len(lower_words)
            if ttr < WEAK_VOCABULARY_TTR:
                return f"low vocabulary diversity (TTR={ttr:.2f})"

        # Check for excessive repetition of any single phrase (3+ word ngrams)
        ngrams = [" ".join(lower_words[i:i+3]) for i in range(len(lower_words) - 2)]
        if ngrams:
            most_common = Counter(ngrams).most_common(1)[0]
            if most_common[1] > 5:
                return f"repetitive phrase '{most_common[0]}' appears {most_common[1]} times"

        return None

    def _rewrite_section(self, section_name: str, text: str, topic: str) -> Optional[str]:
        """LLM rewrite for a weak section."""
        if not self.mm:
            return None
        prompt = (
            f"Rewrite the following '{section_name}' section of an IEEE research paper "
            f"on '{topic}'. The current version is weak.\n\n"
            f"--- CURRENT TEXT ---\n{text}\n--- END ---\n\n"
            "Requirements:\n"
            "- Expand to at least 350 words\n"
            "- Improve vocabulary diversity\n"
            "- Add [N] style citations\n"
            "- Maintain formal IEEE academic tone\n"
            "- Output ONLY the rewritten section text"
        )
        try:
            return self.mm.generate_with_fallback(
                prompt=prompt,
                system_prompt="You are a senior IEEE conference paper reviewer rewriting a weak section.",
                max_tokens=2000,
                temperature=0.6,
            )
        except Exception as exc:
            logger.error("[IEEE] Rewrite failed for '%s': %s", section_name, exc)
            return None

    # ══════════════════════════════════════════════════════════════════════
    # Pass 8 — Citation ↔ Reference mapping consistency
    # ══════════════════════════════════════════════════════════════════════

    def _fix_citations(
        self,
        sections: OrderedDict,
        references: List[Dict[str, Any]],
    ) -> Tuple[OrderedDict, List[str], List[int], List[IEEECleanupAction]]:
        """
        Ensure every [N] citation has a matching reference and vice-versa.
        Returns ``(sections, orphan_citations, unused_ref_numbers, actions)``.
        """
        actions: List[IEEECleanupAction] = []
        full_text = "\n".join(sections.values())

        # Collect all citation numbers used in text
        cited_nums: Set[int] = set()
        for m in re.finditer(r'\[(\d+)\]', full_text):
            cited_nums.add(int(m.group(1)))

        # Reference numbers available (1-indexed)
        ref_nums: Set[int] = set(range(1, len(references) + 1))

        orphans = sorted(cited_nums - ref_nums)
        unused = sorted(ref_nums - cited_nums)

        if orphans:
            actions.append(IEEECleanupAction(
                action="orphan_citations",
                detail=f"Citations without references: {orphans}",
            ))
            # Remap orphan citations to valid range
            sections = self._remap_orphan_citations(sections, orphans, len(references))

        if unused:
            actions.append(IEEECleanupAction(
                action="unused_references",
                detail=f"References never cited: {unused}",
            ))

        if not orphans and not unused and cited_nums:
            actions.append(IEEECleanupAction(
                action="citations_consistent",
                detail=f"All {len(cited_nums)} citations map to references correctly",
            ))

        return sections, [str(o) for o in orphans], unused, actions

    @staticmethod
    def _remap_orphan_citations(
        sections: OrderedDict, orphans: List[int], max_ref: int
    ) -> OrderedDict:
        """Replace orphan citation numbers with valid ones (cyclic remap)."""
        if max_ref == 0:
            return sections

        remap = {}
        for i, orphan in enumerate(orphans):
            remap[orphan] = (i % max_ref) + 1

        for name, text in sections.items():
            for old_num, new_num in remap.items():
                text = re.sub(
                    rf'\[{old_num}\]',
                    f'[{new_num}]',
                    text,
                )
            sections[name] = text

        return sections

    # ── Utility helpers ───────────────────────────────────────────────────

    @staticmethod
    def _find_section(sections: OrderedDict, keyword: str) -> Optional[str]:
        """Find a section key whose normalised name contains *keyword*."""
        for key in sections:
            norm = re.sub(r'^[IVXLC\d]+[\.\)]\s*', '', key).strip().lower()
            if keyword in norm:
                return key
        return None

    # ── Convenience: Assemble final IEEE text ─────────────────────────────

    @staticmethod
    def assemble_ieee_text(
        sections: Dict[str, str],
        references: List[Dict[str, Any]],
        topic: str,
    ) -> str:
        """
        Assemble a single string from cleaned sections + references,
        ready for IEEE PDF generation.
        """
        parts: List[str] = []

        for name, body in sections.items():
            parts.append(f"\n{name}\n")
            parts.append(body.strip())
            parts.append("")

        # IEEE references block
        if references:
            parts.append("\nREFERENCES\n")
            for i, ref in enumerate(references, 1):
                title = ref.get("title", "Unknown")
                link = ref.get("link", "")
                if link:
                    parts.append(f"[{i}] {title}, {link}")
                else:
                    parts.append(f"[{i}] {title}")
            parts.append("")

        return "\n".join(parts)
