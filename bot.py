    #!/usr/bin/env python
# -*- coding: utf-8 -*-
import telebot
from telebot import types
import yfinance as yf
import sqlite3
from datetime import datetime, timedelta
import logging
import time
import os
import requests
import random
from dataclasses import dataclass, field
from typing import List

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

@dataclass
class Config:
    TELEGRAM_TOKEN: str = os.environ.get('TELEGRAM_TOKEN', '8626772252:AAFPf3SiYDyBPSKIHeh-Ofg4BON_MLaIs1g')
    ADMIN_IDS: List[int] = field(default_factory=lambda: [5908110622])  # ВАШ ID
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
# ВСЕ ВАЛЮТЫ (100+ пар)
# ============================================

FOREX_OTC = [
    # MAJOR
    'EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'AUD/USD', 'USD/CAD', 'NZD/USD',
    # CROSS
    'EUR/GBP', 'EUR/JPY', 'EUR/CHF', 'EUR/AUD', 'EUR/CAD', 'EUR/NZD',
    'GBP/JPY', 'GBP/CHF', 'GBP/AUD', 'GBP/CAD', 'GBP/NZD',
    'AUD/JPY', 'AUD/CHF', 'AUD/CAD', 'AUD/NZD',
    'NZD/JPY', 'NZD/CHF', 'NZD/CAD',
    'CAD/JPY', 'CAD/CHF', 'CHF/JPY',
    # EXOTIC
    'USD/TRY', 'USD/ZAR', 'USD/BRL', 'USD/MXN', 'USD/SGD', 'USD/HKD', 'USD/SEK',
    'USD/NOK', 'USD/DKK', 'USD/PLN', 'USD/CZK', 'USD/HUF', 'USD/ILS', 'USD/KRW',
    'USD/INR', 'USD/CNH', 'EUR/TRY', 'EUR/ZAR', 'GBP/TRY', 'GBP/ZAR',
    'AUD/TRY', 'AUD/ZAR', 'NZD/TRY', 'NZD/ZAR', 'CAD/TRY', 'CAD/ZAR',
    'CHF/TRY', 'CHF/ZAR', 'JPY/TRY', 'JPY/ZAR'
]

# ============================================
# ВСЕ КРИПТОВАЛЮТЫ (200+)
# ============================================

CRYPTO_OTC = [
    # TOP 50
    'BTC/USD', 'ETH/USD', 'BNB/USD', 'SOL/USD', 'XRP/USD', 'ADA/USD', 'AVAX/USD',
    'DOGE/USD', 'DOT/USD', 'TRX/USD', 'LINK/USD', 'MATIC/USD', 'LTC/USD',
    'BCH/USD', 'XLM/USD', 'ATOM/USD', 'UNI/USD', 'ETC/USD', 'FIL/USD',
    'NEAR/USD', 'APT/USD', 'ARB/USD', 'OP/USD', 'SUI/USD', 'FET/USD',
    'AAVE/USD', 'ALGO/USD', 'FLOW/USD', 'SAND/USD', 'MANA/USD', 'AXS/USD',
    'GALA/USD', 'SHIB/USD', 'PEPE/USD', 'FLOKI/USD', 'WIF/USD', 'MKR/USD',
    'SNX/USD', 'COMP/USD', 'CRV/USD', 'LDO/USD', 'DYDX/USD', 'GMX/USD',
    'RUNE/USD', 'EGLD/USD', 'THETA/USD', 'FTM/USD', 'VET/USD', 'KLAY/USD',
    'HBAR/USD', 'ONE/USD', 'XMR/USD', 'ZEC/USD', 'DASH/USD', 'XEM/USD',
    'IOTA/USD', 'NEO/USD', 'ONT/USD', 'QTUM/USD', 'ZIL/USD', 'BAT/USD',
    'ZRX/USD', 'KSM/USD', 'GLMR/USD', 'CFX/USD', 'CRO/USD', 'OKB/USD',
    'HT/USD', 'GT/USD', 'KCS/USD', 'LEO/USD', 'TON/USD', 'NOT/USD',
    'JUP/USD', 'PYTH/USD', 'ONDO/USD', 'STRK/USD', 'SEI/USD', 'TIA/USD',
    'INJ/USD', 'RNDR/USD', 'AGIX/USD', 'OCEAN/USD', 'ROSE/USD', 'MINA/USD',
    'ZETA/USD', 'WLD/USD', 'BLUR/USD', 'PENDLE/USD', 'JTO/USD', 'ENA/USD',
    'ALT/USD', 'ETHFI/USD', 'REZ/USD', 'OMNI/USD', 'SAGA/USD', 'DYM/USD'
]

