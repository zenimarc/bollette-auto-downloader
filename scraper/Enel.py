from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import time
import requests
import json
from bollette.Invoice import Invoice
from scraper.InvoiceScraper import InvoiceScraper
from Sqlite import Sqlite
from pathlib import Path
import datetime

CHROMEDRIVER_PATH = "chromedriver.exe"
LOGIN_PAGE = "https://www.enel.it/it/login"
NUMERO_MASSIMO_RISULTATI = 200
contratti_api = "https://www.enel.it/bin/areaclienti/auth/getCards?username=&_="
DOWNLOAD_DIR = Path(__file__).resolve().parent.joinpath("tempDownload")

class Enel(InvoiceScraper):
    def __init__(self, username, password, codfiscale):
        InvoiceScraper.__init__(self)
        self.username = username
        self.password = password
        self.api = "https://www.enel.it/bin/areaclienti/auth/getArchivioBollette?pagamentiRequest=" \
                   "%7B%22cache%22%3Atrue%2C%22canale%22%3A%22W%22%2C%22cf%22%3A%22"+codfiscale\
                   +"%22%2C%22inputList%22%3A%5B%5D%2C%22numeroMassimoX2%22%3A"+\
                   str(NUMERO_MASSIMO_RISULTATI)+"%2C%22tipologia%22%3A%22%22%7D%26emailUtente%3D%26_%3D"
        self.dateFormat = "%Y-%m-%d"
        self.cookies = None
        self.session = None

        options = Options()
        # options.add_argument('--headless')
        # options.add_argument('--disable-gpu')  # Last I checked this was necessary.
        self.browser = webdriver.Chrome(chrome_options=options)

        self.browser.get(LOGIN_PAGE)

        #wait page to be loaded
        time.sleep(4)

        # inserting login and password and click login
        try:
            self.browser.find_element_by_css_selector("#txtLoginUsername").send_keys(self.username)
            self.browser.find_element_by_css_selector("#txtLoginPassword").send_keys(self.password)
            element = self.browser.find_element_by_css_selector("#login-btn")
            self.browser.execute_script("arguments[0].click();", element)
        except Exception as e:
            error = ("errore login ENEL" + self.username)
            self.errors.append(error)
            print(error)
            print(e)
        try:
            # wait page to be loaded
            time.sleep(6)
            # save cookies
            self.cookies = self.browser.get_cookies()
            self.session = requests.Session()
            for cookie in self.cookies:
                self.session.cookies.set(cookie['name'], cookie['value'])
            self.browser.close()
        except Exception as e:
            error = ("errore salvataggio cookie ENEL")
            self.errors.append(error)
            print(error)
            print(e)


    def getBollette(self):
        """generate session and retrieve json of invoices"""
        if self.session is not None:
            retrieved_json = self.session.get(self.api).json()
            #self.browser.get(self.api)
            #retrieved_json = json.loads(self.browser.find_element_by_tag_name("pre").text)
            #print(retrieved_json)
            #with open("response.json", "w") as file:
                #json.dump(retrieved_json, file)
            return retrieved_json
        else:
            error = "impossibile reperire bollette ENEL di: "+self.username
            self.errors.append(error)
            return None


    def getMapContoContrattualeToPodPlusType(self):
        """:returns a map "contocontrattuale": (pod, type)"""
        #self.browser.get(contratti_api)
        #retrieved_json = json.loads(self.browser.find_element_by_tag_name("pre").text)
        retrieved_json = self.session.get(contratti_api).json()
        cards = retrieved_json["data"]["Cards"]
        # è una mappa contocontrattuale: (pod, type)
        mapContoContrattualePod = {}
        for card in cards:
            mapContoContrattualePod[card["contoContrattuale"]] = (card["pod"], str(card["alias"]).upper())

        return mapContoContrattualePod

    def retrieve_pdf_link(self, accountID, Number, Date, InstallationType):
        url = "https://www.enel.it/bin/areaclienti/auth/bollette?action=download-fattura&dispositivo=&tipoDocumento=fattura&numeroFattura=" + Number + "&dataEmissione=" + Date.strftime("%d/%m/%Y")
        return url

    def writePDF(self, invoice: Invoice):
        """
        :type invoice: Invoice
        """
        # restituisce friendlynameandtype = [friendlyname, type]
        friendlyNameAndType = self.db.getFriendlyNameAndTypeFromProviderAndNumber(invoice.provider, int(invoice.number))
        if friendlyNameAndType is not None:
            rel_path = 'pdf/' + friendlyNameAndType[0] + '/' + friendlyNameAndType[1]
        else:
            rel_path = 'pdf/friendlyNameNotFound'

        file_name = rel_path + '/' + str(invoice.number).lstrip("0") + ' ' + invoice.date.strftime("%d-%m-%Y") + '.pdf'
        BASE_DIR = Path(__file__).resolve().parent.parent
        ABSOLUTE_DIR = BASE_DIR.joinpath(rel_path)
        absolute_name = BASE_DIR.joinpath(file_name)
        Path(ABSOLUTE_DIR).mkdir(parents=True, exist_ok=True)

        if absolute_name.is_file():
            print("bolletta già presente non viene riscaricata: "+file_name)
        else:
            response = self.session.get(invoice.pdfLink)
            if response.status_code != 500:
                with open(absolute_name, 'wb') as f:
                    print("download completato: "+file_name)
                    f.write(response.content)

        # qui scarica il file pdf nella cartella di temp
        #self.browser.get(invoice.pdfLink)

    def update_db(self):
        data = self.getBollette()
        if data is None:
            return
        # (pod, type) tuple
        mappaContoPodPlusType = self.getMapContoContrattualeToPodPlusType()
        if data is not None:
            results = data["data"]["results"]
            for result in results:
                contoContrattuale = result["contoContrattuale"]
                fatture = result["fatture"]
                for fattura in fatture:
                    number = fattura["Numerodocumento"]
                    date = datetime.datetime.strptime(fattura["Dataemissione"], self.dateFormat).date() # in date format
                    amount = fattura["Importofattura"]
                    pod = mappaContoPodPlusType[contoContrattuale][0]
                    type = mappaContoPodPlusType[contoContrattuale][1]
                    pdfLink = self.retrieve_pdf_link(contoContrattuale, number, date, type)
                    invoice = Invoice("ENEL", contoContrattuale, pod, number, date, amount, pdfLink, type)

                    done = self.db.create_invoice(invoice.getSqlTuple())
                    if done is None:
                        self.db.update_invoice(invoice.getUpdateTuple())

                    self.writePDF(invoice)
        else:
            self.errors.append("errore generale ENEL di "+self.username)





