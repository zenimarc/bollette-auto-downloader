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
from pathlib import Path
import datetime
import PyPDF2
import re

CHROMEDRIVER_PATH = "chromedriver.exe"
LOGIN_PAGE = "https://myeon.eon-energia.com/it/login.html?state=%2Fit%2Fdashboard.html"
API = "https://api-mmi.eon.it/scsi/invoices/v1.0/?apiversion=v1.2&fromdate=&todate=&pr="
date_format_eon = '%d/%m/%Y'
date_format_sqlite = "%Y-%m-%d"


# ATTENZIONE! Sembra che EON non fornisce POD ma un suo ID particolare

class Eon(InvoiceScraper):
    def __init__(self, username, password):
        InvoiceScraper.__init__(self)
        self.username = username
        self.password = password
        self.JWTtoken = None
        self.sub_key = None
        self.headers = None
        self.podMap = None

        options = Options()
        # options.add_argument('--headless')
        # options.add_argument('--disable-gpu')  # Last I checked this was necessary.
        self.browser = webdriver.Chrome(chrome_options=options)


        # load podmap if exists
        self.loadPodMap()

        self.browser.get(LOGIN_PAGE)

        try:
            myElem = WebDriverWait(self.browser, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                                                'body > main > div > div > div.signin.section > div > div > div.side-box > div.side-box__wrapper > div.form-wrapper > form > div:nth-child(1) > input')))
            print("Page is ready!")
        except TimeoutException:
            print("Loading took too much time!")

        try:
            # inserting login and password and click login
            self.browser.find_element_by_css_selector(
                "body > main > div > div > div.signin.section > div > div > div.side-box > div.side-box__wrapper > div.form-wrapper > form > div:nth-child(1) > input").send_keys(
                self.username)
            self.browser.find_element_by_css_selector(
                "body > main > div > div > div.signin.section > div > div > div.side-box > div.side-box__wrapper > div.form-wrapper > form > div:nth-child(2) > input").send_keys(
                self.password)
            element = self.browser.find_element_by_css_selector(
                "body > main > div > div > div.signin.section > div > div > div.side-box > div.side-box__wrapper > div.form-wrapper > form > div.button-wrapper > button > span")
            self.browser.execute_script("arguments[0].click();", element)
        except Exception as e:
            print(e)
            error = ("impossibile loggare EON" + self.username)
            print(error)
            self.errors.append(error)
            return

        # wait page to be loaded
        try:
            myElem = WebDriverWait(self.browser, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'messages-container')))
            print("Page is ready!")
        except TimeoutException:
            print("Loading took too much time!")

        try:
            self.JWTtoken = self.browser.execute_script("return getJwtToken()")
            self.sub_key = self.browser.execute_script("""return env["subscription.key"]""")

            self.headers = {
                "Host": "api-mmi.eon.it",
                "Connection": "keep-alive",
                "Origin": "https://myeon.eon-energia.com",
                "Authorization": "null",
                "Ocp-Apim-Subscription-Key": "null",
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36",
                "Sec-Fetch-Dest": "empty",
                "X-Request-ID": "6f2a0022-2b7c-4d85-a90d-279c31b92396",
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-Mode": "cors",
                "Referer": "https://myeon.eon-energia.com/it/managemybills.html",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
            }
            self.headers["Authorization"] = "bearer " + self.JWTtoken
            self.headers["Ocp-Apim-Subscription-Key"] = self.sub_key
        except Exception as e:
            print(e.__str__() + "\n errore ottenimento token")

        self.browser.close()

    def loadPodMap(self):
        # load podmap json if exist
        # if file not exist set podmap void json and save a blank json
        BASE_DIR = Path(__file__).resolve().parent
        try:
            with open(BASE_DIR.joinpath("eon_podmap.json"), "r") as jsonFile:
                self.podMap = json.load(jsonFile)
                jsonFile.close()
        except FileNotFoundError:
            self.podMap = {}

    def savePodMap(self):
        BASE_DIR = Path(__file__).resolve().parent
        try:
            with open(BASE_DIR.joinpath("eon_podmap.json"), "w") as jsonFile:
                json.dump(self.podMap, jsonFile)
                jsonFile.close()
        except Exception as e:
            print("impssible to save PodMap " + str(e))
            print(self.podMap)

    # generate session and retrieve json of invoices
    def getBollette(self):
        retrieved_json = requests.get(API, headers=self.headers).json()
        # print(retrieved_json)
        # with open("response.json", "w") as file:
        # json.dump(retrieved_json, file)
        return retrieved_json

    def retrieve_pdf_link(self, accountID, Number, Date, InstallationType):
        url = "https://api-mmi.eon.it/scsi/invoices/v1.0/invoicePDFs/" + Number + "?id_token=" + self.JWTtoken + "&subscription-key=" + self.sub_key + "&account-id=" + accountID + "&invoice-date=" + Date.strftime(
            date_format_eon) + "&installation-type=" + InstallationType
        return url

    def update_db(self):
        errors = []
        data = self.getBollette()
        for elem in data:
            accountID = elem["AccountID"]
            pod = elem["PODIDList"][0]  # load incorrect EON POD just in case we cannot retrieve the real one
            installationType = elem["InstallationType"]

            date = datetime.datetime.strptime(elem["Invoice"]["Date"], date_format_eon).date()

            number = elem["Invoice"]["Number"]
            paymentStatus = elem["Invoice"]["PaymentStatus"]
            amount = elem["Invoice"]["Amount"]
            pdfLink = self.retrieve_pdf_link(accountID, number, date, installationType)
            # eventualmente chiamo una writePDF2 che scrive in temp il pdf, lo analizza e prende POD e fa pod = nuovopod poi procede tutto regolarmente
            # se il pdf non è reperibile procedo con pod sbagliato (tanto sono vecchie) potrei anche creare una mappa PODsbagliato - PODgiusto nel SQL
            # così in futuro prima controllo se il pod sbagliato è presente in database e nel caso non devo neanche scaricare pdf e procedo con pod giusto.
            print("POD: {}: scarico bolletta {} {} del {}".format(pod, "EON", installationType, date))

            realpod = self.getRealPOD(pod, pdfLink, installationType)
            if realpod is not None:
                pod = realpod
            invoice = Invoice("EON", accountID, pod, number, date, amount, pdfLink, installationType, paymentStatus)

            done = self.db.create_invoice(invoice.getSqlTuple())
            if done is None:
                self.db.update_invoice(invoice.getUpdateTuple())

            self.writePDF(invoice)

    # write a temp pdf from the link  and return pdf path name, if i have some error return None
    def writeTempPDF(self, pdfLink):
        BASE_DIR = Path(__file__).resolve().parent
        response = requests.get(pdfLink)
        pdfName = "temp.pdf"
        if response.status_code != 500:
            try:
                with open(BASE_DIR.joinpath(pdfName), 'wb') as f:
                    print("download temp pdf completato: ")
                    f.write(response.content)
                    f.close()
                    return str(BASE_DIR.joinpath(pdfName))
            except Exception as e:
                return None

    def writePDF(self, invoice):
        """
        :type invoice: Invoice
        """
        # restituisce friendlynameandtype = [friendlyname, type]
        friendlyNameAndType = self.db.getFriendlyNameAndTypeFromProviderAndNumber(invoice.provider, int(invoice.number))
        if friendlyNameAndType is not None:
            rel_path = 'pdf/' + friendlyNameAndType[0] + '/' + friendlyNameAndType[1]
        else:
            rel_path = 'pdf/friendlyNameNotFound/'

        file_name = rel_path + '/' + invoice.number + ' ' + invoice.date.strftime("%d-%m-%Y") + '.pdf'
        BASE_DIR = Path(__file__).resolve().parent.parent
        ABSOLUTE_DIR = BASE_DIR.joinpath(rel_path)
        absolute_name = BASE_DIR.joinpath(file_name)
        Path(ABSOLUTE_DIR).mkdir(parents=True, exist_ok=True)

        if absolute_name.is_file():
            print("bolletta già presente non viene riscaricata: " + file_name)
        else:
            response = requests.get(invoice.pdfLink)
            if response.status_code != 500:
                with open(absolute_name, 'wb') as f:
                    print("download completato: " + file_name)
                    f.write(response.content)

    # se riesco restituisco il real POD, altrimenti return None
    def getRealPOD(self, fakePod, pdfLink, type):
        # provo a vedere se ho già una corrispondenza fakePod - realPod nel json
        if fakePod in self.podMap:
            return self.podMap[fakePod]

        pdfName = self.writeTempPDF(pdfLink)
        if pdfName is None:
            return None
        pdfFileObj = open(pdfName, 'rb')

        # pdf reader object
        pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
        # number of pages in pdf
        # print(pdfReader.numPages)
        # a page object
        pageObj = pdfReader.getPage(0)
        # extracting text from page.
        # this will print the text you can also save that into String
        s = pageObj.extractText()
        # print(s)
        result = None
        # questo estrae il POD se LUCE
        if type == "POWER":
            result = re.search('\(punto di prelievo\)(.*)Tipologia contatore', s)
            result = (result.group(1))
        # questo estrae il POD se GAS
        if type == "GAS":
            result = re.search('\(punto di riconsegna\)(.*)Matricola contatore', s)
            result = (result.group(1))

        if result is not None:
            self.addPodMapCouple(fakePod, result)
            return result

    def addPodMapCouple(self, fakePod, pod):
        self.podMap[fakePod] = pod
        self.savePodMap()
