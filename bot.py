#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PRO OTC TRADING BOT
"""

import telebot
from telebot import types
import yfinance as yf
import sqlite3
from datetime import datetime, timedelta
import logging
import time
import os
from dataclasses import dataclass, field
from typing import List

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

@dataclass
class Config:
    TELEGRAM_TOKEN: str = os.environ.get('TELEGRAM_TOKEN', '8626772252:AAFPf3SiYDyBPSKIHeh-Ofg4BON_MLaIs1g')
    ADMIN_IDS: List[int] = field(default_factory=lambda: [123456789])
    WEBMONEY_Z: str = 'Z653554497387'
    WEBMONEY_X: str = 'X857242106275'
    PRICE_MONTHLY_USD: float = 35.00
    PRICE_QUARTERLY_USD: float = 95.00
    PRICE_YEARLY_USD: float = 299.00
    FREE_TRIAL_DAYS: int = 3
    DATABASE: str = 'trading_bot.db'
    SUPPORT_LINK: str = 'https://t.me/ArtemchkaaBro'

config = Config()

# ============================================
# ТАЙМФРЕЙМЫ
# ============================================

TIMEFRAMES = ['1s', '3s', '5s', '10s', '15s', '30s', '1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']

# ============================================
# OTC ИНСТРУМЕНТЫ
# ============================================

INSTRUMENTS = {
    'forex': ['EUR/USD (OTC)', 'GBP/USD (OTC)', 'USD/JPY (OTC)', 'USD/CHF (OTC)', 'AUD/USD (OTC)'],
    'crypto': ['BTC/USD (OTC)', 'ETH/USD (OTC)', 'BNB/USD (OTC)', 'SOL/USD (OTC)'],
    'commodities': ['XAU/USD (Золото OTC)', 'XAG/USD (Серебро OTC)'],
    'stocks': ['AAPL/USD (Apple OTC)', 'MSFT/USD (Microsoft OTC)'],
    'indices': ['SPX/USD (S&P 500 OTC)', 'DJI/USD (Dow Jones OTC)']
}

# ============================================
# ЛОГИРОВАНИЕ
# ============================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================
# КЭШ
# ============================================

price_cache = {}
cache_time = {}
CACHE_TTL = 10

# ============================================
# БАЗА ДАННЫХ
# ============================================

class Database:
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(config.DATABASE) as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                license_plan TEXT,
                license_expires TEXT,
                license_status TEXT,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                total_profit REAL DEFAULT 0
            )''')
            conn.commit()
    
    def get_user(self, telegram_id):
        with sqlite3.connect(config.DATABASE) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            row = c.fetchone()
            if row:
                return {
                    'telegram_id': row[0],
                    'username': row[1],
                    'first_name': row[2],
                    'license_plan': row[3],
                    'license_expires': row[4],
                    'license_status': row[5],
                    'total_trades': int(row[6]) if row[6] else 0,
                    'winning_trades': int(row[7]) if row[7] else 0,
                    'total_profit': float(row[8]) if row[8] else 0.0
                }
            return None
    
    def create_user(self, telegram_id, username, first_name):
        with sqlite3.connect(config.DATABASE) as conn:
            c = conn.cursor()
            existing = self.get_user(telegram_id)
            if existing:
                return existing
            
            expires = (datetime.now() + timedelta(days=config.FREE_TRIAL_DAYS)).isoformat()
            c.execute('''INSERT INTO users (telegram_id, username, first_name, license_plan, license_expires, license_status)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (telegram_id, username, first_name, 'trial', expires, 'active'))
            conn.commit()
            return self.get_user(telegram_id)
    
    def check_license(self, telegram_id):
        if telegram_id == 123456789:
            return {'valid': True, 'plan': 'admin', 'days_left': 9999}
        
        user = self.get_user(telegram_id)
        if not user:
            return {'valid': False, 'message': 'Пользователь не найден'}
        if user['license_status'] != 'active':
            return {'valid': False, 'message': 'Лицензия неактивна'}
        expires = datetime.fromisoformat(user['license_expires'])
        if expires < datetime.now():
            return {'valid': False, 'message': 'Лицензия истекла'}
        days_left = (expires - datetime.now()).days
        return {'valid': True, 'plan': user['license_plan'], 'days_left': days_left}
    
    def activate_license(self, telegram_id, plan):
        if plan == 'monthly':
            expires = datetime.now() + timedelta(days=30)
        elif plan == 'quarterly':
            expires = datetime.now() + timedelta(days=90)
        elif plan == 'yearly':
            expires = datetime.now() + timedelta(days=365)
        else:
            expires = datetime.now() + timedelta(days=config.FREE_TRIAL_DAYS)
        
        with sqlite3.connect(config.DATABASE) as conn:
            c = conn.cursor()
            c.execute('''UPDATE users SET license_plan = ?, license_expires = ?, license_status = 'active'
                         WHERE telegram_id = ?''', (plan, expires.isoformat(), telegram_id))
            conn.commit()
    
    def get_stats(self, telegram_id):
        user = self.get_user(telegram_id)
        if not user:
            return {'total_trades': 0, 'wins': 0, 'losses': 0, 'win_rate': 0, 'total_profit': 0}
        win_rate = (user['winning_trades'] / user['total_trades'] * 100) if user['total_trades'] > 0 else 0
        return {
            'total_trades': user['total_trades'],
            'wins': user['winning_trades'],
            'losses': user['total_trades'] - user['winning_trades'],
            'win_rate': win_rate,
            'total_profit': user['total_profit']
        }

db = Database()

# ============================================
# ИНДИКАТОРЫ
# ============================================

class Indicators:
    @staticmethod
    def calculate_rsi(prices, period=14):
        if len(prices) < period + 1:
            return 50
        gains, losses = [], []
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        avg_gain = sum(gains[-period:]) / period if gains else 0
        avg_loss = sum(losses[-period:]) / period if losses else 0
        if avg_loss == 0:
            return 100
        return 100 - (100 / (1 + (avg_gain / avg_loss)))
    
    @staticmethod
    def generate_signal(prices):
        if len(prices) < 30:
            return {'direction': 'WAIT', 'confidence': 0, 'reasons': [], 'current_price': prices[-1] if prices else 0, 'change': 0}
        
        rsi = Indicators.calculate_rsi(prices)
        current = prices[-1]
        prev = prices[-2]
        change = ((current - prev) / prev) * 100 if prev != 0 else 0
        
        confidence = 50
        reasons = []
        direction = 'WAIT'
        
        if rsi > 70:
            confidence += 15
            reasons.append(f"RSI перекуплен ({rsi:.1f})")
            direction = 'PUT'
        elif rsi < 30:
            confidence += 15
            reasons.append(f"RSI перепродан ({rsi:.1f})")
            direction = 'CALL'
        
        if change > 0.3:
            confidence += 10
            reasons.append(f"Рост {change:.2f}%")
            if direction == 'WAIT':
                direction = 'CALL'
        elif change < -0.3:
            confidence -= 10
            reasons.append(f"Падение {change:.2f}%")
            if direction == 'WAIT':
                direction = 'PUT'
        
        confidence = max(0, min(100, confidence))
        return {'direction': direction, 'confidence': confidence, 'reasons': reasons, 'current_price': current, 'change': change}

indicators = Indicators()

# ============================================
# ТОРГОВЫЙ ДВИЖОК
# ============================================

class TradingEngine:
    def get_price(self, symbol):
        cache_key = symbol
        if cache_key in price_cache and time.time() - cache_time.get(cache_key, 0) < CACHE_TTL:
            return price_cache[cache_key]
        
        try:
            clean = symbol.replace(' (OTC)', '').replace(' Золото', '').replace(' Серебро', '')
            
            if '/' in clean:
                if 'BTC' in clean or 'ETH' in clean:
                    yf_symbol = clean.replace('/', '') + '-USD'
                else:
                    yf_symbol = clean.replace('/', '') + '=X'
            else:
                yf_symbol = clean
            
            ticker = yf.Ticker(yf_symbol)
            data = ticker.history(period='1h', interval='1m')
            
            if not data.empty:
                prices = data['Close'].tolist()
                result = {
                    'prices': prices[-50:],
                    'current': prices[-1],
                    'high': data['High'].iloc[-1],
                    'low': data['Low'].iloc[-1]
                }
                price_cache[cache_key] = result
                cache_time[cache_key] = time.time()
                return result
            return None
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return None

engine = TradingEngine()

# ============================================
# TELEGRAM БОТ
# ============================================

bot = telebot.TeleBot(config.TELEGRAM_TOKEN)
user_settings = {}

def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add('📊 СИГНАЛ', '📈 СТАТИСТИКА')
    kb.add('🔧 ИНСТРУМЕНТ', '⏱️ ТАЙМФРЕЙМ')
    kb.add('🔑 ЛИЦЕНЗИЯ', '💳 КУПИТЬ')
    kb.add('❓ ПОМОЩЬ')
    return kb

@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    db.create_user(user.id, user.username, user.first_name)
    
    if user.id not in user_settings:
        user_settings[user.id] = {'instrument': 'EUR/USD (OTC)', 'timeframe': '5s'}
    
    license_info = db.check_license(user.id)
    
    text = f"""
