from backend.app.config import settings

# Реэкспорт конфига для бота (единый источник)
BOT_TOKEN = settings.bot_token
DATABASE_URL = settings.database_url
REDIS_URL = settings.redis_url
WEBAPP_URL = settings.webapp_url
LOG_LEVEL = settings.log_level

# Webhook
USE_WEBHOOK = settings.use_webhook
WEBHOOK_URL = settings.bot_webhook_url
WEBHOOK_PATH = settings.webhook_path
WEBHOOK_PORT = settings.webhook_port
WEBHOOK_SECRET = settings.webhook_secret
