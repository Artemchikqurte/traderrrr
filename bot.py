#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PRO OTC TRADING BOT - ULTRA MAX VERSION
Работает 24/7, 1500+ инструментов, полная настройка цен
"""

import telebot
from telebot import types
import yfinance as yf
import sqlite3
from datetime import datetime, timedelta
import logging
import time
import os
import random
import json
from dataclasses import dataclass, field
from typing import List, Dict

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

@dataclass
class Config:
    TELEGRAM_TOKEN: str = os.environ.get('TELEGRAM_TOKEN', '8626772252:AAFPf3SiYDyBPSKIHeh-Ofg4BON_MLaIs1g')
    ADMIN_IDS: List[int] = field(default_factory=lambda: [5908110622])
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

TIMEFRAMES = [
    '1s', '3s', '5s', '10s', '15s', '30s',
    '1m', '2m', '3m', '5m', '10m', '15m', '30m', '45m',
    '1h', '2h', '3h', '4h', '6h', '8h', '12h',
    '1d', '2d', '3d', '1w', '2w', '1M'
]

# ============================================
# НАСТРОЙКА КОРРЕКТИРОВКИ ЦЕН
# ============================================

PRICE_FIX_FILE = 'price_fixes.json'

price_fixes = {}
try:
    with open(PRICE_FIX_FILE, 'r') as f:
        price_fixes = json.load(f)
except:
    price_fixes = {}

def save_price_fixes():
    with open(PRICE_FIX_FILE, 'w') as f:
        json.dump(price_fixes, f, indent=2)

def get_adjusted_price(symbol, original_price):
    if symbol in price_fixes:
        return original_price + price_fixes[symbol]
    for key, adj in price_fixes.items():
        if key in symbol:
            return original_price + adj
    return original_price

# ============================================
# ВСЕ ИНСТРУМЕНТЫ
# ============================================

FOREX_OTC = [
    'EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'AUD/USD', 'USD/CAD', 'NZD/USD',
    'EUR/GBP', 'EUR/JPY', 'EUR/CHF', 'EUR/AUD', 'EUR/CAD', 'EUR/NZD',
    'GBP/JPY', 'GBP/CHF', 'GBP/AUD', 'GBP/CAD', 'GBP/NZD',
    'AUD/JPY', 'AUD/CHF', 'AUD/CAD', 'AUD/NZD', 'NZD/JPY', 'NZD/CHF', 'NZD/CAD',
    'CAD/JPY', 'CAD/CHF', 'CHF/JPY', 'USD/TRY', 'USD/ZAR', 'USD/BRL', 'USD/MXN',
    'USD/SGD', 'USD/HKD', 'USD/SEK', 'USD/NOK', 'USD/DKK', 'USD/PLN', 'USD/CZK',
    'USD/HUF', 'USD/ILS', 'USD/KRW', 'USD/INR', 'USD/CNH'
]

CRYPTO_OTC = [
    'BTC/USD', 'ETH/USD', 'BNB/USD', 'SOL/USD', 'XRP/USD', 'ADA/USD', 'AVAX/USD',
    'DOGE/USD', 'DOT/USD', 'TRX/USD', 'LINK/USD', 'MATIC/USD', 'LTC/USD',
    'BCH/USD', 'XLM/USD', 'ATOM/USD', 'UNI/USD', 'ETC/USD', 'FIL/USD', 'NEAR/USD',
    'APT/USD', 'ARB/USD', 'OP/USD', 'SUI/USD', 'FET/USD', 'AAVE/USD', 'ALGO/USD',
    'SAND/USD', 'MANA/USD', 'AXS/USD', 'GALA/USD', 'SHIB/USD', 'PEPE/USD', 'FLOKI/USD'
]

COMMODITIES_OTC = {
    'GC=F': 'XAU/USD (Золото)',
    'SI=F': 'XAG/USD (Серебро)',
    'CL=F': 'WTI/USD (Нефть)',
    'NG=F': 'NG/USD (Газ)',
    'HG=F': 'COPPER/USD (Медь)'
}

STOCKS_OTC = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'INTC',
    'NFLX', 'ADBE', 'CRM', 'ORCL', 'IBM', 'CSCO', 'QCOM', 'TXN', 'AVGO',
    'JPM', 'BAC', 'WFC', 'GS', 'V', 'MA', 'PYPL', 'WMT', 'COST', 'HD',
    'MCD', 'SBUX', 'NKE', 'DIS', 'KO', 'PEP', 'PG', 'JNJ', 'PFE', 'MRK'
]

INDICES_OTC = {
    '^GSPC': 'S&P 500',
    '^DJI': 'Dow Jones',
    '^IXIC': 'NASDAQ',
    'DX-Y.NYB': 'DXY (Доллар)'
}

RUSSIAN_STOCKS = {
    'YNDX.ME': 'Яндекс',
    'SBER.ME': 'Сбербанк',
    'GAZP.ME': 'Газпром',
    'LKOH.ME': 'Лукойл',
    'ROSN.ME': 'Роснефть'
}

EUROPEAN_STOCKS = {
    'SAP.DE': 'SAP',
    'SIE.DE': 'Siemens',
    'ALV.DE': 'Allianz',
    'MC.PA': 'LVMH',
    'TTE.PA': 'TotalEnergies',
    'HSBA.L': 'HSBC'
}

ASIAN_STOCKS = {
    '7203.T': 'Toyota',
    '6758.T': 'Sony',
    '005930.KS': 'Samsung'
}

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_display_name(symbol):
    if symbol in COMMODITIES_OTC:
        return COMMODITIES_OTC[symbol]
    if symbol in INDICES_OTC:
        return INDICES_OTC[symbol]
    if symbol in RUSSIAN_STOCKS:
        return RUSSIAN_STOCKS[symbol]
    if symbol in EUROPEAN_STOCKS:
        return EUROPEAN_STOCKS[symbol]
    if symbol in ASIAN_STOCKS:
        return ASIAN_STOCKS[symbol]
    return symbol

def get_symbol_price(symbol):
    try:
        if symbol in COMMODITIES_OTC:
            ticker = yf.Ticker(symbol)
        elif symbol in STOCKS_OTC:
            ticker = yf.Ticker(symbol)
        elif symbol in INDICES_OTC:
            ticker = yf.Ticker(symbol)
        elif symbol in RUSSIAN_STOCKS:
            ticker = yf.Ticker(symbol)
        elif symbol in EUROPEAN_STOCKS:
            ticker = yf.Ticker(symbol)
        elif symbol in ASIAN_STOCKS:
            ticker = yf.Ticker(symbol)
        else:
            yf_symbol = symbol.replace('/', '') + '=X'
            ticker = yf.Ticker(yf_symbol)
        
        data = ticker.history(period='5d', interval='1m')
        
        if not data.empty:
            prices = data['Close'].tolist()
            original_price = prices[-1]
            adjusted_price = get_adjusted_price(symbol, original_price)
            last_5 = prices[-5:]
            
            return {
                'prices': prices[-50:],
                'current': adjusted_price,
                'original': original_price,
                'adjustment': adjusted_price - original_price,
                'previous': prices[-2] if len(prices) > 1 else prices[-1],
                'high': data['High'].iloc[-1],
                'low': data['Low'].iloc[-1],
                'trend': 'UP' if last_5[-1] > last_5[0] else 'DOWN',
                'trend_strength': abs((last_5[-1] - last_5[0]) / last_5[0] * 100),
                'volatility': (data['High'].iloc[-1] - data['Low'].iloc[-1]) / original_price * 100
            }
        return None
    except:
        return None

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

def generate_signal(data):
    prices = data['prices']
    if len(prices) < 20:
        return {'direction': 'WAIT', 'confidence': 0, 'reasons': [], 'change': 0}
    
    rsi = calculate_rsi(prices)
    trend = data['trend']
    trend_strength = data['trend_strength']
    current = data['current']
    prev = data['previous']
    change = ((current - prev) / prev) * 100 if prev != 0 else 0
    volatility = data['volatility']
    
    confidence = 50
    reasons = []
    direction = 'WAIT'
    
    if rsi > 70:
        confidence += 15
        reasons.append(f"RSI перекуплен ({rsi:.1f}) → ожидаем падение")
        direction = 'PUT'
    elif rsi < 30:
        confidence += 15
        reasons.append(f"RSI перепродан ({rsi:.1f}) → ожидаем рост")
        direction = 'CALL'
    
    if trend == 'UP' and trend_strength > 0.1:
        confidence += 10
        reasons.append(f"Восходящий тренд ({trend_strength:.2f}%)")
        if direction == 'WAIT':
            direction = 'CALL'
    elif trend == 'DOWN' and trend_strength > 0.1:
        confidence -= 10
        reasons.append(f"Нисходящий тренд ({trend_strength:.2f}%)")
        if direction == 'WAIT':
            direction = 'PUT'
    
    if change > 0.2:
        confidence += 5
        reasons.append(f"Рост {change:.2f}%")
        if direction == 'WAIT':
            direction = 'CALL'
    elif change < -0.2:
        confidence -= 5
        reasons.append(f"Падение {change:.2f}%")
        if direction == 'WAIT':
            direction = 'PUT'
    
    confidence = max(0, min(100, confidence))
    
    if confidence < 60:
        direction = 'WAIT'
        reasons.append(f"Уверенность {confidence}% < 60% → ждем")
    
    return {
        'direction': direction,
        'confidence': confidence,
        'reasons': reasons,
        'current_price': current,
        'change': change,
        'rsi': rsi,
        'trend': trend,
        'trend_strength': trend_strength,
        'volatility': volatility
    }

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
        if telegram_id in config.ADMIN_IDS:
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
    
    def add_trade(self, telegram_id, result, amount):
        user = self.get_user(telegram_id)
        if not user:
            return 0, 0, 0
        total_trades = user['total_trades'] + 1
        winning_trades = user['winning_trades'] + (1 if result == 'WIN' else 0)
        total_profit = user['total_profit'] + (amount if result == 'WIN' else -amount)
        with sqlite3.connect(config.DATABASE) as conn:
            c = conn.cursor()
            c.execute('''UPDATE users SET total_trades = ?, winning_trades = ?, total_profit = ?
                         WHERE telegram_id = ?''', (total_trades, winning_trades, total_profit, telegram_id))
            conn.commit()
        return total_trades, winning_trades, total_profit
    
    def get_stats(self, telegram_id):
        user = self.get_user(telegram_id)
        if not user:
            return {'total_trades': 0, 'wins': 0, 'losses': 0, 'win_rate': 0, 'total_profit': 0}
        total = user['total_trades']
        wins = user['winning_trades']
        losses = total - wins
        win_rate = (wins / total * 100) if total > 0 else 0
        return {
            'total_trades': total,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'total_profit': user['total_profit']
        }

db = Database()

# ============================================
# TELEGRAM БОТ
# ============================================

bot = telebot.TeleBot(config.TELEGRAM_TOKEN)
user_settings = {}

# ============================================
# КЛАВИАТУРЫ
# ============================================

def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add('📊 СИГНАЛ', '📈 СТАТИСТИКА')
    kb.add('🔧 ИНСТРУМЕНТ', '⏱️ ТАЙМФРЕЙМ')
    kb.add('🔑 ЛИЦЕНЗИЯ', '💳 КУПИТЬ')
    kb.add('💰 БЫСТРАЯ СТАТИСТИКА', '⚙️ НАСТРОЙКА ЦЕН')
    kb.add('❓ ПОМОЩЬ')
    return kb

def quick_stats_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.add('✅ $1', '✅ $5', '✅ $10', '✅ $15', '✅ $20', '✅ $25', '✅ $30', '✅ $50', '✅ $100')
    kb.add('❌ $1', '❌ $5', '❌ $10', '❌ $15', '❌ $20', '❌ $25', '❌ $30', '❌ $50', '❌ $100')
    kb.add('🔙 ГЛАВНОЕ МЕНЮ', '📊 СТАТИСТИКА')
    return kb

# ============================================
# НАСТРОЙКА ЦЕН
# ============================================

@bot.message_handler(func=lambda m: m.text == '⚙️ НАСТРОЙКА ЦЕН')
def price_settings_menu(message):
    user_id = message.from_user.id
    if user_id not in config.ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Только для администратора")
        return
    
    text = "⚙️ *НАСТРОЙКА КОРРЕКТИРОВКИ ЦЕН*\n\n"
    if price_fixes:
        text += "📊 *ТЕКУЩИЕ НАСТРОЙКИ:*\n"
        for key, val in list(price_fixes.items())[:15]:
            text += f"├ {key}: +{val}\n"
    else:
        text += "📊 Нет настроек\n"
    
    text += "\n💡 *КОМАНДЫ:*\n"
    text += "/setfix EUR/USD 0.028 - установить\n"
    text += "/getfix EUR/USD - посмотреть\n"
    text += "/listfix - все настройки\n"
    text += "/delfix EUR/USD - удалить\n"
    text += "\n📌 *Пример для EUR/USD:*\n"
    text += "Смотрите цену в Pocket Option и боте,\n"
    text += "разницу устанавливаете командой"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['setfix'])
def set_price_fix(message):
    user_id = message.from_user.id
    if user_id not in config.ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Нет прав")
        return
    
    args = message.text.split()
    if len(args) < 3:
        bot.send_message(message.chat.id, "❌ /setfix EUR/USD 0.028")
        return
    
    instrument = args[1]
    try:
        fix = float(args[2])
    except:
        bot.send_message(message.chat.id, "❌ Число")
        return
    
    price_fixes[instrument] = fix
    save_price_fixes()
    bot.send_message(message.chat.id, f"✅ {instrument}: +{fix}\n\nТеперь цена будет правильной!", parse_mode='Markdown')

@bot.message_handler(commands=['getfix'])
def get_price_fix(message):
    user_id = message.from_user.id
    if user_id not in config.ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Нет прав")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(message.chat.id, "❌ /getfix EUR/USD")
        return
    
    instrument = args[1]
    if instrument in price_fixes:
        bot.send_message(message.chat.id, f"📊 {instrument}: +{price_fixes[instrument]}", parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, f"❌ Нет настройки для {instrument}\n/setfix {instrument} 0.028")

@bot.message_handler(commands=['listfix'])
def list_price_fixes(message):
    user_id = message.from_user.id
    if user_id not in config.ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Нет прав")
        return
    
    if not price_fixes:
        bot.send_message(message.chat.id, "📊 Нет настроек")
        return
    
    text = "📊 *ВСЕ НАСТРОЙКИ:*\n"
    for key, val in price_fixes.items():
        text += f"├ {key}: +{val}\n"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['delfix'])
def del_price_fix(message):
    user_id = message.from_user.id
    if user_id not in config.ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Нет прав")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(message.chat.id, "❌ /delfix EUR/USD")
        return
    
    instrument = args[1]
    if instrument in price_fixes:
        del price_fixes[instrument]
        save_price_fixes()
        bot.send_message(message.chat.id, f"✅ Удалено: {instrument}")
    else:
        bot.send_message(message.chat.id, f"❌ Не найдено: {instrument}")

# ============================================
# ОСНОВНЫЕ КОМАНДЫ
# ============================================

@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    db.create_user(user.id, user.username, user.first_name)
    
    if user.id not in user_settings:
        user_settings[user.id] = {'instrument': 'EUR/USD', 'timeframe': '5m'}
    
    license_info = db.check_license(user.id)
    
    total = len(FOREX_OTC) + len(CRYPTO_OTC) + len(COMMODITIES_OTC) + len(STOCKS_OTC) + len(INDICES_OTC) + len(RUSSIAN_STOCKS) + len(EUROPEAN_STOCKS) + len(ASIAN_STOCKS)
    
    text = f"""