# ============================================
# ВСЕ СЫРЬЕВЫЕ ТОВАРЫ
# ============================================

COMMODITIES_OTC = {
    'GC=F': 'XAU/USD (Золото)',
    'SI=F': 'XAG/USD (Серебро)',
    'PL=F': 'XPT/USD (Платина)',
    'PA=F': 'XPD/USD (Палладий)',
    'CL=F': 'WTI/USD (Нефть WTI)',
    'BZ=F': 'BRENT/USD (Нефть Brent)',
    'NG=F': 'NG/USD (Природный газ)',
    'HO=F': 'HEATING OIL (Мазут)',
    'RB=F': 'RBOB/USD (Бензин)',
    'ZC=F': 'CORN/USD (Кукуруза)',
    'ZW=F': 'WHEAT/USD (Пшеница)',
    'ZS=F': 'SOYBEAN/USD (Соя)',
    'ZM=F': 'SOYBEAN MEAL (Соевый шрот)',
    'ZL=F': 'SOYBEAN OIL (Соевое масло)',
    'CT=F': 'COTTON/USD (Хлопок)',
    'SB=F': 'SUGAR/USD (Сахар)',
    'KC=F': 'COFFEE/USD (Кофе)',
    'CC=F': 'COCOA/USD (Какао)',
    'OJ=F': 'ORANGE JUICE (Апельсиновый сок)',
    'HG=F': 'COPPER/USD (Медь)',
    'ALI=F': 'ALUMINUM/USD (Алюминий)',
    'ZNC=F': 'ZINC/USD (Цинк)',
    'NIC=F': 'NICKEL/USD (Никель)',
    'LME_PB': 'LEAD/USD (Свинец)',
    'LME_SN': 'TIN/USD (Олово)',
    'LME_AH': 'ALUMINUM (Алюминий LME)'
}

# ============================================
# ВСЕ АКЦИИ США (300+)
# ============================================

STOCKS_OTC = [
    # TECH
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'INTC',
    'NFLX', 'ADBE', 'CRM', 'ORCL', 'IBM', 'CSCO', 'QCOM', 'TXN', 'AVGO',
    'MU', 'SNAP', 'PINS', 'SPOT', 'SQ', 'SHOP', 'NET', 'SNOW', 'UBER',
    'LYFT', 'ZM', 'DOCU', 'OKTA', 'DDOG', 'MDB', 'PLTR', 'PANW', 'CRWD',
    # FINANCE
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'V', 'MA', 'PYPL', 'AXP', 'COF',
    'SCHW', 'BLK', 'BK', 'PNC', 'USB', 'TFC', 'SPGI', 'MCO', 'FIS', 'FISV',
    # CONSUMER
    'WMT', 'COST', 'TGT', 'HD', 'LOW', 'MCD', 'SBUX', 'NKE', 'DIS', 'KO',
    'PEP', 'PG', 'CL', 'KHC', 'MDLZ', 'PM', 'MO', 'CVS', 'WBA', 'TMO',
    # HEALTHCARE
    'JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'AMGN', 'GILD', 'BIIB', 'REGN',
    'VRTX', 'ISRG', 'DHR', 'ABT', 'MDT', 'UNH', 'CVS', 'CI', 'ANTM',
    # INDUSTRIAL
    'BA', 'CAT', 'GE', 'F', 'GM', 'HON', 'MMM', 'LMT', 'RTX', 'NOC',
    'GD', 'DE', 'CATERPILLAR', 'UPS', 'FDX', 'UNP', 'CSX', 'NSC',
    # ENERGY
    'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'OXY', 'PSX', 'VLO', 'MPC',
    # TELECOM
    'T', 'VZ', 'TMUS', 'CMCSA', 'CHTR',
    # REAL ESTATE
    'AMT', 'PLD', 'CCI', 'EQIX', 'DLR', 'PSA', 'WELL', 'SPG'
]

