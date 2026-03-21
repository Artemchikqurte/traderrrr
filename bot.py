#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PRO OTC TRADING BOT - С АВТОКАЛИБРОВКОЙ
"""

import telebot
from telebot import types
import yfinance as yf
import sqlite3
from datetime import datetime, timedelta
import logging
import time
import os
import json
from dataclasses import dataclass, field
from typing import List

# ============================================
# НАСТРОЙКИ
# ============================================

@dataclass
class Config:
    TELEGRAM_TOKEN: str = '8626772252:AAFPf3SiYDyBPSKIHeh-Ofg4BON_MLaIs1g'
    ADMIN_ID: int = 123456789
    DATABASE: str = 'trading_bot.db'

config = Config()

# ============================================
# ТАЙМФРЕЙМЫ
# ============================================

TIMEFRAMES = ['1s', '5s', '10s', '15s', '30s', '1m', '5m', '15m', '30m', '1h', '4h', '1d']

# ============================================
# ИНСТРУМЕНТЫ
# ============================================

INSTRUMENTS = {
    'forex': ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD'],
    'crypto': ['BTC/USD', 'ETH/USD', 'SOL/USD'],
    'commodities': ['XAU/USD (Золото)', 'XAG/USD (Серебро)']
}

# ============================================
# НАСТРОЙКА ЦЕН (АВТОСОХРАНЕНИЕ)
# ============================================

PRICE_FIXES_FILE = 'price_fixes.json'

price_fixes = {}
try:
    with open(PRICE_FIXES_FILE, 'r') as f:
        price_fixes = json.load(f)
except:
    price_fixes = {}

def save_fixes():
    with open(PRICE_FIXES_FILE, 'w') as f:
        json.dump(price_fixes, f, indent=2)

# ============================================
# ПОЛУЧЕНИЕ ЦЕНЫ
# ============================================

def get_price(symbol):
    try:
        clean = symbol.replace(' (Золото)', '').replace(' (Серебро)', '')
        
        if clean in ['XAU/USD', 'XAG/USD']:
            ticker = yf.Ticker('GC=F' if 'XAU' in clean else 'SI=F')
        elif '/' in clean:
            ticker = yf.Ticker(clean.replace('/', '') + '=X')
        else:
            ticker = yf.Ticker(clean)
        
        data = ticker.history(period='1d', interval='1m')
        
        if not data.empty:
            original = data['Close'].iloc[-1]
            
            # Применяем корректировку
            for key, fix in price_fixes.items():
                if key in symbol:
                    price = original + fix
                    break
            else:
                price = original
            
            return {
                'price': price,
                'original': original,
                'high': data['High'].iloc[-1],
                'low': data['Low'].iloc[-1],
                'change': ((price - data['Close'].iloc[-2]) / data['Close'].iloc[-2]) * 100 if len(data) > 1 else 0
            }
        return None
    except:
        return None

# ============================================
# RSI
# ============================================

def calculate_rsi(symbol):
    try:
        clean = symbol.replace(' (Золото)', '').replace(' (Серебро)', '')
        
        if clean in ['XAU/USD', 'XAG/USD']:
            ticker = yf.Ticker('GC=F' if 'XAU' in clean else 'SI=F')
        elif '/' in clean:
            ticker = yf.Ticker(clean.replace('/', '') + '=X')
        else:
            ticker = yf.Ticker(clean)
        
        data = ticker.history(period='5d', interval='5m')
        
        if len(data) < 15:
            return 50
        
        prices = data['Close'].tolist()
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        
        avg_gain = sum(gains[-14:]) / 14
        avg_loss = sum(losses[-14:]) / 14
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    except:
        return 50

# ============================================
# СИГНАЛ
# ============================================

def get_signal(symbol):
    rsi = calculate_rsi(symbol)
    price_data = get_price(symbol)
    
    if not price_data:
        return {'signal': '❌', 'text': 'Нет данных', 'confidence': 0}
    
    change = price_data['change']
    
    if rsi > 70:
        signal = '📉 ПРОДАЖА (PUT)'
        confidence = 70 + (rsi - 70) * 0.5
    elif rsi < 30:
        signal = '📈 ПОКУПКА (CALL)'
        confidence = 70 + (30 - rsi) * 0.5
    elif change > 0.3:
        signal = '📈 ПОКУПКА (CALL)'
        confidence = 60
    elif change < -0.3:
        signal = '📉 ПРОДАЖА (PUT)'
        confidence = 60
    else:
        signal = '⏸️ ОЖИДАНИЕ'
        confidence = 0
    
    return {
        'signal': signal,
        'price': price_data['price'],
        'original': price_data['original'],
        'rsi': round(rsi, 1),
        'change': round(change, 2),
        'confidence': round(confidence, 1),
        'high': price_data['high'],
        'low': price_data['low']
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
            c.execute('''CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                symbol TEXT,
                direction TEXT,
                result TEXT,
                amount REAL,
                profit REAL
            )''')
            conn.commit()
    
    def add_trade(self, symbol, direction, result, amount):
        profit = amount if result == 'WIN' else -amount
        with sqlite3.connect(config.DATABASE) as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO trades (date, symbol, direction, result, amount, profit)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (datetime.now().strftime('%Y-%m-%d %H:%M'), symbol, direction, result, amount, profit))
            conn.commit()
    
    def get_stats(self):
        with sqlite3.connect(config.DATABASE) as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*), SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END), SUM(profit) FROM trades")
            row = c.fetchone()
            total = row[0] if row[0] else 0
            wins = row[1] if row[1] else 0
            profit = row[2] if row[2] else 0
            win_rate = (wins / total * 100) if total > 0 else 0
            return {'total': total, 'wins': wins, 'losses': total - wins, 'win_rate': win_rate, 'profit': profit}

db = Database()

# ============================================
# TELEGRAM БОТ
# ============================================

bot = telebot.TeleBot(config.TELEGRAM_TOKEN)
user_settings = {}

def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add('📊 СИГНАЛ', '📈 СТАТИСТИКА')
    kb.add('🔧 ИНСТРУМЕНТ', '⏱️ ТАЙМФРЕЙМ')
    kb.add('💰 ДОБАВИТЬ СДЕЛКУ', '🔧 АВТОКАЛИБРОВКА')
    kb.add('❓ ПОМОЩЬ')
    return kb

# ============================================
# АВТОКАЛИБРОВКА (ГЛАВНОЕ)
# ============================================

@bot.message_handler(func=lambda m: m.text == '🔧 АВТОКАЛИБРОВКА')
def calibrate_menu(message):
    user_id = message.from_user.id
    if user_id != config.ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Только для админа")
        return
    
    text = """
