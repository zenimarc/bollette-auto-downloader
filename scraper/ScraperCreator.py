from scraper.Enel import Enel
from scraper.Eon import Eon
from scraper.Sen import Sen


class ScraperCreator:
    def __init__(self):
        pass

    @staticmethod
    def getScraper(account_data):
        if account_data["provider"] == "EON":
            return Eon(account_data["username"], account_data["password"])
        if account_data["provider"] == "ENEL":
            return Enel(account_data["username"], account_data["password"], account_data["cf"])
        if account_data["provider"] == "SEN":
            return Sen(account_data["username"], account_data["password"])
