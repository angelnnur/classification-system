"""
Модуль для сбора данных о товарах с маркетплейсов
"""
from .wildberries_parser import WildberriesParser
from .ozon_parser import OzonParser
from .yandex_market_parser import YandexMarketParser

__all__ = ['WildberriesParser', 'OzonParser', 'YandexMarketParser']