🔧 *АВТОКАЛИБРОВКА ЦЕН*

Как это работает:
1. Смотришь цену в Pocket Option
2. Отправляешь команду с символом и ценой
3. Бот сам вычислит разницу и запомнит

📌 *КОМАНДЫ:*

/calibrate EUR/USD 1.18567
/calibrate BTC/USD 85000
/calibrate XAU/USD 2350.50

📊 *ТЕКУЩИЕ НАСТРОЙКИ:*
"""
    for key, val in price_fixes.items():
        text += f"├ {key}: +{val:.5f}\n"
    
    if not price_fixes:
        text += "├ Нет настроек\n"
    
    text += "\n💡 *Пример:*\nСмотришь EUR/USD = 1.18567\nПишешь: /calibrate EUR/USD 1.18567"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['calibrate'])
def calibrate(message):
    """Автоматическая калибровка цены"""
    user_id = message.from_user.id
    
    if user_id != config.ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Нет прав")
        return
    
    args = message.text.split()
    if len(args) < 3:
        bot.send_message(message.chat.id, 
            "❌ *Как использовать:*\n"
            "/calibrate EUR/USD 1.18567\n\n"
            "Где 1.18567 - цена в Pocket Option",
            parse_mode='Markdown')
        return
    
    symbol = args[1]
    try:
        pocket_price = float(args[2])
    except:
        bot.send_message(message.chat.id, "❌ Неверная цена")
        return
    
    # Получаем цену бота
    price_data = get_price(symbol)
    if not price_data:
        bot.send_message(message.chat.id, f"❌ Не удалось получить цену для {symbol}")
        return
    
    bot_price = price_data['price']
    diff = pocket_price - bot_price
    
    # Сохраняем корректировку
    price_fixes[symbol] = diff
    save_fixes()
    
    text = f"""
