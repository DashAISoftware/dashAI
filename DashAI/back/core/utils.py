from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MultilingualString:
    en: str
    es: Optional[str] = None

    def get(self, lang: str) -> str:
        if lang == "es" and self.es:
            return self.es
        return self.en
