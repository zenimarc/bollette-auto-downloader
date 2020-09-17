import PyPDF2
from pathlib import Path
import re
from bollette.Invoice import Invoice
from scraper import Sen
import os
from os.path import isfile, join

class PdfParser:
    def __init__(self):
        super()

    @staticmethod
    def parsePDF(path):
        """can take as input a directory path or a file path (as string) it will converts later to path"""
        # this removes " " generated when you drag and drop
        if '"' in str(path):
            cleaned_path = Path(path[:-1][1:])
        else:
            cleaned_path = Path(path)


        if cleaned_path.is_file():
            data_string = getDataStringFromPdf(cleaned_path)
            if data_string is not None:
                if getProvider(data_string) == "SEN":
                    Sen.processNewInvoice(path, data_string)

        if cleaned_path.is_dir():
            files_and_dir_list = os.listdir(cleaned_path)
            for file in files_and_dir_list:
                PdfParser.parsePDF(cleaned_path.joinpath(file))


def getDataStringFromPdf(path):
    """:returns a text string version of the pdf"""
    try:
        pdfFileObj = open(Path(path), 'rb')
        # pdf reader object
        pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
        # number of pages in pdf
        # print(pdfReader.numPages)
        # a page object
        pageObj = pdfReader.getPage(0)
        # extracting text from page.
        # this will print the text you can also save that into String
        s = pageObj.extractText()
        return s
    except Exception as e:
        print(e)
        return None

def getProvider(string):
    if ("Servizio di Maggior Tutela") in string:
        return "SEN"