✅ *КАЛИБРОВКА ВЫПОЛНЕНА!*

━━━━━━━━━━━━━━━━━━━━━━
📊 *{symbol}*
━━━━━━━━━━━━━━━━━━━━━━

💰 Pocket Option: `{pocket_price:.5f}`
🤖 Бот показывал: `{bot_price:.5f}`
🔧 Разница: `{diff:+.5f}`

✅ Корректировка сохранена!

Теперь цены будут совпадать!
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ============================================
# ОСТАЛЬНЫЕ КОМАНДЫ
# ============================================

@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    
    if user.id not in user_settings:
        user_settings[user.id] = {'instrument': 'EUR/USD', 'timeframe': '5m'}
    
    stats = db.get_stats()
    
    text = f"""
🚀 *ТВОЙ ТОРГОВЫЙ БОТ*

Привет, {user.first_name}! 👋

📊 *СТАТИСТИКА:*
├ Сделок: {stats['total']}
├ Побед: {stats['wins']}
├ Поражений: {stats['losses']}
├ Win Rate: {stats['win_rate']:.1f}%
└ Прибыль: {stats['profit']:+.2f}$

━━━━━━━━━━━━━━━━━━━━━━
⚙️ *СЕЙЧАС:*
├ Инструмент: {user_settings[user.id]['instrument']}
└ Таймфрейм: {user_settings[user.id]['timeframe']}

👇 Выбери действие:
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == '📊 СИГНАЛ')
def signal(m):
    user_id = m.from_user.id
    settings = user_settings.get(user_id, {'instrument': 'EUR/USD', 'timeframe': '5m'})
    symbol = settings['instrument']
    timeframe = settings['timeframe']
    
    msg = bot.send_message(m.chat.id, f"🔍 *{symbol}* | {timeframe}\n└ Анализ...", parse_mode='Markdown')
    
    signal_data = get_signal(symbol)
    
    if signal_data['signal'] == '❌':
        bot.edit_message_text("❌ Ошибка получения данных", m.chat.id, msg.message_id)
        return
    
    if 'ПОКУПКА' in signal_data['signal']:
        color = "🟢"
    elif 'ПРОДАЖА' in signal_data['signal']:
        color = "🔴"
    else:
        color = "⚪"
    
    # Показываем корректировку если есть
    fix_text = ""
    for key, fix in price_fixes.items():
        if key in symbol:
            fix_text = f"\n🔧 Коррекция: +{fix:.5f}"
            break
    
    text = f"""
{color} *СИГНАЛ* {color}
━━━━━━━━━━━━━━━━━━━━━━

📊 *{symbol}*
⏱️ *{timeframe}*

💰 Цена: `{signal_data['price']:.5f}`{fix_text}
📊 Изменение: `{signal_data['change']:+.2f}%`
📈 RSI: `{signal_data['rsi']:.1f}`

🎯 *{signal_data['signal']}*
⚡️ Уверенность: `{signal_data['confidence']}%`

━━━━━━━━━━━━━━━━━━━━━━
💡 Действуй строго по сигналу!
"""
    bot.edit_message_text(text, m.chat.id, msg.message_id, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '📈 СТАТИСТИКА')
def stats(m):
    stats = db.get_stats()
    
    bar = '🟢' * int(stats['win_rate'] / 5) + '⚪' * (20 - int(stats['win_rate'] / 5))
    
    text = f"""
📊 *СТАТИСТИКА*
━━━━━━━━━━━━━━━━━━━━━

├ Сделок: `{stats['total']}`
├ Побед: `{stats['wins']}`
├ Поражений: `{stats['losses']}`
├ Win Rate: `{stats['win_rate']:.1f}%`
└ Прибыль: `{stats['profit']:+.2f}$`

