"""Korean UI strings."""

STRINGS = {
    # Page titles
    "page_title": "Kompline - 알고리즘 공정성 검증 시스템",
    "page_subtitle": "금융상품 비교·추천 알고리즘 감사 자동화",

    # Sidebar
    "settings": "설정",
    "use_api_server": "API 서버 사용",
    "api_connected": "API 연결됨",
    "api_error": "API 연결 실패",
    "api_start_hint": "서버 시작: `uvicorn api.main:app --port 8888`",
    "use_llm": "LLM 평가 사용",
    "enable_hitl": "검토자 확인 활성화",
    "show_logs": "실시간 로그 표시",

    # Source code input
    "source_input": "소스코드 입력",
    "compliance_selection": "감사 규정 선택",
    "sample_code": "샘플 코드",
    "load_compliant": "규정 준수 코드 불러오기",
    "load_noncompliant": "규정 위반 코드 불러오기",

    # GitHub integration
    "github_import": "GitHub 저장소 가져오기",
    "github_url": "GitHub URL",
    "github_url_placeholder": "https://github.com/owner/repo",
    "github_branch": "브랜치",
    "github_load": "저장소 불러오기",
    "github_loading": "저장소에서 파일을 가져오는 중...",
    "github_files_found": "Python 파일 {count}개 발견",
    "github_select_files": "감사할 파일 선택",

    # Project upload
    "project_upload": "프로젝트 업로드",
    "upload_files": ".py 파일 업로드",
    "upload_hint": "여러 파일을 한번에 업로드할 수 있습니다",

    # Analysis
    "start_analysis": "감사 시작",
    "analyzing": "분석 중...",
    "analysis_results": "감사 결과",

    # Results
    "compliant": "규정 준수",
    "non_compliant": "규정 위반 발견",
    "status_unknown": "상태: 알 수 없음",
    "total_passed": "통과",
    "total_failed": "위반",
    "total_review": "검토 필요",

    # Detailed findings
    "detailed_findings": "세부 감사 결과",
    "rule": "규칙",
    "status": "상태",
    "confidence": "신뢰도",
    "reasoning": "판단 근거",
    "recommendation": "권고사항",

    # User confirmation
    "mapping_confirmation": "감사 결과 매핑 확인",
    "mapping_instruction": "AI가 분석한 결과가 실제 감사 기준과 올바르게 매핑되었는지 확인해주세요.",
    "confirm_mapping": "매핑 확인 완료",
    "reject_mapping": "매핑 수정 필요",
    "mapping_comment": "의견 또는 수정사항",
    "mapping_confirmed": "매핑이 확인되었습니다",
    "mapping_rejected": "매핑 수정이 필요합니다. 의견을 검토 후 재분석합니다.",

    # HITL
    "pending_reviews": "검토 대기 항목",
    "review_needed": "검토 필요",

    # Report
    "report": "감사 보고서",
    "export_report": "보고서 내보내기",

    # Logs
    "agent_activity": "에이전트 활동 로그",

    # Footer
    "footer": "Kompline v0.1.0 | 알고리즘 공정성 자가평가 자동화 시스템",

    # Errors
    "error_no_input": "소스코드를 입력하거나 파일을 업로드해주세요",
    "error_api_connect": "API 서버에 연결할 수 없습니다",
    "error_analysis_failed": "분석 실패",

    # Tabs
    "tab_direct": "직접 입력",
    "tab_github": "GitHub 가져오기",
    "tab_upload": "파일 업로드",

    # Compliance names
    "compliance_algorithm_fairness": "알고리즘 공정성",
    "compliance_pipa": "개인정보보호법",
}