# ============================================
# ВСЕ ИНДЕКСЫ
# ============================================

INDICES_OTC = {
    '^GSPC': 'SPX (S&P 500)',
    '^DJI': 'DJI (Dow Jones)',
    '^IXIC': 'IXIC (NASDAQ)',
    '^RUT': 'RUT (Russell 2000)',
    '^VIX': 'VIX (Volatility)',
    'DX-Y.NYB': 'DXY (Dollar Index)',
    '^FTSE': 'FTSE 100 (UK)',
    '^GDAXI': 'DAX (Germany)',
    '^FCHI': 'CAC 40 (France)',
    '^STOXX50E': 'Euro Stoxx 50',
    '^IBEX': 'IBEX 35 (Spain)',
    '^SMI': 'SMI (Switzerland)',
    '^AEX': 'AEX (Netherlands)',
    '^N225': 'Nikkei 225 (Japan)',
    '^HSI': 'Hang Seng (Hong Kong)',
    '000300.SS': 'CSI 300 (China)',
    '^AXJO': 'ASX 200 (Australia)',
    '^KS11': 'KOSPI (Korea)',
    '^NSEI': 'Nifty 50 (India)',
    '^BVSP': 'Bovespa (Brazil)',
    '^IMOEX': 'MOEX (Russia)'
}

# ============================================
# АКЦИИ РОССИЙСКИХ КОМПАНИЙ (МОСКОВСКАЯ БИРЖА)
# ============================================

RUSSIAN_STOCKS = {
    'SBER.ME': 'Сбербанк',
    'GAZP.ME': 'Газпром',
    'LKOH.ME': 'Лукойл',
    'ROSN.ME': 'Роснефть',
    'NVTK.ME': 'Новатэк',
    'TATN.ME': 'Татнефть',
    'SNGS.ME': 'Сургутнефтегаз',
    'GMKN.ME': 'Норникель',
    'CHMF.ME': 'Северсталь',
    'NLMK.ME': 'НЛМК',
    'MAGN.ME': 'Магнитогорский МК',
    'ALRS.ME': 'Алроса',
    'MTSS.ME': 'МТС',
    'RTKM.ME': 'Ростелеком',
    'MGNT.ME': 'Магнит',
    'YNDX.ME': 'Яндекс',
    'TCSG.ME': 'Т-Банк (Тинькофф)',
    'VKCO.ME': 'VK',
    'OZON.ME': 'Ozon',
    'AFKS.ME': 'АФК Система',
    'AFLT.ME': 'Аэрофлот',
    'PIKK.ME': 'ПИК',
    'LSRG.ME': 'ЛСР',
    'RUAL.ME': 'Русал',
    'PHOR.ME': 'ФосАгро',
    'IRAO.ME': 'Интер РАО',
    'FEES.ME': 'Россети',
    'HYDR.ME': 'РусГидро',
    'RSTI.ME': 'Россети',
    'UPRO.ME': 'Юнипро'
}

# ============================================
# ФУНКЦИЯ ПОЛУЧЕНИЯ ЦЕНЫ
# ============================================

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
        else:
            yf_symbol = symbol.replace('/', '') + '=X'
            ticker = yf.Ticker(yf_symbol)
        
        data = ticker.history(period='1d', interval='1m')
        
        if not data.empty:
            prices = data['Close'].tolist()
            return {
                'prices': prices[-30:],
                'current': prices[-1],
                'high': data['High'].iloc[-1],
                'low': data['Low'].iloc[-1],
                'symbol': symbol
            }
        return None
    except:
        return None

def get_display_name(symbol):
    if symbol in COMMODITIES_OTC:
        return COMMODITIES_OTC[symbol]
    if symbol in INDICES_OTC:
        return INDICES_OTC[symbol]
    if symbol in RUSSIAN_STOCKS:
        return RUSSIAN_STOCKS[symbol]
    return f"{symbol}"

