from backend.app.config import settings

# Реэкспорт конфига для бота (единый источник)
BOT_TOKEN = settings.bot_token
DATABASE_URL = settings.database_url
REDIS_URL = settings.redis_url
WEBAPP_URL = settings.webapp_url
LOG_LEVEL = settings.log_level
