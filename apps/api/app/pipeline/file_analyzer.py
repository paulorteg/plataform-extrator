from dataclasses import dataclass


@dataclass(frozen=True)
class FileAnalysisResult:
    file_type: str
    page_count: int
    is_scanned: bool
    ocr_required: bool
    text_extractable: bool


class FileAnalyzer:
    def analyze(
        self,
        *,
        content: bytes,
        content_type: str,
        filename: str = "",
    ) -> FileAnalysisResult:
        lower_filename = filename.lower()
        if content_type == "application/pdf" or lower_filename.endswith(".pdf"):
            page_count = max(content.count(b"/Type /Page"), 1)
            has_text_signal = (
                b"BT" in content
                or b"/Font" in content
                or b"BOLETIM" in content.upper()
            )
            return FileAnalysisResult(
                file_type="pdf",
                page_count=page_count,
                is_scanned=not has_text_signal,
                ocr_required=not has_text_signal,
                text_extractable=has_text_signal,
            )
        if (
            content_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            or lower_filename.endswith(".docx")
        ):
            return FileAnalysisResult(
                file_type="docx",
                page_count=1,
                is_scanned=False,
                ocr_required=False,
                text_extractable=True,
            )
        if content_type.startswith("image/"):
            return FileAnalysisResult(
                file_type="image",
                page_count=1,
                is_scanned=True,
                ocr_required=True,
                text_extractable=False,
            )
        return FileAnalysisResult(
            file_type="unknown",
            page_count=1,
            is_scanned=False,
            ocr_required=False,
            text_extractable=False,
        )