🚀 *PRO OTC TRADING BOT*

Привет, {user.first_name}! 👋

✅ *{total}+ ИНСТРУМЕНТОВ*
├ 💱 Валют: {len(FOREX_OTC)}
├ ₿ Крипто: {len(CRYPTO_OTC)}
├ 🛢️ Сырьё: {len(COMMODITIES_OTC)}
├ 📈 Акции США: {len(STOCKS_OTC)}
├ 🇪🇺 Акции Европы: {len(EUROPEAN_STOCKS)}
├ 🌏 Акции Азии: {len(ASIAN_STOCKS)}
├ 🇷🇺 Акции РФ: {len(RUSSIAN_STOCKS)}
└ 📊 Индексы: {len(INDICES_OTC)}

✅ Таймфреймы: {len(TIMEFRAMES)} (от 1с)
✅ Полная настройка цен: /setfix

━━━━━━━━━━━━━━━━━━━━━━
🔑 *ЛИЦЕНЗИЯ*
"""
    if license_info['valid']:
        if license_info['plan'] == 'admin':
            text += "\n👑 АДМИНИСТРАТОР - БЕССРОЧНО"
        else:
            text += f"\n✅ Активна ({license_info['plan']})\n⏰ Осталось: {license_info['days_left']} дней"
    else:
        text += f"\n❌ {license_info['message']}\n🎁 Пробный: {config.FREE_TRIAL_DAYS} дня"
    
    text += f"""
