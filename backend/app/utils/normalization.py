"""Lớp normalization cho extraction result.

Pipeline của project:
1. LLM/mock extractor trả về dữ liệu thô
2. Normalization làm sạch, chuẩn hóa, gộp trùng
3. UCP calculation chỉ dùng dữ liệu đã normalize
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from app.models.requests import ActorItem, NormalizedUseCaseDocument, UseCaseItem
from app.services.mapping_config import (
    ACTION_VERB_PATTERNS,
    ACTOR_NAME_NORMALIZATION,
    AVERAGE_USE_CASE_PREFIXES,
    AVERAGE_USE_CASE_ACTION_KEYWORDS,
    COMPLEX_USE_CASE_PREFIXES,
    COMPLEX_USE_CASE_ACTION_KEYWORDS,
    EXTERNAL_ACTOR_KEYWORDS,
    HUMAN_ACTOR_KEYWORDS,
    IGNORE_AS_ACTOR,
    INTERNAL_STEP_EXCLUSIONS,
    MERGE_RULES,
    ROLE_LIKE_SUFFIXES,
    SIMPLE_USE_CASE_PREFIXES,
    SIMPLE_USE_CASE_ACTION_KEYWORDS,
    TRAILING_USE_CASE_FILLER_WORDS,
    VERB_CANONICAL_MAP,
)
from app.utils.parser import normalize_name, split_sentences

ALLOWED_COMPLEXITIES = {"simple", "average", "complex"}
ARTICLE_PATTERN = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)
ACTOR_TRIGGER_PATTERN = re.compile(
    r"(?:the|a|an)\s+([a-z][a-z\s-]{0,50}?)\s+(?:can|may|must|should|will)\b",
    re.IGNORECASE,
)
ALLOW_PATTERN = re.compile(
    r"allows\s+(?:the|a|an)?\s*([a-z][a-z\s-]{0,50}?)\s+to\b",
    re.IGNORECASE,
)
EXTERNAL_TRIGGER_PATTERN = re.compile(
    r"(?:external\s+)?([a-z][a-z\s-]{0,50}?(?:service|gateway|api|provider|system))\b",
    re.IGNORECASE,
)
BACKGROUND_SUBJECT_ACTION_PATTERN = re.compile(
    r"^(?:the\s+)?(?:system|[a-z][a-z\s-]{0,50}?(?:service|gateway|api|provider|system))\s+"
    r"(?:sends?|notifies?|alerts?|logs?|stores?|saves?|updates?)\b",
    re.IGNORECASE,
)
VALID_TRANSACTIONAL_SEND_PHRASES = (
    "send money",
    "transfer money",
    "transfer funds",
    "transfer payment",
)
# Ghi chú:
# Nhóm phrase này được thêm để tách bạch 2 trường hợp:
# 1. "Send Money" là business use case hợp lệ của domain banking
# 2. "Send Confirmation" là internal step phải loại bỏ


def normalize_extraction_result(
    actors: Iterable[ActorItem],
    use_cases: Iterable[UseCaseItem],
    source_text: str = "",
) -> tuple[list[ActorItem], list[UseCaseItem]]:
    """Chuẩn hóa toàn bộ extraction result."""
    # Hàm này là "cổng vào" chính của layer normalization.
    # Mọi dữ liệu extraction đều nên đi qua đây trước khi tính UCP.
    normalized_actors = normalize_actors(actors, source_text)
    normalized_use_cases = normalize_use_cases(use_cases, source_text)
    return normalized_actors, normalized_use_cases


def normalize_use_case_documents(
    use_case_documents: Iterable[NormalizedUseCaseDocument],
) -> list[NormalizedUseCaseDocument]:
    """Chuẩn hóa danh sách Use Case Specification về schema chuẩn nội bộ."""
    normalized_documents: list[NormalizedUseCaseDocument] = []

    for use_case_document in use_case_documents:
        normalized_document = normalize_use_case_document(use_case_document)
        if normalized_document is not None:
            normalized_documents.append(normalized_document)

    return normalized_documents


def normalize_structured_use_cases(
    use_cases: Iterable[UseCaseItem],
) -> list[UseCaseItem]:
    """Chuẩn hóa nhẹ cho use case đến từ tài liệu có cấu trúc.

    Với Use Case Specification chuẩn:
    - tên use case đã đến từ field chính thức trong tài liệu
    - không nên áp các rule mạnh của free-text như bỏ notify/send hay rút gọn tên

    Vì vậy hàm này chỉ:
    - làm sạch tên
    - chuẩn hóa complexity
    - loại trùng
    """
    normalized_items: list[UseCaseItem] = []

    for use_case in use_cases:
        cleaned_name = normalize_name(use_case.name).strip(" .,:;")
        if not cleaned_name:
            continue

        # Một vài tên trong tài liệu vẫn được rút gọn nhẹ để giữ tính nhất quán khi demo.
        if cleaned_name.lower() in {"register account", "create account"}:
            cleaned_name = "Register"

        normalized_items.append(
            UseCaseItem(
                name=_title_case_name(cleaned_name),
                complexity=_normalize_complexity(use_case.complexity) or "average",
                description=use_case.description,
            )
        )

    return _deduplicate_use_cases(normalized_items)


def normalize_use_case_document(
    use_case_document: NormalizedUseCaseDocument,
) -> NormalizedUseCaseDocument | None:
    """Chuẩn hóa một use case document đơn lẻ.

    Mục tiêu:
    - chuẩn hóa tên field
    - làm sạch actor
    - làm sạch tên use case
    - làm sạch danh sách bước
    - tách primary / secondary actor nếu source bị gộp chung
    """
    normalized_name = _standardize_use_case_name(use_case_document.use_case_name)
    if not normalized_name:
        return None

    primary_actor = _standardize_actor_label(use_case_document.primary_actor)
    secondary_actors = [_standardize_actor_label(actor_name) for actor_name in use_case_document.secondary_actors]
    secondary_actors = [actor_name for actor_name in secondary_actors if actor_name]

    # Nếu primary actor bị gộp nhiều actor trong một field,
    # lấy actor đầu là primary, các actor còn lại đẩy sang secondary.
    if primary_actor and any(separator in primary_actor.lower() for separator in (",", " and ", ";", " & ")):
        actor_candidates = _split_actor_names_from_single_field(primary_actor)
        if actor_candidates:
            primary_actor = actor_candidates[0]
            secondary_actors = actor_candidates[1:] + secondary_actors

    if primary_actor is None and secondary_actors:
        primary_actor = secondary_actors.pop(0)

    return NormalizedUseCaseDocument(
        use_case_id=_clean_optional_multiline_text(use_case_document.use_case_id),
        use_case_name=normalized_name,
        primary_actor=primary_actor,
        secondary_actors=_deduplicate_names(secondary_actors),
        description=_clean_optional_multiline_text(use_case_document.description),
        trigger=_clean_optional_multiline_text(use_case_document.trigger),
        preconditions=_clean_optional_multiline_text(use_case_document.preconditions),
        postconditions=_clean_optional_multiline_text(use_case_document.postconditions),
        main_success_scenario=_clean_step_list(use_case_document.main_success_scenario),
        alternative_flows=_clean_step_list(use_case_document.alternative_flows),
        exception_flows=_clean_step_list(use_case_document.exception_flows),
        priority=_clean_optional_multiline_text(use_case_document.priority),
        business_rules=_clean_optional_multiline_text(use_case_document.business_rules),
        notes=_clean_optional_multiline_text(use_case_document.notes),
    )


def normalize_actors(actors: Iterable[ActorItem], source_text: str = "") -> list[ActorItem]:
    """Chuẩn hóa actor:
    - bỏ System
    - map human/external
    - gộp trùng
    - fallback cho role chưa thấy trước đó
    """
    # Ghép actor có sẵn từ extractor với actor quét thêm trực tiếp từ source_text.
    # Cách này giúp tăng độ bền khi extractor thô bỏ sót một vài actor.
    candidates = list(actors) + _extract_actor_candidates_from_text(source_text)
    normalized_items: list[ActorItem] = []

    for actor in candidates:
        # Mỗi actor sẽ được làm sạch và gán complexity lại theo rule cố định.
        normalized_actor = _normalize_actor_item(actor.name, actor.complexity)
        if normalized_actor is not None:
            normalized_items.append(normalized_actor)

    return _deduplicate_actors(normalized_items)


def normalize_use_cases(use_cases: Iterable[UseCaseItem], source_text: str = "") -> list[UseCaseItem]:
    """Chuẩn hóa use case:
    - giữ verb + noun theo domain
    - bỏ internal step
    - merge sub-action
    - gộp trùng
    """
    # Tương tự actor, use case cũng lấy từ hai nguồn:
    # 1. extractor thô
    # 2. quét lại từ chính source text
    candidates = list(use_cases) + _extract_use_case_candidates_from_text(source_text)
    normalized_items: list[UseCaseItem] = []

    for use_case in candidates:
        # Mỗi use case sẽ được:
        # - bỏ nếu là internal step
        # - đổi tên về dạng chuẩn
        # - phân loại lại complexity
        normalized_use_case = _normalize_use_case_item(
            use_case.name,
            use_case.complexity,
            use_case.description,
        )
        if normalized_use_case is not None:
            normalized_items.append(normalized_use_case)

    return _deduplicate_use_cases(normalized_items)


def _extract_actor_candidates_from_text(text: str) -> list[ActorItem]:
    """Quét actor từ free-text input."""
    if not text.strip():
        return []

    lowered_text = text.lower()
    items: list[ActorItem] = []

    # Quét từ điển human actor trước để bắt các vai trò phổ biến đa domain.
    for keyword in sorted(HUMAN_ACTOR_KEYWORDS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(keyword)}\b", lowered_text):
            items.append(ActorItem(name=keyword.title(), complexity="complex"))

    # Quét tiếp external actor như gateway, service, api...
    for keyword in sorted(EXTERNAL_ACTOR_KEYWORDS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(keyword)}\b", lowered_text):
            items.append(ActorItem(name=_title_case_name(keyword), complexity="simple"))

    # Các regex bên dưới dùng để bắt actor theo mẫu câu tự nhiên.
    for match in ACTOR_TRIGGER_PATTERN.findall(text):
        items.append(ActorItem(name=_title_case_name(match), complexity="complex"))

    for match in ALLOW_PATTERN.findall(text):
        items.append(ActorItem(name=_title_case_name(match), complexity="complex"))

    for match in EXTERNAL_TRIGGER_PATTERN.findall(text):
        items.append(ActorItem(name=_title_case_name(match), complexity="simple"))

    return items


def _extract_use_case_candidates_from_text(text: str) -> list[UseCaseItem]:
    """Quét use case từ free-text input."""
    items: list[UseCaseItem] = []

    for sentence in split_sentences(text):
        items.extend(_extract_use_case_candidates_from_sentence(sentence))

    return items


def _extract_use_case_candidates_from_sentence(sentence: str) -> list[UseCaseItem]:
    """Tách một câu tự nhiên thành các candidate use case."""
    cleaned_sentence = normalize_name(sentence)
    lowered_sentence = cleaned_sentence.lower()

    if not cleaned_sentence:
        return []

    # Câu kiểu "Payment Gateway is used to process..." chỉ mô tả tích hợp,
    # không phải danh sách use case do actor thực hiện trực tiếp.
    if " is used to " in lowered_sentence:
        return []

    # Loại các câu mô tả tác vụ nền như "System sends reminder".
    if _is_background_processing_sentence(cleaned_sentence):
        return []

    action_text = cleaned_sentence
    patterns = [
        r"^The system allows (?:the |a |an )?[A-Za-z\s-]+ to ",
        r"^The system lets (?:the |a |an )?[A-Za-z\s-]+ to ",
        r"^(?:The |A |An )?[A-Za-z\s-]+ can ",
        r"^(?:The |A |An )?[A-Za-z\s-]+ may ",
        r"^(?:The |A |An )?[A-Za-z\s-]+ must ",
        r"^(?:The |A |An )?[A-Za-z\s-]+ should ",
        r"^(?:The |A |An )?[A-Za-z\s-]+ will ",
    ]

    for pattern in patterns:
        action_text = re.sub(pattern, "", action_text, flags=re.IGNORECASE)

    # Tách nhiều hành động trong cùng một câu thành nhiều candidate riêng.
    raw_segments = re.split(r",| and | or ", action_text)
    items: list[UseCaseItem] = []

    for segment in raw_segments:
        cleaned_segment = normalize_name(segment).strip(" .:;")
        if not cleaned_segment:
            continue
        items.append(UseCaseItem(name=cleaned_segment, complexity="average"))

    return items


def _normalize_actor_item(name: str, complexity: str) -> ActorItem | None:
    """Chuẩn hóa một actor đơn lẻ."""
    cleaned_name = _clean_actor_name(name)
    if not cleaned_name:
        return None

    lowered_name = cleaned_name.lower()

    # Bỏ các tên không được xem là actor trong UCP.
    if lowered_name in IGNORE_AS_ACTOR:
        return None

    # Nếu tên actor vẫn chứa các từ như "system" nhưng không phải external actor thật,
    # mình cũng loại bỏ để tránh kéo sai UAW.
    if any(
        ignored == lowered_name
        or lowered_name.startswith(f"{ignored} ")
        or lowered_name.endswith(f" {ignored}")
        for ignored in IGNORE_AS_ACTOR
    ) and not (
        _is_external_actor_name(lowered_name)
        or _looks_like_interface_actor_name(lowered_name)
    ):
        return None

    if lowered_name in ACTOR_NAME_NORMALIZATION:
        cleaned_name = ACTOR_NAME_NORMALIZATION[lowered_name]
        lowered_name = cleaned_name.lower()

    # Rule phân loại ưu tiên:
    # 1. human actor -> complex
    # 2. external actor -> simple
    if _is_human_actor_name(lowered_name):
        return ActorItem(name=_title_case_name(cleaned_name), complexity="complex")

    if _is_external_actor_name(lowered_name):
        return ActorItem(name=_title_case_name(cleaned_name), complexity="simple")

    # Actor kiểu database/file/protocol/text interface theo chuẩn UCP sẽ là average.
    if _looks_like_interface_actor_name(lowered_name):
        return ActorItem(name=_title_case_name(cleaned_name), complexity="average")

    # Nếu chưa match rule mạnh, thử giữ complexity gốc nếu nó hợp lệ.
    normalized_complexity = _normalize_complexity(complexity)
    if normalized_complexity in ALLOWED_COMPLEXITIES:
        return ActorItem(name=_title_case_name(cleaned_name), complexity=normalized_complexity)

    # Fallback cuối cùng: nếu nhìn giống tên role nghiệp vụ thì xem như human actor.
    if _looks_like_role_name(lowered_name):
        return ActorItem(name=_title_case_name(cleaned_name), complexity="complex")

    return None


def _normalize_use_case_item(
    name: str,
    complexity: str,
    description: str | None = None,
) -> UseCaseItem | None:
    """Chuẩn hóa một use case đơn lẻ."""
    cleaned_name = _clean_use_case_text(name)
    lowered_name = cleaned_name.lower()

    if not cleaned_name:
        return None

    # Internal step như "Send Reminder" hoặc "Validate Data"
    # không được tính là use case trong UCP.
    if _is_internal_step(lowered_name):
        return None

    # Nếu use case là sub-action thì merge về use case cha.
    # Ví dụ "update room availability" -> "Manage Room Information"
    merged_name = _apply_merge_rule(lowered_name)
    if merged_name is None and lowered_name in MERGE_RULES:
        return None
    if merged_name is not None:
        canonical_name = merged_name
    else:
        canonical_name = _extract_canonical_use_case_name(cleaned_name)

    # Loại các mảnh câu dài hoặc méo nghĩa trước khi đưa vào UCP.
    if not canonical_name or _looks_like_sentence_fragment(canonical_name):
        return None

    # Complexity cuối cùng ưu tiên rule classifier hơn là complexity thô từ extractor.
    inferred_complexity = _classify_use_case_complexity(canonical_name)
    normalized_complexity = _normalize_complexity(complexity)
    # Nếu use case đi từ template có description đi kèm,
    # ưu tiên complexity đã được tính từ Main Flow / Alternative Flow.
    if description and normalized_complexity:
        final_complexity = normalized_complexity
    else:
        final_complexity = inferred_complexity or normalized_complexity or "average"

    return UseCaseItem(
        name=canonical_name,
        complexity=final_complexity,
        description=description,
    )


def _extract_canonical_use_case_name(raw_name: str) -> str:
    """Rút gọn về tên use case dạng verb + noun và giữ noun theo domain."""
    cleaned_name = _clean_use_case_text(raw_name)
    lowered_name = cleaned_name.lower()

    # Một vài trường hợp được chuẩn hóa thủ công để tên nhìn đẹp hơn khi demo.
    if lowered_name == "pay":
        return "Pay Online"

    if "add to cart" in lowered_name or ("add" in lowered_name and "shopping cart" in lowered_name):
        return "Add To Cart"

    if "make payment" in lowered_name or lowered_name == "payment":
        return "Make Payment"

    # Tìm cụm động từ chuẩn dài nhất trước để tăng độ chính xác.
    phrase_patterns = sorted(VERB_CANONICAL_MAP.keys(), key=len, reverse=True)
    matched_phrase = None

    for phrase in phrase_patterns:
        if re.search(rf"\b{re.escape(phrase)}\b", lowered_name):
            matched_phrase = phrase
            break

    # Nếu không tìm được verb chuẩn:
    # - cho phép giữ lại cụm ngắn <= 4 từ
    # - còn lại thì loại bỏ vì dễ là sentence fragment
    if matched_phrase is None:
        if len(cleaned_name.split()) <= 4:
            return _title_case_name(cleaned_name)
        return ""

    canonical_verb = VERB_CANONICAL_MAP[matched_phrase]
    # Remainder là phần noun/domain object phía sau verb.
    remainder = re.sub(rf"^.*?\b{re.escape(matched_phrase)}\b", "", cleaned_name, flags=re.IGNORECASE)
    remainder = normalize_name(remainder)
    remainder = ARTICLE_PATTERN.sub("", remainder)
    remainder = _trim_leading_filler_words(remainder)
    remainder = _trim_trailing_filler_words(remainder)

    if canonical_verb in {"Login", "Logout", "Register"} and not remainder:
        return canonical_verb

    if canonical_verb == "Pay" and not remainder:
        return "Pay Online"

    if canonical_verb == "Make Payment":
        return "Make Payment"

    if remainder:
        return f"{canonical_verb} {_title_case_name(remainder)}"

    return canonical_verb


def _classify_use_case_complexity(name: str) -> str:
    """Phân loại complexity của use case bằng rule-based scoring.

    Quy tắc ưu tiên:
    - complex override average
    - average override simple

    Mapping điểm:
    - score 1 -> simple
    - score 2 -> average
    - score 3 -> complex
    """
    lowered_name = name.lower()

    # Rule ưu tiên cao nhất:
    # use case giao dịch nhiều bước như book/reserve/borrow/place order
    # sẽ được xếp complex trước.
    if _looks_like_transactional_workflow(lowered_name):
        return "complex"

    # Sau đó mới kiểm tra prefix tường minh.
    for prefix in COMPLEX_USE_CASE_PREFIXES:
        if lowered_name.startswith(prefix.lower()):
            return "complex"

    for prefix in SIMPLE_USE_CASE_PREFIXES:
        if lowered_name.startswith(prefix.lower()):
            return "simple"

    for prefix in AVERAGE_USE_CASE_PREFIXES:
        if lowered_name.startswith(prefix.lower()):
            return "average"

    # Nếu không match prefix, fallback sang cơ chế chấm điểm đơn giản.
    score = _score_use_case_complexity(lowered_name)

    if score >= 3:
        return "complex"
    if score >= 2:
        return "average"
    return "simple"


def _looks_like_transactional_workflow(lowered_name: str) -> bool:
    """Nhận diện use case dạng giao dịch nhiều bước.

    Các action như book, reserve, borrow, enroll, place order, transfer, checkout
    thường kéo theo nhiều bước xử lý nên được ưu tiên xếp complex.

    Rule này được ưu tiên chạy sớm để:
    - tránh việc "Transfer Money" bị rơi xuống nhóm average
    - đảm bảo các transactional workflow luôn được xếp đúng là complex
    """
    transactional_prefixes = (
        "transfer",
        "send money",
        "book",
        "reserve",
        "borrow",
        "enroll",
        "place order",
        "checkout",
        "schedule",
        "manage",
        "manage account",
        "manage information",
    )
    return any(
        lowered_name == prefix or lowered_name.startswith(f"{prefix} ")
        for prefix in transactional_prefixes
    )


def _score_use_case_complexity(lowered_name: str) -> int:
    """Tính điểm complexity theo action keyword.

    Rule:
    - view/search/check/display -> 1
    - update/confirm/approve/register/payment -> 2
    - transfer/book/borrow/order/manage/reserve/schedule -> 3
    """
    # Score 3 được ưu tiên vì complex override average/simple.
    if _contains_action_keyword(lowered_name, COMPLEX_USE_CASE_ACTION_KEYWORDS):
        return 3

    if _contains_action_keyword(lowered_name, AVERAGE_USE_CASE_ACTION_KEYWORDS):
        return 2

    if _contains_action_keyword(lowered_name, SIMPLE_USE_CASE_ACTION_KEYWORDS):
        return 1

    return 2


def _apply_merge_rule(lowered_name: str) -> str | None:
    """Áp dụng merge rule cho các sub-action."""
    # Ưu tiên merge rule khai báo tường minh trong mapping_config.
    for source_text, target_name in MERGE_RULES.items():
        if source_text in lowered_name:
            return target_name

    # Nếu không có rule tường minh thì thử merge bằng heuristic tổng quát.
    generic_merge_target = _resolve_generic_manage_merge(lowered_name)
    if generic_merge_target is not None:
        return generic_merge_target

    return None


def _clean_actor_name(name: str) -> str:
    """Làm sạch actor name."""
    cleaned_name = normalize_name(name)
    cleaned_name = ARTICLE_PATTERN.sub("", cleaned_name)
    cleaned_name = re.sub(r"^(external)\s+", "", cleaned_name, flags=re.IGNORECASE)
    cleaned_name = cleaned_name.strip(" .,:;")
    return cleaned_name


def _clean_use_case_text(name: str) -> str:
    """Làm sạch raw use case text."""
    cleaned_name = normalize_name(name)
    cleaned_name = re.sub(r"^(to)\s+", "", cleaned_name, flags=re.IGNORECASE)
    cleaned_name = re.sub(r"^(the|a|an)\s+", "", cleaned_name, flags=re.IGNORECASE)
    cleaned_name = re.sub(r"\b(after|before|when|if)\b.*$", "", cleaned_name, flags=re.IGNORECASE)
    cleaned_name = cleaned_name.strip(" .,:;")
    return cleaned_name


def _normalize_complexity(value: str | None) -> str | None:
    """Đưa complexity về lowercase."""
    if value is None:
        return None
    cleaned_value = value.strip().lower()
    if cleaned_value in ALLOWED_COMPLEXITIES:
        return cleaned_value
    return None


def _is_human_actor_name(lowered_name: str) -> bool:
    """Kiểm tra actor có thuộc nhóm human hay không."""
    return any(
        re.search(rf"\b{re.escape(keyword)}\b", lowered_name)
        for keyword in HUMAN_ACTOR_KEYWORDS
    )


def _is_external_actor_name(lowered_name: str) -> bool:
    """Kiểm tra actor có thuộc nhóm external system hay không."""
    if any(
        re.search(rf"\b{re.escape(keyword)}\b", lowered_name)
        for keyword in EXTERNAL_ACTOR_KEYWORDS
    ):
        return True

    fallback_keywords = ("service", "api", "gateway", "provider")
    return any(keyword in lowered_name for keyword in fallback_keywords)


def _looks_like_interface_actor_name(lowered_name: str) -> bool:
    """Nhận diện actor kiểu protocol/file/database/text interface.

    Các actor này theo chuẩn UCP thường được xếp average,
    nên không được loại bỏ chỉ vì tên có chứa "database" hay "file".
    """
    interface_keywords = ("database", "db", "file", "protocol", "text", "csv", "excel")
    return any(keyword in lowered_name for keyword in interface_keywords)


def _looks_like_role_name(lowered_name: str) -> bool:
    """Fallback cho role chưa có trong danh sách keyword."""
    words = lowered_name.split()
    if not words or len(words) > 3:
        return False

    if any(word in IGNORE_AS_ACTOR for word in words):
        return False

    return any(word.endswith(suffix) for word in words for suffix in ROLE_LIKE_SUFFIXES)


def _is_internal_step(lowered_name: str) -> bool:
    """Loại bỏ internal step."""
    # Ngoại lệ cho domain banking:
    # "Send Money" là business use case hợp lệ, không phải notification nội bộ.
    if any(
        lowered_name == phrase or lowered_name.startswith(f"{phrase} ")
        for phrase in VALID_TRANSACTIONAL_SEND_PHRASES
    ):
        return False

    # Danh sách loại trừ cố định cho các tác vụ nền.
    if any(exclusion in lowered_name for exclusion in INTERNAL_STEP_EXCLUSIONS):
        return True

    # Các từ send/notify/reminder/alert thường là hành vi tự động của hệ thống.
    # Tuy nhiên rule ngoại lệ phía trên sẽ giữ lại các use case banking hợp lệ.
    if any(keyword in lowered_name for keyword in ("send", "notify", "reminder", "alert")):
        return True

    if "confirmation" in lowered_name and ("system" in lowered_name or "service" in lowered_name):
        return True

    if lowered_name.startswith("system "):
        return True

    return False


def _looks_like_sentence_fragment(name: str) -> bool:
    """Loại bỏ sentence fragment không phải functional name."""
    lowered_name = name.lower()
    if lowered_name.startswith(("the ", "after ", "when ", "if ", "system ")):
        return True
    if " allows " in lowered_name or " successful order " in lowered_name:
        return True
    return False


def _is_background_processing_sentence(sentence: str) -> bool:
    """Loại câu mô tả hành vi nền của system/service."""
    lowered_sentence = sentence.lower()

    # Ví dụ bị loại:
    # - "The system sends confirmation"
    # - "Email Service notifies user"
    # Đây là hành vi nền, không phải use case do actor theo đuổi.
    if BACKGROUND_SUBJECT_ACTION_PATTERN.search(sentence):
        return True

    if lowered_sentence.startswith("after ") and any(
        keyword in lowered_sentence for keyword in ("send", "notify", "reminder", "alert", "confirmation")
    ):
        return True

    return False


def _trim_trailing_filler_words(text: str) -> str:
    """Bỏ filler word ở cuối để tên use case gọn hơn."""
    words = text.split()
    while words and words[-1].lower() in TRAILING_USE_CASE_FILLER_WORDS:
        words.pop()
    return " ".join(words)


def _trim_leading_filler_words(text: str) -> str:
    """Bỏ filler word ở đầu phần noun."""
    words = text.split()
    while words and words[0].lower() in TRAILING_USE_CASE_FILLER_WORDS:
        words.pop(0)
    return " ".join(words)


def _standardize_use_case_name(name: str | None) -> str:
    """Chuẩn hóa tên use case về dạng dễ đọc và nhất quán."""
    if not name:
        return ""

    cleaned_name = normalize_name(name)
    cleaned_name = cleaned_name.strip(" .,:;")

    if not cleaned_name:
        return ""

    return _title_case_name(cleaned_name)


def _standardize_actor_label(actor_name: str | None) -> str | None:
    """Chuẩn hóa tên actor để dùng ổn định trong parser/classifier."""
    if not actor_name:
        return None

    cleaned_name = normalize_name(actor_name).strip(" .,:;")
    if not cleaned_name:
        return None

    if cleaned_name.lower() == "admin":
        return "Administrator"

    words: list[str] = []
    for word in cleaned_name.split():
        lowered_word = word.lower()
        if lowered_word == "api":
            words.append("API")
        elif lowered_word == "db":
            words.append("DB")
        else:
            words.append(word.capitalize())

    return " ".join(words)


def _clean_optional_multiline_text(value: str | None) -> str | None:
    """Làm sạch field text nhiều dòng."""
    if not value:
        return None

    cleaned_lines = [normalize_name(line) for line in value.splitlines() if normalize_name(line)]
    if not cleaned_lines:
        return None

    return "\n".join(cleaned_lines)


def _clean_step_list(steps: list[str]) -> list[str]:
    """Làm sạch danh sách bước trong flow."""
    cleaned_steps: list[str] = []

    for step in steps:
        cleaned_step = normalize_name(step)
        cleaned_step = re.sub(r"^\s*(?:\d+[\.\)]|[A-Za-z][\.\)]|[-*•])\s*", "", cleaned_step)
        cleaned_step = cleaned_step.strip(" .:-")
        if not cleaned_step:
            continue
        cleaned_steps.append(cleaned_step)

    return cleaned_steps


def _split_actor_names_from_single_field(value: str) -> list[str]:
    """Tách một field actor bị gộp nhiều actor."""
    parts = re.split(r",| and | & |;", value, flags=re.IGNORECASE)
    return [
        standardized_name
        for part in parts
        if (standardized_name := _standardize_actor_label(part)) is not None
    ]


def _deduplicate_names(values: list[str]) -> list[str]:
    """Loại phần tử trùng nhưng vẫn giữ thứ tự ban đầu."""
    seen: set[str] = set()
    unique_values: list[str] = []

    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_values.append(value)

    return unique_values


def _title_case_name(name: str) -> str:
    """Title Case đơn giản cho tên actor/use case."""
    formatted_words: list[str] = []

    for word in normalize_name(name).split():
        lowered_word = word.lower()
        if lowered_word in {"api", "db", "erp", "crm", "sms"}:
            formatted_words.append(lowered_word.upper())
        else:
            formatted_words.append(word.capitalize())

    return " ".join(formatted_words)


def _contains_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    """Kiểm tra text có chứa một keyword hoặc phrase nào đó hay không."""
    return any(re.search(rf"\b{re.escape(keyword)}\b", text) for keyword in keywords)


def _contains_action_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    """Kiểm tra action keyword ở đầu use case để tránh nhầm noun của domain.

    Ví dụ:
    - "Book Rooms" -> match action "book"
    - "View Book Details" -> không match action "book"
    """
    return any(text == keyword or text.startswith(f"{keyword} ") for keyword in keywords)


def _deduplicate_actors(actors: Iterable[ActorItem]) -> list[ActorItem]:
    """Gộp actor trùng theo tên và giữ actor cụ thể hơn.

    Ví dụ:
    - Manager + Hotel Manager -> giữ Hotel Manager
    - Manager + Education Manager -> giữ Education Manager
    """
    unique_items: list[ActorItem] = []

    for actor in actors:
        replaced_existing = False
        skip_current = False

        for index, existing_actor in enumerate(unique_items):
            # Nếu trùng tên hoàn toàn thì bỏ actor đến sau.
            if actor.name.lower() == existing_actor.name.lower():
                skip_current = True
                break

            # Nếu actor mới cụ thể hơn actor cũ thì thay actor cũ.
            if _is_more_specific_name(actor.name, existing_actor.name):
                unique_items[index] = actor
                replaced_existing = True
                break

            # Nếu actor cũ đã cụ thể hơn actor mới thì bỏ actor mới.
            if _is_more_specific_name(existing_actor.name, actor.name):
                skip_current = True
                break

        if skip_current:
            continue

        if not replaced_existing:
            unique_items.append(actor)

    return unique_items


def _deduplicate_use_cases(use_cases: Iterable[UseCaseItem]) -> list[UseCaseItem]:
    """Gộp use case trùng theo tên."""
    seen: set[str] = set()
    unique_items: list[UseCaseItem] = []

    for use_case in use_cases:
        key = use_case.name.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(use_case)

    return unique_items


def _resolve_generic_manage_merge(lowered_name: str) -> str | None:
    """Merge các sub-action update/edit/delete về manage use case phù hợp."""
    if not lowered_name.startswith(("update ", "edit ", "delete ")):
        return None

    if any(keyword in lowered_name for keyword in ("room availability", "room information", "room details")):
        return "Manage Room Information"

    if any(keyword in lowered_name for keyword in ("book inventory", "book information", "book details")):
        return "Manage Book Information"

    if any(keyword in lowered_name for keyword in ("guest record", "guest information", "customer record", "customer information")):
        return "Manage Customer Records"

    if any(keyword in lowered_name for keyword in ("reservation", "booking")):
        return "Manage Reservations"

    if any(keyword in lowered_name for keyword in ("assignment", "assignment details")):
        return "Manage Assignments"

    return None


def _is_more_specific_name(candidate_name: str, existing_name: str) -> bool:
    """Kiểm tra tên candidate có cụ thể hơn tên existing hay không."""
    candidate_words = candidate_name.lower().split()
    existing_words = existing_name.lower().split()

    if candidate_name.lower() == existing_name.lower():
        return False

    if len(candidate_words) <= len(existing_words):
        return False

    return all(word in candidate_words for word in existing_words)
