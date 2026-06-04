import re


SECTION_PATTERNS = {
    "boletim": re.compile(r"\b(?:BOLETIM|BO\s*(?:N[ºO.]|NUMERO|NÚMERO))\b", re.IGNORECASE),
    "evento": re.compile(r"\b(?:FATO|EVENTO|NATUREZA|OCORR[ÊE]NCIA)\b", re.IGNORECASE),
    "motorista": re.compile(r"\b(?:MOTORISTA|CONDUTOR)\b", re.IGNORECASE),
    "veiculo": re.compile(r"\b(?:VE[IÍ]CULO|PLACA|RENAVAM|CHASSI)\b", re.IGNORECASE),
    "carga": re.compile(r"\b(?:MERCADORIA|CARGA|OBJETO MATERIAL)\b", re.IGNORECASE),
    "empresa": re.compile(r"\b(?:V[IÍ]TIMA|EMPRESA|CNPJ|EMBARCADOR)\b", re.IGNORECASE),
}


class SectionDetectorV1:
    def detect(self, text: str) -> dict[str, bool]:
        return {
            section_key: bool(pattern.search(text))
            for section_key, pattern in SECTION_PATTERNS.items()
        }
