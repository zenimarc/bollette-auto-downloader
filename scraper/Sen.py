from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
import time
import requests
import json
from bollette.Invoice import Invoice
from Sqlite import Sqlite
from pathlib import Path
import datetime
from bs4 import BeautifulSoup
import re
import shutil
from scraper.InvoiceScraper import InvoiceScraper
import PyPDF2

CHROMEDRIVER_PATH = "chromedriver.exe"
LOGIN_PAGE = "https://www.servizioelettriconazionale.it/it-IT/bolletta/servizi/online"
POD_PAGE = "https://www.servizioelettriconazionale.it/it-IT/clienti/SEN/servizi/Areaclienti/ControllaBolletta/riepilogo.jsp?funz=A10&fromhp=si#dettaglio"
BOLLETTE_PAGE = "https://www.servizioelettriconazionale.it/it-IT/clienti/SEN/servizi/Areaclienti/ControllaBolletta/riepilogo.jsp?funz=A10&fromhp=si"
DOWNLOAD_DIR = Path(__file__).resolve().parent.joinpath("tempDownload")
DEFAULT_PDF_NAME = "vediPDF.pdf"
ANNO_INIZIO_DATABASE = 2015

class Sen(InvoiceScraper):
    def __init__(self, username, password):
        InvoiceScraper.__init__(self)
        self.username = username
        self.password = password
        self.dateFormat = "%Y-%m-%d"
        self.cookies = None
        self.session = None

        # delete temp folder (flush previous dowload)
        try:
            shutil.rmtree(DOWNLOAD_DIR)
        except:
            pass
        # create temp folder to download if not already exists
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        # set options to download pdf separately
        options = Options()
        options.add_experimental_option('prefs', {
            "download.default_directory": str(DOWNLOAD_DIR),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        })
        self.browser = webdriver.Chrome(chrome_options=options)

        self.browser.get(LOGIN_PAGE)

        #wait page to be loaded
        time.sleep(2)

        # inserting login and password and click login
        try:
            self.browser.maximize_window()
            self.browser.find_element_by_css_selector("#txtUsername").send_keys(self.username)
            self.browser.find_element_by_css_selector("#txtPassword").send_keys(self.password)
            element = self.browser.find_element_by_css_selector("#accessBtn")
            self.browser.execute_script("arguments[0].click();", element)
        except Exception as e:
            error = ("errore login SEN" + self.username)
            self.errors.append(error)
            print(error)
            print(e)
        try:
            # wait page to be loaded
            time.sleep(5)
            # save cookies
            self.cookies = self.browser.get_cookies()
            self.session = requests.Session()
            for cookie in self.cookies:
                self.session.cookies.set(cookie['name'], cookie['value'])
        except Exception as e:
            print("errore salvataggio cookie SEN")
            print(e)


    def writePDF(self, invoice, index):
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
            cmd = "doSubmitFaro(1,this,'" + str(index) + "')"
            self.browser.execute_script(cmd)
            # a questo punto il pdf è scaricato nella cartella temporanea, dobbiamo spostarlo
            try:
                waitFile()
                #os.rename(DOWNLOAD_DIR.joinpath(DEFAULT_PDF_NAME), DOWNLOAD_DIR.joinpath(str(invoice.number) + '.pdf'))
                #shutil.move(DOWNLOAD_DIR.joinpath(str(invoice.number)+'.pdf'), absolute_name)
                shutil.move(DOWNLOAD_DIR.joinpath(DEFAULT_PDF_NAME), absolute_name)

            except Exception as e:
                print("errore download pdf: "+file_name)
                # nel dubbio delete temp folder (flush previous download)
                shutil.rmtree(DOWNLOAD_DIR)
                # create temp folder to download if not exists
                DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # qui scarica il file pdf nella cartella di temp
        #self.browser.get(invoice.pdfLink)


    def getPod(self):
        try:
            self.browser.get(POD_PAGE)
            pagesource = self.browser.page_source
            soup = BeautifulSoup(pagesource, 'html.parser')
            scores = soup.find_all(text=re.compile('Codice POD:'))
            # soup.find(text=re.compile('Codice POD:')).find_next("div", {"class": "col p-0"})
            pod = scores[0].parent.find_next("div", {"class": "col p-0"}).text
            return pod
        except:
            error ="errore nel trovare POD, BOLLETTE NON SCARICATE DA "+self.username
            self.errors.append(error)
            print(error)
            return None

    def getForniture(self, current_try):
        try:
            pagesource = self.browser.page_source
            soup = BeautifulSoup(pagesource, 'html.parser')
            tab = soup.find("div", {"id": "tabsForniture_cellaSelect"})
            # .find(text=re.compile('Codice POD:'))
            divs = tab.next_element
            codici = divs.find_all("option")
            num_forniture = []
            for i in range(1, len(codici)):
                num_forniture.append(codici[i].text)
            return num_forniture
        except:
            # errore account senza forniture
            # se è la seconda volta che riprovo esco
            if current_try > 1:
                return None
            print("inserisci codice cliente di una bolletta di "+self.username + " esempio 006675999")
            codicecliente = input()
            self.browser.find_element_by_css_selector("#eneltel").send_keys(codicecliente)
            self.browser.find_element_by_css_selector("#tabsContent > form > div > div:nth-child(6) > div:nth-child(5) > div > button").click()
            time.sleep(1)
            return self.getForniture(current_try+1)



    def changeFornitura(self, id):
        command = "fnCambiaFornitura(" + str(id) + ')'
        self.browser.execute_script(command)

    def getBollette(self):
        # va nella pagina delle bollette, bisognerà poi indicare anno con setAnnoBollette
        self.browser.get(BOLLETTE_PAGE)
        time.sleep(1)

    def setAnnoBollette(self, anno):
        cmd = "scegliAnno("+str(anno)+')'
        self.browser.execute_script(cmd)
        time.sleep(1)

    def getNumBolletteAnno(self, anno):
        cmd = "scegliAnno("+str(anno)+')'
        self.browser.execute_script(cmd)
        rows = self.browser.find_element_by_id("tab_bollette").find_elements_by_tag_name("tr")
        return len(rows[1:])

    def closeBrowser(self):
        self.browser.quit()

    def update_db(self):

        # prima vedo tutte le forniture disponibili
        forniture = self.getForniture(0)
        if forniture is not None:
            for fornitura in forniture:
                if not len(forniture) == 1:
                    self.changeFornitura(fornitura)
                #per ogni fornitura salvo subito il POD
                pod = self.getPod()
                if pod is None:
                    continue

                # SEN prende un numero in più quindi se la lunghezza del pod è lungo 15 anzichè 14 posso troncare ultimo numero pod[:-1]
                if len(pod) == 15:
                    pod = pod[:-1]

                # setto subito type LUCE tanto sen è solo luce
                type = "LUCE"
                # per ogni fornitura (quindi ogni POD) eseguo scraping bollette
                self.getBollette()
                annoCorrente = datetime.datetime.now().date().year
                annoInizio = ANNO_INIZIO_DATABASE
                # per ogni fornitura controllo tutti gli anni
                for anno in range(annoInizio, annoCorrente+1):
                    self.setAnnoBollette(anno)
                    # qui estrapola la tabella anno corrente
                    try:
                        rows = self.browser.find_element_by_id("tab_bollette").find_elements_by_tag_name("tr")
                    except:
                        # se non trova la tabella probabilmente in questo anno non c'è niente, continua al prossimo anno
                        continue
                    for row in rows[1:]:
                        cols = row.find_elements_by_tag_name("td")
                        num_bolletta = None
                        data_scad = None
                        importo = None
                        for col in cols:
                            label = col.get_attribute("aria-label")
                            # print(label)
                            if label == "Numero Bolletta":
                                num_bolletta = col.text
                            if label == "Data Scadenza":
                                data_scad = col.text
                            if label == "Importo Bolletta euro":
                                importo = col.text

                        print("nuova bolletta "+str(num_bolletta)+str(data_scad)+str(importo))
                        num_bolletta_generated = int(pod[-3:] + str(data_scad).replace("/", "") + str(importo).replace(",", "").replace("-",""))
                        print(num_bolletta_generated)

                        # set date in date format
                        data_scad = datetime.datetime.strptime(data_scad, "%d/%m/%Y")
                        invoice = Invoice("SEN", fornitura, pod, num_bolletta_generated, data_scad, importo, None, type)

                        done = self.db.create_invoice(invoice.getSqlTuple())
                        if done is None:
                            self.db.update_invoice(invoice.getUpdateTuple())

                        self.writePDF(invoice, rows.index(row))  # gli index devono partire da 1, noi sfasiamo array che prima partiva da 1 ora da zero per mandare js sul sito
            self.closeBrowser()
        else:
            self.errors.append("errore generale Servizio elettrico nazionale su: "+self.username)