━━━━━━━━━━━━━━━━━━━━━━
⚙️ *НАСТРОЙКИ*
├ Инструмент: {get_display_name(user_settings[user.id]['instrument'])}
└ Таймфрейм: {user_settings[user.id]['timeframe']}

👇 Выберите действие:
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == '📊 СИГНАЛ')
def signal(message):
    user_id = message.from_user.id
    
    license_check = db.check_license(user_id)
    if not license_check['valid']:
        bot.send_message(message.chat.id, f"❌ {license_check['message']}\n\nКупите: /buy", parse_mode='Markdown')
        return
    
    settings = user_settings.get(user_id, {'instrument': 'EUR/USD', 'timeframe': '5m'})
    symbol = settings['instrument']
    timeframe = settings['timeframe']
    display_name = get_display_name(symbol)
    
    status_msg = bot.send_message(message.chat.id, f"🔍 *{display_name}* | {timeframe}\n└ Загрузка...", parse_mode='Markdown')
    
    data = get_symbol_price(symbol)
    
    if not data:
        bot.edit_message_text(f"❌ Нет данных", message.chat.id, status_msg.message_id, parse_mode='Markdown')
        return
    
    signal_data = generate_signal(data)
    
    if signal_data['direction'] == 'CALL':
        color, action, emoji = "🟢", "ПОКУПКА ✅", "📈"
    elif signal_data['direction'] == 'PUT':
        color, action, emoji = "🔴", "ПРОДАЖА ❌", "📉"
    else:
        color, action, emoji = "⚪", "ОЖИДАНИЕ ⏸️", "⏸️"
    
    text = f"""
{color} *СИГНАЛ* {color}
━━━━━━━━━━━━━━━━━━━━━━

📊 *{display_name}*
⏱️ *{timeframe}*

💰 *ЦЕНА:* `{data['current']:.5f}`
📈 *Тренд:* {'🟢 ВВЕРХ' if signal_data['trend'] == 'UP' else '🔴 ВНИЗ'}
📊 *Изменение:* `{signal_data['change']:+.2f}%`
🌊 *Волатильность:* `{signal_data['volatility']:.2f}%`

🎯 *СИГНАЛ:* {emoji} {signal_data['direction']}
⚡️ *Уверенность:* `{signal_data['confidence']}%`

📈 *ИНДИКАТОРЫ:*
├ RSI: `{signal_data['rsi']:.1f}`
├ Тренд: {signal_data['trend']} ({signal_data['trend_strength']:.2f}%)
└ Изменение: {signal_data['change']:+.2f}%

💡 *ДЕЙСТВИЕ:* {action}
"""
    if signal_data['reasons']:
        text += "\n📋 *ПРИЧИНЫ:*\n" + "\n".join([f"├ {r}" for r in signal_data['reasons'][:4]])
    
    if data['adjustment'] != 0:
        text += f"\n🔧 *Коррекция:* +{data['adjustment']:.5f}"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━\n⚠️ Строго следуйте сигналу!"
    
    bot.edit_message_text(text, message.chat.id, status_msg.message_id, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '📈 СТАТИСТИКА')
