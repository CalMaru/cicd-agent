from enum import Enum


class TaskType(str, Enum):
    API_DESIGN = "api_design"
    DEPLOYMENT_CHECKLIST = "deployment_checklist"
    CODE_REVIEW = "code_review"
    ERROR_ANALYSIS = "error_analysis"


def classify_task(user_input: str) -> TaskType:
    """
    사용자 입력을 분석하여 태스크 유형을 결정한다.

    키워드 기반 분류:
    - api, endpoint, 명세, 스키마 → api_design
    - 배포, deploy, checklist, 롤백 → deployment_checklist
    - 리뷰, review, 코드 → code_review
    - 에러, error, 버그, 의존성 → error_analysis
    """
    lower = user_input.lower()

    keywords = {
        TaskType.API_DESIGN: ["api", "endpoint", "명세", "스키마"],
        TaskType.DEPLOYMENT_CHECKLIST: ["배포", "deploy", "checklist", "롤백"],
        TaskType.CODE_REVIEW: ["리뷰", "review", "코드"],
        TaskType.ERROR_ANALYSIS: ["에러", "error", "버그", "의존성"],
    }

    for task_type, words in keywords.items():
        if any(word in lower for word in words):
            return task_type

    return TaskType.ERROR_ANALYSIS
