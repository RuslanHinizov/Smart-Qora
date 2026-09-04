from typing import Literal

Language = Literal["ru", "kk", "en", "tr"]
SUPPORTED_LANGUAGES: tuple[Language, ...] = ("ru", "kk", "en", "tr")

MESSAGES = {
    "ru": {"not_found": "Не найдено", "camera_created": "Камера создана", "camera_deleted": "Камера удалена"},
    "kk": {"not_found": "Табылмады", "camera_created": "Камера құрылды", "camera_deleted": "Камера жойылды"},
    "en": {"not_found": "Not found", "camera_created": "Camera created", "camera_deleted": "Camera deleted"},
    "tr": {"not_found": "Bulunamadı", "camera_created": "Kamera oluşturuldu", "camera_deleted": "Kamera silindi"},
}


def normalize_language(value: str | None, default: Language = "ru") -> Language:
    if value:
        code = value.split(",", 1)[0].split("-", 1)[0].lower().strip()
        if code in SUPPORTED_LANGUAGES:
            return code  # type: ignore[return-value]
    return default


def translate(key: str, language: Language = "ru") -> str:
    return MESSAGES.get(language, MESSAGES["ru"]).get(key, key)