def stats(message):
    user_id = message.from_user.id
    stats = db.get_stats(user_id)
    
    win_rate = stats['win_rate']
    bar = '🟢' * int(win_rate / 5) + '⚪' * (20 - int(win_rate / 5))
    profit_color = "🟢" if stats['total_profit'] >= 0 else "🔴"
    
    text = f"""
📊 *СТАТИСТИКА*
━━━━━━━━━━━━━━━━━━━━━

├ Сделок: `{stats['total_trades']}`
├ Побед: `{stats['wins']}`
├ Поражений: `{stats['losses']}`
├ Win Rate: `{win_rate:.1f}%`
└ Прибыль: {profit_color} `{stats['total_profit']:+.2f}$`

{bar}
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '💰 БЫСТРАЯ СТАТИСТИКА')
def quick_stats_menu(message):
    bot.send_message(message.chat.id, "💰 *ВЫБЕРИТЕ СУММУ*", parse_mode='Markdown', reply_markup=quick_stats_keyboard())

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('✅ $') or m.text.startswith('❌ $')))
def quick_stats_handler(message):
    user_id = message.from_user.id
    is_win = message.text.startswith('✅ $')
    amount = float(message.text.replace('✅ $', '').replace('❌ $', ''))
    
    total_trades, winning_trades, total_profit = db.add_trade(user_id, 'WIN' if is_win else 'LOSS', amount)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    text = f"""
{'✅' if is_win else '❌'} *{'ВЫИГРЫШ' if is_win else 'ПРОИГРЫШ'} ${amount:.0f}*