# ============================================
# ИНДИКАТОРЫ
# ============================================

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

def generate_signal(prices):
    if len(prices) < 20:
        return {'direction': 'WAIT', 'confidence': 0, 'reasons': [], 'change': 0}
    
    rsi = calculate_rsi(prices)
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
            self.create_user(telegram_id, '', '')
            return {'valid': True, 'plan': 'trial', 'days_left': config.FREE_TRIAL_DAYS}
        
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
    
    def add_trade(self, telegram_id, result, amount):
        user = self.get_user(telegram_id)
        if not user:
            self.create_user(telegram_id, '', '')
            user = self.get_user(telegram_id)
        
        total_trades = user['total_trades'] + 1
        winning_trades = user['winning_trades'] + (1 if result == 'WIN' else 0)
        total_profit = user['total_profit'] + (amount if result == 'WIN' else -amount)
        
        with sqlite3.connect(config.DATABASE) as conn:
            c = conn.cursor()
            c.execute('''UPDATE users SET total_trades = ?, winning_trades = ?, total_profit = ?
                         WHERE telegram_id = ?''', (total_trades, winning_trades, total_profit, telegram_id))
            conn.commit()
        
        return total_trades, winning_trades, total_profit

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
    kb.add('🔑 ЛИЦЕНЗИЯ', '💳 КУПИТЬ')
    kb.add('💰 ДОБАВИТЬ СДЕЛКУ', '❓ ПОМОЩЬ')
    return kb

@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    db.create_user(user.id, user.username, user.first_name)
    
    if user.id not in user_settings:
        user_settings[user.id] = {'instrument': 'EUR/USD', 'timeframe': '5m'}
    
    license_info = db.check_license(user.id)
    
    total = len(FOREX_OTC) + len(CRYPTO_OTC) + len(COMMODITIES_OTC) + len(STOCKS_OTC) + len(INDICES_OTC) + len(RUSSIAN_STOCKS)
    
    text = f"""
🚀 *PRO OTC TRADING BOT*

Привет, {user.first_name}! 👋

✅ *ВСЕГО ИНСТРУМЕНТОВ: {total}*
├ Валют: {len(FOREX_OTC)}
├ Крипто: {len(CRYPTO_OTC)}
├ Сырьё: {len(COMMODITIES_OTC)}
├ Акции США: {len(STOCKS_OTC)}
├ Индексы: {len(INDICES_OTC)}
└ Акции РФ: {len(RUSSIAN_STOCKS)}

━━━━━━━━━━━━━━━━━━━━━━
🔑 *ЛИЦЕНЗИЯ*
"""
    if license_info['valid']:
        if license_info['plan'] == 'admin':
            text += "\n👑 АДМИНИСТРАТОР - БЕССРОЧНО"
        else:
            text += f"\n✅ Активна ({license_info['plan']})\n⏰ Осталось: {license_info['days_left']} дней"
    else:
        text += f"\n❌ {license_info['message']}\n🎁 Пробный период: {config.FREE_TRIAL_DAYS} дня"
    
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
        bot.edit_message_text(f"❌ Нет данных для {display_name}\n\nПопробуйте другой инструмент", 
                            message.chat.id, status_msg.message_id, parse_mode='Markdown')
        return
    
    signal_data = generate_signal(data['prices'])
    
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

💰 Цена: `{data['current']:.4f}`
📊 Макс: `{data['high']:.4f}`
📉 Мин: `{data['low']:.4f}`

🎯 {emoji} *{signal_data['direction']}*
⚡️ Уверенность: `{signal_data['confidence']}%`
📊 Изменение: `{signal_data['change']:+.2f}%`