🚀 *PRO OTC TRADING BOT*

Привет, {user.first_name}! 👋

✅ Таймфреймы от 1 секунды
✅ OTC инструменты
✅ Автоматические сигналы

━━━━━━━━━━━━━━━━━━━━━━
🔑 *ЛИЦЕНЗИЯ*
"""
    if license_info['valid']:
        if license_info['plan'] == 'admin':
            text += "\n👑 АДМИНИСТРАТОР - БЕССРОЧНО"
        else:
            text += f"\n✅ Активна ({license_info['plan']})\n⏰ Осталось: {license_info['days_left']} дней"
    else:
        text += f"\n❌ Неактивна\n🎁 Пробный период: {config.FREE_TRIAL_DAYS} дня"
    
    text += f"""
━━━━━━━━━━━━━━━━━━━━━━
⚙️ *НАСТРОЙКИ*
├ Инструмент: {user_settings[user.id]['instrument']}
└ Таймфрейм: {user_settings[user.id]['timeframe']}

👇 Выберите действие:
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == '📊 СИГНАЛ')
def signal(message):
    user_id = message.from_user.id
    
    license_check = db.check_license(user_id)
    if not license_check['valid']:
        bot.send_message(message.chat.id, f"❌ {license_check['message']}\n\nКупите лицензию: /buy", parse_mode='Markdown')
        return
    
    settings = user_settings.get(user_id, {'instrument': 'EUR/USD (OTC)', 'timeframe': '5s'})
    symbol = settings['instrument']
    timeframe = settings['timeframe']
    
    status_msg = bot.send_message(message.chat.id, f"🔍 *{symbol}* | {timeframe}\n└ ⏳ Загрузка...", parse_mode='Markdown')
    
    data = engine.get_price(symbol)
    
    if not data:
        bot.edit_message_text(f"❌ Ошибка: нет данных", message.chat.id, status_msg.message_id, parse_mode='Markdown')
        return
    
    signal_data = indicators.generate_signal(data['prices'])
    
    if signal_data['direction'] == 'CALL':
        color, action, emoji = "🟢", "ПОКУПКА (BUY) ✅", "📈"
    elif signal_data['direction'] == 'PUT':
        color, action, emoji = "🔴", "ПРОДАЖА (SELL) ❌", "📉"
    else:
        color, action, emoji = "⚪", "ОЖИДАНИЕ ⏸️", "⏸️"
    
    text = f"""
{color} *СИГНАЛ* {color}
━━━━━━━━━━━━━━━━━━━━━━

📊 *{symbol}*
⏱️ *{timeframe}*

💰 Цена: `{data['current']:.5f}`
🎯 {emoji} {signal_data['direction']}
⚡️ Уверенность: `{signal_data['confidence']}%`
📊 Изменение: `{signal_data['change']:+.2f}%`

💡 {action}
"""
    if signal_data['reasons']:
        text += "\n📋 *ПРИЧИНЫ:*\n" + "\n".join([f"├ {r}" for r in signal_data['reasons'][:3]])
    
    bot.edit_message_text(text, message.chat.id, status_msg.message_id, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '📈 СТАТИСТИКА')
