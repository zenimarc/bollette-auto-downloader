from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from Sqlite import Sqlite

class InvoiceScraper:
    def __init__(self):
        self.browser = None
        self.db = Sqlite()
        self.errors = []

    def update_db(self):
        """updates invoice db"""
        pass