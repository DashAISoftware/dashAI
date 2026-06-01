from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MultilingualString:
    en: str
    es: Optional[str] = None
    pt: Optional[str] = None
    de: Optional[str] = None
    zh: Optional[str] = None

    def get(self, lang: str) -> str:
        # Normalize: "zh-CN" → "zh", "zh,zh;q=0.9" → "zh"
        lang = lang.split(",")[0].split(";")[0].split("-")[0].strip()
        if lang == "es" and self.es:
            return self.es
        if lang == "pt" and self.pt:
            return self.pt
        if lang == "de" and self.de:
            return self.de
        if lang == "zh" and self.zh:
            return self.zh
        return self.en