def stats(message):
    user_id = message.from_user.id
    stats = db.get_stats(user_id)
    
    win_rate = stats['win_rate']
    bar = '🟢' * int(win_rate / 5) + '⚪' * (20 - int(win_rate / 5))
    
    text = f"""
📊 *СТАТИСТИКА*
━━━━━━━━━━━━━━━━━━━━━

├ Сделок: `{stats['total_trades']}`
├ Побед: `{stats['wins']}`
├ Поражений: `{stats['losses']}`
├ Win Rate: `{win_rate:.1f}%`
└ Прибыль: `{stats['total_profit']:+.2f}$`

{bar}
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '🔧 ИНСТРУМЕНТ')
def instrument(message):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("💱 ВАЛЮТЫ", callback_data="cat_forex"),
        types.InlineKeyboardButton("₿ КРИПТО", callback_data="cat_crypto"),
        types.InlineKeyboardButton("🛢️ СЫРЬЕ", callback_data="cat_commodities"),
        types.InlineKeyboardButton("📈 АКЦИИ", callback_data="cat_stocks"),
        types.InlineKeyboardButton("📊 ИНДЕКСЫ", callback_data="cat_indices")
    )
    bot.send_message(message.chat.id, "📊 *ВЫБЕРИТЕ КАТЕГОРИЮ*", parse_mode='Markdown', reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == '⏱️ ТАЙМФРЕЙМ')
def timeframe(message):
    kb = types.InlineKeyboardMarkup(row_width=4)
    for tf in TIMEFRAMES:
        kb.add(types.InlineKeyboardButton(tf, callback_data=f"tf_{tf}"))
    bot.send_message(message.chat.id, "⏱️ *ВЫБЕРИТЕ ТАЙМФРЕЙМ*", parse_mode='Markdown', reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == '🔑 ЛИЦЕНЗИЯ')
def license_info(message):
    user_id = message.from_user.id
    license_check = db.check_license(user_id)
    
    if license_check['valid']:
        text = f"🔑 *ЛИЦЕНЗИЯ*\n\n✅ Активна\n📋 {license_check['plan']}\n⏰ {license_check['days_left']} дней"
    else:
        text = f"🔑 *ЛИЦЕНЗИЯ*\n\n❌ {license_check['message']}\n🎁 Пробный: {config.FREE_TRIAL_DAYS} дня\n💳 /buy"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '💳 КУПИТЬ')
def buy(message):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton(f"💵 1 мес - ${config.PRICE_MONTHLY_USD}", callback_data="buy_monthly"),
        types.InlineKeyboardButton(f"💵 3 мес - ${config.PRICE_QUARTERLY_USD}", callback_data="buy_quarterly"),
        types.InlineKeyboardButton(f"💵 1 год - ${config.PRICE_YEARLY_USD}", callback_data="buy_yearly")
    )
    
    text = f"""