{bar}
"""
    bot.send_message(m.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '💰 ДОБАВИТЬ СДЕЛКУ')
def add_trade_menu(m):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🟢 ВЫИГРАЛ", callback_data="trade_win"),
        types.InlineKeyboardButton("🔴 ПРОИГРАЛ", callback_data="trade_loss")
    )
    bot.send_message(m.chat.id, "💰 *РЕЗУЛЬТАТ СДЕЛКИ?*", parse_mode='Markdown', reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith('trade_'))
def trade_result(call):
    user_id = call.from_user.id
    result = call.data.replace('trade_', '').upper()
    
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]['pending_trade'] = result
    
    bot.answer_callback_query(call.id, f"Введите сумму")
    bot.send_message(call.message.chat.id, f"💰 *Введите сумму в $* (например: 15)\n\nРезультат: {'ВЫИГРЫШ' if result == 'WIN' else 'ПРОИГРЫШ'}", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text and m.text.replace('.', '').isdigit() and m.from_user.id in user_settings and 'pending_trade' in user_settings[m.from_user.id])
def process_amount(m):
    user_id = m.from_user.id
    result = user_settings[user_id]['pending_trade']
    amount = float(m.text)
    
    settings = user_settings.get(user_id, {'instrument': 'EUR/USD'})
    symbol = settings['instrument']
    
    db.add_trade(symbol, 'CALL' if result == 'WIN' else 'PUT', result, amount)
    stats = db.get_stats()
    
    text = f"""
✅ *СДЕЛКА ЗАПИСАНА!*

📊 {result} ${amount:.0f}

📊 *НОВАЯ СТАТИСТИКА:*
├ Сделок: {stats['total']}
├ Побед: {stats['wins']}
├ Win Rate: {stats['win_rate']:.1f}%
└ Прибыль: ${stats['profit']:.2f}
"""
    bot.reply_to(m, text, parse_mode='Markdown')
    del user_settings[user_id]['pending_trade']

@bot.message_handler(func=lambda m: m.text == '🔧 ИНСТРУМЕНТ')
def instrument(m):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("💱 ВАЛЮТЫ", callback_data="cat_forex"),
        types.InlineKeyboardButton("₿ КРИПТО", callback_data="cat_crypto"),
        types.InlineKeyboardButton("🛢️ СЫРЬЕ", callback_data="cat_commodities")
    )
    bot.send_message(m.chat.id, "📊 *ВЫБЕРИ КАТЕГОРИЮ*", parse_mode='Markdown', reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == '⏱️ ТАЙМФРЕЙМ')
def timeframe(m):
    kb = types.InlineKeyboardMarkup(row_width=4)
    for tf in TIMEFRAMES:
        kb.add(types.InlineKeyboardButton(tf, callback_data=f"tf_{tf}"))
    bot.send_message(m.chat.id, "⏱️ *ВЫБЕРИ ТАЙМФРЕЙМ*", parse_mode='Markdown', reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == '❓ ПОМОЩЬ')
def help_cmd(m):
    text = """
❓ *ПОМОЩЬ*
━━━━━━━━━━━━━━━━━━━━━

📌 *ОСНОВНЫЕ КОМАНДЫ:*

/signal - Получить сигнал
/stats - Статистика

🔧 *АВТОКАЛИБРОВКА ЦЕН:*

1. Смотришь цену в Pocket Option
2. Отправляешь: /calibrate EUR/USD 1.18567
3. Бот запоминает разницу

📋 *ДРУГИЕ КОМАНДЫ:*

/setfix EUR/USD 0.028 - ручная установка
/delfix EUR/USD - удалить
/listfix - все настройки

⏱️ *ТАЙМФРЕЙМЫ:*
1с,5с,10с,15с,30с,1м,5м,15м,30м,1ч,4ч,1д

📞 @ArtemchkaaBro
"""
    bot.send_message(m.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.from_user.id
    data = call.data
    
    if user_id not in user_settings:
        user_settings[user_id] = {'instrument': 'EUR/USD', 'timeframe': '5m'}
    
    if data.startswith('cat_'):
        cat = data.replace('cat_', '')
        items = INSTRUMENTS.get(cat, [])
        kb = types.InlineKeyboardMarkup(row_width=1)
        for item in items:
            kb.add(types.InlineKeyboardButton(item, callback_data=f"inst_{item}"))
        bot.edit_message_text(f"📊 *{cat.upper()}*", call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=kb)
    
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

# ============================================
# ЗАПУСК
# ============================================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 ТВОЙ ТОРГОВЫЙ БОТ")
    print("=" * 50)
    print("✅ Бот запущен!")
    print("💡 Для калибровки цены: /calibrate EUR/USD 1.18567")
    print("=" * 50)
    
    bot.infinity_polling(timeout=60)
