#!/usr/bin/env python
# -*- coding: utf-8 -*-
import telebot
import time
import os

TOKEN = '8626772252:AAFPf3SiYDyBPSKIHeh-Ofg4BON_MLaIs1g'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ Бот работает! Версия 1.0")

@bot.message_handler(func=lambda m: True)
def echo(message):
    bot.reply_to(message, f"Я получил: {message.text}")

print("✅ Бот запущен!")
bot.infinity_polling()
