import datetime

date_format_sqlite = "%Y-%m-%d"

# notare che date + in formato data e non stringa
class Invoice:
    date: datetime.date

    def __init__(self, provider, accountID, pod, number, date, amount, pdfLink, installationType, paymentStatus=None):
        self.provider = provider
        self.accountID = accountID
        self.pod = pod
        self.number = number
        self.date = date
        self.amount = amount
        self.installationType = installationType
        self.paymentStatus = paymentStatus
        self.pdfLink = pdfLink

    def getSqlTuple(self):
        return self.provider, self.accountID, self.pod, int(str(self.number).lstrip("0")), self.date.strftime(
            date_format_sqlite), self.amount, self.installationType

    def getUpdateTuple(self):
        return self.provider, self.accountID, self.pod, self.date.strftime(
            date_format_sqlite), self.amount, self.installationType, self.number