💳 *ПОКУПКА ЛИЦЕНЗИИ*

💰 WebMoney Z: `{config.WEBMONEY_Z}`
₿ WebMoney X: `{config.WEBMONEY_X}`

📋 Тарифы:
📅 Месяц: ${config.PRICE_MONTHLY_USD}
📆 3 месяца: ${config.PRICE_QUARTERLY_USD}
🌟 Год: ${config.PRICE_YEARLY_USD}

После оплаты: /confirm [ID] [plan]
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == '❓ ПОМОЩЬ')
def help_cmd(message):
    text = f"""
❓ *ПОМОЩЬ*

/start - Запуск
/signal - Сигнал
/stats - Статистика
/license - Лицензия
/buy - Купить

⏱️ Таймфреймы: 1s,5s,15s,30s,1m,5m,15m,30m,1h,4h,1d

📞 Поддержка: {config.SUPPORT_LINK}
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.from_user.id
    data = call.data
    
    if user_id not in user_settings:
        user_settings[user_id] = {'instrument': 'EUR/USD (OTC)', 'timeframe': '5s'}
    
    if data.startswith('cat_'):
        cat = data.replace('cat_', '')
        items = INSTRUMENTS.get(cat, [])
        kb = types.InlineKeyboardMarkup(row_width=1)
        for item in items:
            kb.add(types.InlineKeyboardButton(item, callback_data=f"inst_{item}"))
        bot.edit_message_text(f"📊 *{cat.upper()} OTC*", call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=kb)
    
    elif data.startswith('inst_'):
        inst = data.replace('inst_', '')
        user_settings[user_id]['instrument'] = inst
        bot.answer_callback_query(call.id, f"✅ {inst}")
        bot.edit_message_text(f"✅ *Инструмент:* {inst}", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    
    elif data.startswith('tf_'):
        tf = data.replace('tf_', '')
        user_settings[user_id]['timeframe'] = tf
        bot.answer_callback_query(call.id, f"✅ {tf}")
        bot.edit_message_text(f"✅ *Таймфрейм:* {tf}", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    
    elif data.startswith('buy_'):
        plan = data.replace('buy_', '')
        price = getattr(config, f'PRICE_{plan.upper()}_USD')
        text = f"""
💳 *ОПЛАТА*

💰 Кошелек: `{config.WEBMONEY_Z}`
💵 Сумма: ${price}
📋 План: {plan}

После оплаты: /confirm {user_id} {plan}
"""
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['confirm'])
def confirm(message):
    user_id = message.from_user.id
    if user_id not in config.ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Нет прав")
        return
    
    args = message.text.split()
    if len(args) < 3:
        bot.send_message(message.chat.id, "❌ /confirm [user_id] [plan]")
        return
    
    target = int(args[1])
    plan = args[2]
    
    if plan in ['monthly', 'quarterly', 'yearly']:
        db.activate_license(target, plan)
        bot.send_message(message.chat.id, f"✅ Активировано для {target}\n📋 {plan}")
        try:
            bot.send_message(target, f"✅ *ЛИЦЕНЗИЯ АКТИВИРОВАНА!*\n\nТариф: {plan}\nИспользуйте /signal", parse_mode='Markdown')
        except:
            pass

# ============================================
# ЗАПУСК
# ============================================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 PRO OTC TRADING BOT")
    print("=" * 50)
    print(f"👤 Админ: @ArtemchkaaBro")
    print(f"💳 Z: {config.WEBMONEY_Z}")
    print(f"₿ X: {config.WEBMONEY_X}")
    print("=" * 50)
    print("✅ Бот запущен!")
    print("=" * 50)
    
    bot.infinity_polling(timeout=60)
