"""
Сервис для отправки уведомлений пользователям
"""
from datetime import datetime, timezone, timedelta
import logging

from aiogram import Bot
from repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


def parse_timezone_offset(offset_str: str) -> float:
    """Парсит строку часового пояса в число часов"""
    if not offset_str:
        return 0.0
    
    sign = 1 if offset_str[0] == '+' else -1
    hours = int(offset_str[1:3])
    minutes = int(offset_str[4:6]) if len(offset_str) > 4 else 0
    return sign * (hours + minutes / 60)


class NotificationService:
    """Сервис для отправки уведомлений"""
    
    @staticmethod
    async def send_notification(bot: Bot, user_id: int, message: str):
        """Отправляет уведомление пользователю"""
        try:
            logger.debug(f"📤 Попытка отправить уведомление пользователю {user_id}...")
            await bot.send_message(chat_id=user_id, text=message)
            logger.info(f"✅ Уведомление успешно отправлено пользователю {user_id}")
        except Exception as e:
            # Пользователь мог заблокировать бота или удалить чат
            error_msg = str(e)[:100]
            logger.warning(f"⚠️  Не удалось отправить уведомление пользователю {user_id}: {error_msg}")
    
    @staticmethod
    async def send_notifications_job(bot: Bot, target_hour: int, message: str):
        """Отправляет уведомления всем пользователям, у которых наступило указанное время"""
        time_label = "утренние" if target_hour == 9 else "вечерние"
        logger.info(f"🔄 Начало обработки {time_label} уведомлений (целевой час: {target_hour}:00)...")
        
        try:
            # Получаем текущее время в UTC
            now_utc = datetime.now(timezone.utc)
            logger.debug(f"🕐 Текущее время UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Получаем всех пользователей
            logger.info("📊 Получение списка пользователей из базы данных...")
            try:
                users = UserRepository.get_all_with_timezone()
                logger.info(f"✅ Получено {len(users)} пользователей из базы данных")
            except Exception as db_error:
                logger.error(f"❌ Ошибка базы данных при получении пользователей: {db_error}")
                return
            
            if not users:
                logger.info("ℹ️  Пользователи не найдены, уведомления не требуются")
                return
            
            sent_count = 0
            checked_count = 0
            skipped_no_timezone = 0
            
            logger.info(f"🔍 Проверка времени для {len(users)} пользователей...")
            
            for user in users:
                if not user.timezone_offset:
                    skipped_no_timezone += 1
                    continue
                
                try:
                    # Парсим часовой пояс
                    offset_hours = parse_timezone_offset(user.timezone_offset)
                    user_tz = timezone(timedelta(hours=offset_hours))
                    
                    # Вычисляем текущее время в часовом поясе пользователя
                    now_user_tz = now_utc.astimezone(user_tz)
                    user_hour = now_user_tz.hour
                    user_minute = now_user_tz.minute
                    checked_count += 1
                    
                    logger.debug(f"👤 Пользователь {user.user_id}: часовой пояс {user.timezone_offset}, локальное время {now_user_tz.strftime('%H:%M')}")
                    
                    # Проверяем, что наступило нужное время (в пределах первых 5 минут часа)
                    if user_hour == target_hour and user_minute < 5:
                        logger.info(f"⏰ Время для уведомления пользователя {user.user_id} (локальное время: {user_hour}:{user_minute:02d})")
                        await NotificationService.send_notification(bot, user.user_id, message)
                        sent_count += 1
                    else:
                        logger.debug(f"⏭️  Пропуск пользователя {user.user_id} (локальное время: {user_hour}:{user_minute:02d}, требуется {target_hour}:00)")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки пользователя {user.user_id}: {e}")
                    continue
            
            # Итоговая статистика
            logger.info("=" * 60)
            logger.info(f"📊 Итоги обработки {time_label} уведомлений:")
            logger.info(f"   • Всего пользователей в базе: {len(users)}")
            logger.info(f"   • Пропущено без часового пояса: {skipped_no_timezone}")
            logger.info(f"   • Проверено пользователей: {checked_count}")
            logger.info(f"   • Отправлено уведомлений: {sent_count}")
            logger.info("=" * 60)
            
            if sent_count > 0:
                logger.info(f"✅ Успешно отправлено {sent_count} {time_label} уведомлений")
            else:
                logger.info(f"ℹ️  Уведомления не требовались (ни у одного пользователя не наступило {target_hour}:00)")
                
        except Exception as e:
            logger.error(f"❌ Критическая ошибка в задаче {time_label} уведомлений: {e}", exc_info=True)
    
    @staticmethod
    async def send_evening_notifications(bot: Bot):
        """Отправляет вечерние уведомления в 22:00"""
        logger.info("🌙 Запуск отправки вечерних уведомлений (22:00)...")
        await NotificationService.send_notifications_job(bot, 22, "Пора отметить выполненные задачи")
        logger.info("✅ Процесс отправки вечерних уведомлений завершен")
    
    @staticmethod
    async def send_morning_notifications(bot: Bot):
        """Отправляет утренние уведомления в 9:00"""
        logger.info("🌅 Запуск отправки утренних уведомлений (9:00)...")
        await NotificationService.send_notifications_job(bot, 9, "Хорошего дня!")
        logger.info("✅ Процесс отправки утренних уведомлений завершен")