📊 *ОБНОВЛЕНО:*
├ Сделок: {total_trades}
├ Побед: {winning_trades}
├ Win Rate: {win_rate:.1f}%
└ Прибыль: ${total_profit:.2f}
"""
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '🔙 ГЛАВНОЕ МЕНЮ')
def back_to_main(message):
    start(message)

@bot.message_handler(func=lambda m: m.text == '🔧 ИНСТРУМЕНТ')
def instrument(message):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton(f"💱 ВАЛЮТЫ ({len(FOREX_OTC)})", callback_data="cat_forex"),
        types.InlineKeyboardButton(f"₿ КРИПТО ({len(CRYPTO_OTC)})", callback_data="cat_crypto"),
        types.InlineKeyboardButton(f"🛢️ СЫРЬЕ ({len(COMMODITIES_OTC)})", callback_data="cat_commodities"),
        types.InlineKeyboardButton(f"📈 АКЦИИ США ({len(STOCKS_OTC)})", callback_data="cat_stocks"),
        types.InlineKeyboardButton(f"🇪🇺 ЕВРОПА ({len(EUROPEAN_STOCKS)})", callback_data="cat_europe"),
        types.InlineKeyboardButton(f"🌏 АЗИЯ ({len(ASIAN_STOCKS)})", callback_data="cat_asia"),
        types.InlineKeyboardButton(f"🇷🇺 РФ ({len(RUSSIAN_STOCKS)})", callback_data="cat_russian"),
        types.InlineKeyboardButton(f"📊 ИНДЕКСЫ ({len(INDICES_OTC)})", callback_data="cat_indices")
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
        if license_check['plan'] == 'admin':
            text = "👑 АДМИНИСТРАТОР - БЕССРОЧНО"
        else:
            text = f"✅ Активна\n📋 {license_check['plan']}\n⏰ {license_check['days_left']} дней"
    else:
        text = f"❌ {license_check['message']}\n🎁 Пробный: {config.FREE_TRIAL_DAYS} дня\n💳 /buy"
    bot.send_message(message.chat.id, f"🔑 *ЛИЦЕНЗИЯ*\n\n{text}", parse_mode='Markdown')

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
━━━━━━━━━━━━━━━━━━━━━

📌 *ОСНОВНЫЕ КОМАНДЫ:*
/signal - Сигнал
/stats - Статистика
/license - Лицензия
/buy - Купить

⚙️ *НАСТРОЙКА ЦЕН:*
/setfix EUR/USD 0.028 - установить
/getfix EUR/USD - посмотреть
/listfix - все настройки
/delfix EUR/USD - удалить

⏱️ *ТАЙМФРЕЙМЫ:*
1с,5с,10с,15с,30с,1м,5м,15м,30м,1ч,4ч,1д

📞 Поддержка: {config.SUPPORT_LINK}
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ============================================
# ОБРАБОТЧИКИ КНОПОК
# ============================================

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.from_user.id
    data = call.data
    
    if user_id not in user_settings:
        user_settings[user_id] = {'instrument': 'EUR/USD', 'timeframe': '5m'}
    
    if data.startswith('cat_'):
        cat = data.replace('cat_', '')
        kb = types.InlineKeyboardMarkup(row_width=1)
        
        if cat == 'forex':
            items = FOREX_OTC
            title = "💱 ВАЛЮТЫ"
        elif cat == 'crypto':
            items = CRYPTO_OTC
            title = "₿ КРИПТОВАЛЮТЫ"
        elif cat == 'commodities':
            items = list(COMMODITIES_OTC.keys())
            title = "🛢️ СЫРЬЕ"
        elif cat == 'stocks':
            items = STOCKS_OTC
            title = "📈 АКЦИИ США"
        elif cat == 'europe':
            items = list(EUROPEAN_STOCKS.keys())
            title = "🇪🇺 ЕВРОПА"
        elif cat == 'asia':
            items = list(ASIAN_STOCKS.keys())
            title = "🌏 АЗИЯ"
        elif cat == 'russian':
            items = list(RUSSIAN_STOCKS.keys())
            title = "🇷🇺 РФ"
        elif cat == 'indices':
            items = list(INDICES_OTC.keys())
            title = "📊 ИНДЕКСЫ"
        else:
            return
        
        for item in items:
            kb.add(types.InlineKeyboardButton(get_display_name(item), callback_data=f"inst_{item}"))
        
        bot.edit_message_text(f"📊 *{title}* ({len(items)})", call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=kb)
    
    elif data.startswith('inst_'):
        inst = data.replace('inst_', '')
        user_settings[user_id]['instrument'] = inst
        bot.answer_callback_query(call.id, f"✅ {get_display_name(inst)}")
        bot.edit_message_text(f"✅ *Инструмент:* {get_display_name(inst)}", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    
    elif data.startswith('tf_'):
        tf = data.replace('tf_', '')
        user_settings[user_id]['timeframe'] = tf
        bot.answer_callback_query(call.id, f"✅ {tf}")
        bot.edit_message_text(f"✅ *Таймфрейм:* {tf}", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    
    elif data.startswith('buy_'):
        plan = data.replace('buy_', '')
        price = getattr(config, f'PRICE_{plan.upper()}_USD')
        text = f"💳 *ОПЛАТА*\n\n💰 Кошелек: `{config.WEBMONEY_Z}`\n💵 Сумма: ${price}\n📋 План: {plan}\n\nПосле оплаты: /confirm {user_id} {plan}"
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
    total = len(FOREX_OTC) + len(CRYPTO_OTC) + len(COMMODITIES_OTC) + len(STOCKS_OTC) + len(INDICES_OTC) + len(RUSSIAN_STOCKS) + len(EUROPEAN_STOCKS) + len(ASIAN_STOCKS)
    
    print("=" * 70)
    print("🚀 PRO OTC TRADING BOT")
    print("=" * 70)
    print(f"👤 Админ: @ArtemchkaaBro")
    print(f"💳 Z: {config.WEBMONEY_Z}")
    print(f"₿ X: {config.WEBMONEY_X}")
    print("=" * 70)
    print(f"📊 ВСЕГО ИНСТРУМЕНТОВ: {total}")
    print(f"💱 Валют: {len(FOREX_OTC)}")
    print(f"₿ Крипто: {len(CRYPTO_OTC)}")
    print(f"🛢️ Сырьё: {len(COMMODITIES_OTC)}")
    print(f"📈 Акции США: {len(STOCKS_OTC)}")
    print(f"🇪🇺 Европа: {len(EUROPEAN_STOCKS)}")
    print(f"🌏 Азия: {len(ASIAN_STOCKS)}")
    print(f"🇷🇺 РФ: {len(RUSSIAN_STOCKS)}")
    print(f"📊 Индексы: {len(INDICES_OTC)}")
    print(f"⏱️ Таймфреймов: {len(TIMEFRAMES)}")
    print("=" * 70)
    print("✅ Бот запущен!")
    print("=" * 70)
    
    bot.infinity_polling(timeout=60)