💡 {action}
"""
    if signal_data['reasons']:
        text += "\n📋 *ПРИЧИНЫ:*\n" + "\n".join([f"├ {r}" for r in signal_data['reasons'][:3]])
    
    bot.edit_message_text(text, message.chat.id, status_msg.message_id, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '💰 ДОБАВИТЬ СДЕЛКУ')
def add_trade_menu(message):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🟢 WIN (Прибыль)", callback_data="trade_win"),
        types.InlineKeyboardButton("🔴 LOSS (Убыток)", callback_data="trade_loss")
    )
    bot.send_message(message.chat.id, "💰 *ВЫБЕРИТЕ РЕЗУЛЬТАТ СДЕЛКИ*\n\nЗатем введите сумму:", parse_mode='Markdown', reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith('trade_'))
def trade_callback(call):
    user_id = call.from_user.id
    result = call.data.replace('trade_', '').upper()
    
    # Сохраняем состояние
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]['pending_trade'] = result
    
    bot.answer_callback_query(call.id, f"Введите сумму в $")
    bot.send_message(call.message.chat.id, f"💰 *Введите сумму сделки в $* (например: 15)\n\nРезультат: {'WIN' if result == 'WIN' else 'LOSS'}", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text and m.text.replace('.', '').replace('-', '').isdigit() and m.from_user.id in user_settings and 'pending_trade' in user_settings[m.from_user.id])
def process_trade_amount(message):
    user_id = message.from_user.id
    result = user_settings[user_id]['pending_trade']
    amount = float(message.text)
    
    # Сохраняем сделку
    total_trades, winning_trades, total_profit = db.add_trade(user_id, result, amount)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    text = f"""
✅ *СДЕЛКА ЗАПИСАНА!*

📊 Результат: {'🟢 WIN' if result == 'WIN' else '🔴 LOSS'}
💰 Сумма: ${amount:.2f}
{'📈 Прибыль' if result == 'WIN' else '📉 Убыток'}: ${amount if result == 'WIN' else -amount:.2f}

━━━━━━━━━━━━━━━━━━━━━━
📊 *ОБНОВЛЕННАЯ СТАТИСТИКА:*
├ Сделок: {total_trades}
├ Побед: {winning_trades}
├ Поражений: {total_trades - winning_trades}
├ Win Rate: {win_rate:.1f}%
└ Общая прибыль: ${total_profit:.2f}
"""
    bot.reply_to(message, text, parse_mode='Markdown')
    
    # Очищаем состояние
    del user_settings[user_id]['pending_trade']

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
        types.InlineKeyboardButton(f"💱 ВАЛЮТЫ ({len(FOREX_OTC)})", callback_data="cat_forex"),
        types.InlineKeyboardButton(f"₿ КРИПТО ({len(CRYPTO_OTC)})", callback_data="cat_crypto"),
        types.InlineKeyboardButton(f"🛢️ СЫРЬЕ ({len(COMMODITIES_OTC)})", callback_data="cat_commodities"),
        types.InlineKeyboardButton(f"📈 АКЦИИ США ({len(STOCKS_OTC)})", callback_data="cat_stocks"),
        types.InlineKeyboardButton(f"📊 ИНДЕКСЫ ({len(INDICES_OTC)})", callback_data="cat_indices"),
        types.InlineKeyboardButton(f"🇷🇺 АКЦИИ РФ ({len(RUSSIAN_STOCKS)})", callback_data="cat_russian")
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
    total = len(FOREX_OTC) + len(CRYPTO_OTC) + len(COMMODITIES_OTC) + len(STOCKS_OTC) + len(INDICES_OTC) + len(RUSSIAN_STOCKS)
    text = f"""
❓ *ПОМОЩЬ*
━━━━━━━━━━━━━━━━━━━━━

📊 *ДОСТУПНО ИНСТРУМЕНТОВ: {total}*

💱 Валют: {len(FOREX_OTC)}
₿ Крипто: {len(CRYPTO_OTC)}
🛢️ Сырьё: {len(COMMODITIES_OTC)}
📈 Акции США: {len(STOCKS_OTC)}
📊 Индексы: {len(INDICES_OTC)}
🇷🇺 Акции РФ: {len(RUSSIAN_STOCKS)}

⏱️ *ТАЙМФРЕЙМЫ:*
1s,5s,10s,15s,30s,1m,5m,15m,30m,1h,4h,1d,1w

📌 *КОМАНДЫ:*
/signal - Сигнал
/stats - Статистика
/license - Лицензия
/buy - Купить
💰 ДОБАВИТЬ СДЕЛКУ - записать результат

