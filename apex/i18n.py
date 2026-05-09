"""Localized UI - Multi-language support for APEX."""

import os


LOCALES = {
    "en": {
        "app_name": "APEX",
        "welcome": "Welcome to APEX - The last coding agent you'll ever need",
        "prompt": ">>> ",
        "thinking": "Thinking...",
        "working": "Working...",
        "done": "Done!",
        "error": "Error",
        "success": "Success",
        "help_title": "Available Commands",
        "model": "Model",
        "agent": "Agent",
        "cwd": "Working Directory",
        "clear": "Clear history",
        "sessions": "Sessions",
        "agents": "Agents",
        "help": "Show this help message",
        "quit": "Exit APEX",
    },
    "ja": {
        "app_name": "APEX",
        "welcome": "APEXへようこそ - 最後のコーディングエージェント",
        "prompt": ">>> ",
        "thinking": "思考中...",
        "working": "実行中...",
        "done": "完了!",
        "error": "エラー",
        "success": "成功",
        "help_title": "利用可能なコマンド",
        "model": "モデル",
        "agent": "エージェント",
        "cwd": "作業ディレクトリ",
        "clear": "履歴をクリア",
        "sessions": "セッション",
        "agents": "エージェント",
        "help": "このヘルプメッセージを表示",
        "quit": "APEXを終了",
    },
    "zh-Hans": {
        "app_name": "APEX",
        "welcome": "欢迎使用APEX - 最后的编码助手",
        "prompt": ">>> ",
        "thinking": "思考中...",
        "working": "工作中...",
        "done": "完成!",
        "error": "错误",
        "success": "成功",
        "help_title": "可用命令",
        "model": "模型",
        "agent": "代理",
        "cwd": "工作目录",
        "clear": "清除历史",
        "sessions": "会话",
        "agents": "代理",
        "help": "显示帮助信息",
        "quit": "退出APEX",
    },
    "pt-BR": {
        "app_name": "APEX",
        "welcome": "Bem-vindo ao APEX - O último agente de codificação que você precisará",
        "prompt": ">>> ",
        "thinking": "Pensando...",
        "working": "Trabalhando...",
        "done": "Concluído!",
        "error": "Erro",
        "success": "Sucesso",
        "help_title": "Comandos Disponíveis",
        "model": "Modelo",
        "agent": "Agente",
        "cwd": "Diretório de Trabalho",
        "clear": "Limpar histórico",
        "sessions": "Sessões",
        "agents": "Agentes",
        "help": "Mostrar esta mensagem de ajuda",
        "quit": "Sair do APEX",
    },
}


def detect_locale() -> str:
    """Auto-detect locale from environment."""
    lang = os.environ.get("LANG", "")
    if not lang:
        return "en"
    
    lang = lang.split(".")[0].lower()
    
    if "ja" in lang:
        return "ja"
    if "zh" in lang:
        return "zh-Hans"
    if "pt" in lang:
        return "pt-BR"
    
    return "en"


class I18n:
    """Internationalization support for APEX."""

    def __init__(self, locale: str = "auto"):
        if locale == "auto":
            locale = detect_locale()
        
        self.locale = locale if locale in LOCALES else "en"
        self._strings = LOCALES[self.locale]

    def get(self, key: str, default: str = "") -> str:
        """Get translated string."""
        return self._strings.get(key, default)

    def __getitem__(self, key: str) -> str:
        """Get translated string using bracket notation."""
        return self.get(key, key)

    def __contains__(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._strings

    @property
    def available_locales(self) -> list[str]:
        """List available locales."""
        return list(LOCALES.keys())


_i18n_instance = None


def get_i18n(locale: str = "auto") -> I18n:
    """Get global i18n instance."""
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = I18n(locale)
    return _i18n_instance


def set_locale(locale: str) -> None:
    """Set global locale."""
    global _i18n_instance
    _i18n_instance = I18n(locale)