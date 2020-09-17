from scraper.Eon import Eon
from scraper.Enel import Enel
from Sqlite import Sqlite
import datetime
from pathlib import Path
from shutil import copyfile
from scraper.Sen import Sen
import os
from scraper.PdfParser import PdfParser
from scraper.ScraperCreator import ScraperCreator
import chromedriver_autoinstaller
import json

BASE_DIR = Path(__file__).resolve().parent
DESKTOP_DIR = Path(os.path.join(os.environ["HOMEPATH"], "Desktop"))
OUTPUT_ON_DESKTOP = 1
bollette_output_dateformat = "%Y-%m-%d"

#update chromedriver if necessary
chromedriver_autoinstaller.install()


# return pdf path and name if exist else None
def getPdfPath(friendlyName, type, number, date):
    file = BASE_DIR.joinpath("pdf/"+friendlyName+'/'+type+'/'+str(number)+' ' + date + '.pdf')
    if file.is_file():
        return file
    else:
        return None


def getPdfName(date):
    return date + '.pdf'


print("cosa vuoi fare?\n1. nuova interrogazione\n2. aggiungi pdf manualmente\n3. aggiorna database")
select = int(input())
if select == 3:
    scrapers = []
    with open("accounts.json", "r") as json_file:
        accounts_data = json.load(json_file)
        for account_data in accounts_data:
            if account_data["sync"]:  # if sync it's true for this account
                scrapers.append(ScraperCreator.getScraper(account_data))

        for scraper in scrapers:
            scraper.update_db()
            for errror in scraper.errors:
                print(errror)


if select == 1:
    db = Sqlite()
    print("scegli utenza")
    utenze = db.getFriendlyNameList()

    for utenza in utenze:
        print(str(utenze.index(utenza)) + ' ' + utenza[0])

    index_utenza = int(input())
    friendlyNameUtenza = utenze[index_utenza][0]
    print("data inizio? gg/mm/YYYY")
    startDate = datetime.datetime.strptime(input(), "%d/%m/%Y").date()
    print("data fine? gg/mm/YYYY  oppure scrivi: oggi")
    data_inserita = input()
    if (data_inserita == "oggi"):
        endDate = datetime.datetime.now().date()
    else:
        endDate = datetime.datetime.strptime(data_inserita, "%d/%m/%Y").date()

    # invoices tipo [number, friendlyName, Date, Amount, tipo)
    invoices = db.getRowsNameAndDateAndAmount(friendlyNameUtenza, startDate, endDate)
    print(invoices)
    # invoice: [number, friendlyName, Date, Amount, tipo)
    total = 0
    dateformat = "%d-%m-%Y"

    if OUTPUT_ON_DESKTOP==0:
        outputFolder = BASE_DIR.joinpath(friendlyNameUtenza+'- da '+startDate.strftime(dateformat)+' a '+endDate.strftime(dateformat))
    else:
        outputFolder = DESKTOP_DIR.joinpath(friendlyNameUtenza+'- da '+startDate.strftime(dateformat)+' a '+endDate.strftime(dateformat))
    # creo cartella output
    print(outputFolder)
    Path(outputFolder).mkdir(parents=True, exist_ok=True)

    recap_text = "Riassunto spese luce e gas da: "+str(startDate.strftime("%d/%m/%Y")) + ' a ' + str(endDate.strftime("%d/%m/%Y")) + '\n'
    for invoice in invoices:
        number = invoice[0]
        friendlyName = str(invoice[1])
        # converto la data in formato nostro con trattini
        date = str(datetime.datetime.strptime(invoice[2], "%Y-%m-%d").date().strftime("%d-%m-%Y"))
        tipo = str(invoice[4])
        print("\nutenza: "+ friendlyName)
        print("data: "+ date)
        print("totale bolletta: €"+str(invoice[3]))
        print("tipo: " + tipo)
        amount = float(invoice[3])
        total = total + amount
        pdfPath = getPdfPath(friendlyName, tipo, number, date)
        pdfPathNew = outputFolder.joinpath(tipo)
        print(pdfPathNew)

        recap_text = recap_text + "\nBolletta " + tipo + ' del ' + date + ': €' + str(amount)

        # creo cartella output
        Path(pdfPathNew).mkdir(parents=True, exist_ok=True)
        if pdfPath is not None:
            date = str(datetime.datetime.strptime(invoice[2], "%Y-%m-%d").date().strftime(bollette_output_dateformat))
            copyfile(str(pdfPath), pdfPathNew.joinpath(getPdfName(date)))

    print("\ntotale bollette: €"+ str(round(total,2)))
    recap_text = recap_text + "\n\nTOTALE:€ " + str(round(total, 2))
    # scrivo nel file il recap delle bollette
    with open(outputFolder.joinpath("riassunto spese.txt"), "w") as file:
        file.write(recap_text)

if select == 2:
    print("trascina qui la cartella o il file pdf da aggiungere al database poi premi invio")
    PdfParser.parsePDF(input())