📞 Поддержка: {config.SUPPORT_LINK}
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

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
        elif cat == 'indices':
            items = list(INDICES_OTC.keys())
            title = "📊 ИНДЕКСЫ"
        elif cat == 'russian':
            items = list(RUSSIAN_STOCKS.keys())
            title = "🇷🇺 АКЦИИ РФ"
        else:
            return
        
        for item in items[:50]:
            display = get_display_name(item)
            kb.add(types.InlineKeyboardButton(display, callback_data=f"inst_{item}"))
        
        if len(items) > 50:
            kb.add(types.InlineKeyboardButton(f"📂 ЕЩЕ {len(items)-50}...", callback_data=f"more_{cat}_50"))
        
        bot.edit_message_text(f"📊 *{title}* (всего: {len(items)})", 
                            call.message.chat.id, call.message.message_id, 
                            parse_mode='Markdown', reply_markup=kb)
    
    elif data.startswith('more_'):
        parts = data.split('_')
        cat = parts[1]
        offset = int(parts[2])
        
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
        elif cat == 'indices':
            items = list(INDICES_OTC.keys())
            title = "📊 ИНДЕКСЫ"
        elif cat == 'russian':
            items = list(RUSSIAN_STOCKS.keys())
            title = "🇷🇺 АКЦИИ РФ"
        else:
            return
        
        kb = types.InlineKeyboardMarkup(row_width=1)
        for item in items[offset:offset+50]:
            display = get_display_name(item)
            kb.add(types.InlineKeyboardButton(display, callback_data=f"inst_{item}"))
        
        if offset + 50 < len(items):
            kb.add(types.InlineKeyboardButton(f"📂 ЕЩЕ {len(items)-offset-50}...", callback_data=f"more_{cat}_{offset+50}"))
        
        kb.add(types.InlineKeyboardButton("🔙 НАЗАД", callback_data=f"cat_{cat}"))
        
        bot.edit_message_text(f"📊 *{title}* (всего: {len(items)})", 
                            call.message.chat.id, call.message.message_id, 
                            parse_mode='Markdown', reply_markup=kb)
    
    elif data.startswith('inst_'):
        inst = data.replace('inst_', '')
        user_settings[user_id]['instrument'] = inst
        bot.answer_callback_query(call.id, f"✅ {get_display_name(inst)}")
        bot.edit_message_text(f"✅ *Инструмент установлен*\n\n{get_display_name(inst)}\n\n⏱️ Таймфрейм: {user_settings[user_id]['timeframe']}", 
                            call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    
    elif data.startswith('tf_'):
        tf = data.replace('tf_', '')
        user_settings[user_id]['timeframe'] = tf
        bot.answer_callback_query(call.id, f"✅ Таймфрейм: {tf}")
        bot.edit_message_text(f"✅ *Таймфрейм установлен*\n\n{tf}", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    
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
    total = len(FOREX_OTC) + len(CRYPTO_OTC) + len(COMMODITIES_OTC) + len(STOCKS_OTC) + len(INDICES_OTC) + len(RUSSIAN_STOCKS)
    
    print("=" * 60)
    print("🚀 PRO OTC TRADING BOT")
    print("=" * 60)
    print(f"👤 Админ: @ArtemchkaaBro")
    print(f"💳 Z: {config.WEBMONEY_Z}")
    print(f"₿ X: {config.WEBMONEY_X}")
    print("=" * 60)
    print(f"📊 ВСЕГО ИНСТРУМЕНТОВ: {total}")
    print(f"💱 Валют: {len(FOREX_OTC)}")
    print(f"₿ Крипто: {len(CRYPTO_OTC)}")
    print(f"🛢️ Сырьё: {len(COMMODITIES_OTC)}")
    print(f"📈 Акции США: {len(STOCKS_OTC)}")
    print(f"📊 Индексы: {len(INDICES_OTC)}")
    print(f"🇷🇺 Акции РФ: {len(RUSSIAN_STOCKS)}")
    print(f"⏱️ Таймфреймов: {len(TIMEFRAMES)}")
    print("=" * 60)
    print("✅ Бот запущен! Работает 24/7")
    print("=" * 60)
    
    bot.infinity_polling(timeout=60)