"""
# per ogni row della tabella sopra posso vedere il dettaglio (da fare dopo aver chiamato getBollette() )
sen.browser.execute_script("doSubmit(n)")
rows2 = sen.browser.find_element_by_id("dettaglio_bolletta").find_element_by_tag_name("tbody").find_elements_by_tag_name("tr")
for row in rows2:
    # Get the columns (all the column 2)
    cols = row.find_elements_by_tag_name("td") #note: index start from 0, 1 is col 2
    print("desc: "+cols[0].text)
    print("value: "+cols[1].text)
"""
def waitFile():
    max_limit = 8  # Seconds.

    start = time.time()
    condition_met = False
    while time.time() - start < max_limit:
        if DOWNLOAD_DIR.joinpath(DEFAULT_PDF_NAME).is_file():
            condition_met = True
            break
        time.sleep(1)
    return condition_met

def processNewInvoice(original_path, string):
    db = Sqlite()
    invoice = getInvoiceFromString(string)
    if invoice is not None:
        done = db.create_invoice(invoice.getSqlTuple())
        if done is None:
            db.update_invoice(invoice.getUpdateTuple())
        copyPdf(db, invoice, original_path)



# returrns a dictionary with key: pod, date, amount, fornitura
def getInvoiceFromString(s):
    try:
        # questo estrae il POD se LUCE
        pod = re.search(' POD(.*)CODICE FISCALE', s)
        pod = (pod.group(1))
        # SEN prende un numero in più quindi se la lunghezza del pod è lungo 15 anzichè 14 posso troncare ultimo numero pod[:-1]
        if len(pod) == 15:
            pod = pod[:-1]
        try:
            date = re.search('Del (.*)MESE', s)
            date = (date.group(1))
        except:
            date = re.search('Del (.*)BIMES', s)
            date = (date.group(1))

        date = datetime.datetime.strptime(date, "%d.%m.%Y")
        try:
            amount = re.search('TOTALE DA PAGARE(.*) Entro', s)
            amount = (amount.group(1))
        except:
            amount = re.search('FATTURATI(.*) Forniamo', s)
            amount = (amount.group(1))
        amount = amount.replace(",",".")
        fornitura = re.search('FORNITURAN CLIENTE(.*)CODICE POD', s)
        fornitura = (fornitura.group(1))
        num_bolletta_generated = int(
            pod[-3:] + str(date.strftime("%d/%m/%Y")).replace("/", "") + str(amount).replace(".", "").replace("-",""))
        return Invoice("SEN", fornitura, pod, num_bolletta_generated, date, amount, None, "LUCE")

    except Exception as e:
        print(e)
        return None

def copyPdf(db, invoice, original_file):
    # restituisce friendlynameandtype = [friendlyname, type]
    friendlyNameAndType = db.getFriendlyNameAndTypeFromPod(invoice.pod)
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
        print("bolletta già presente non viene copiata: "+file_name)
    else:
        shutil.copy(original_file, absolute_name)










