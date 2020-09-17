import sqlite3
from sqlite3 import Error
from pathlib import Path
from bollette.Invoice import Invoice

BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR.joinpath("SQLcode/")


class Sqlite:
    def __init__(self):
        self.conn = create_connection("db.db")

    def create_invoice(self, invoice_tuple):
        """
        Create a new project into the projects table
        :param conn:
        :param invoice_tuple:
        :return: invoice id or None in case of exception
        """
        sql = ''' INSERT INTO bollette(Provider, AccountID, POD, Number, Date, Amount, InstallationType)
                  VALUES(?,?,?,?,?,?,?) '''
        try:
            cur = self.conn.cursor()
            cur.execute(sql, invoice_tuple)
            self.conn.commit()
            return cur.lastrowid
        except Exception as e:
            #print(e)
            return None

    def update_invoice(self, invoice_tuple):

        sql = ''' UPDATE bollette
                  SET Provider = ? ,
                      AccountID = ? ,
                      POD = ?,
                      Date = ?,
                      Amount = ?,
                      InstallationType = ?
                  WHERE Number = ?'''
        try:
            cur = self.conn.cursor()
            cur.execute(sql, invoice_tuple)
            self.conn.commit()
        except Exception as e:
            #print(e)
            return None

    def getFriendlyNameList(self):
        try:
            with open(SQL_DIR.joinpath("getFriendlyNameList.sql"), "r") as f:
                sql = f.read()
                f.close()
                return self.conn.cursor().execute(sql).fetchall()
        except Exception as e:
            print(e)
            return None

    #restituisce [number, friendlyName, Date, Amount, tipo)
    def getRowsNameAndDateAndAmount(self, friendlyName, startDate, endDate):
        try:
            with open(SQL_DIR.joinpath("getRowsNameAndDateAndAmount.sql"), "r") as f:
                sql = f.read()
                f.close()
                return self.conn.cursor().execute(sql, (friendlyName, str(startDate), str(endDate))).fetchall()
        except Exception as e:
            print(e)
            return None
    #restituisce [friendlyname, type]
    def getFriendlyNameAndTypeFromProviderAndNumber(self, provider, number):
        try:
            with open(SQL_DIR.joinpath("getFriendlyNameAndTypeFromProviderAndNumber.sql"), "r") as f:
                sql = f.read()
                f.close()
                return self.conn.cursor().execute(sql, (provider, int(number))).fetchone()
        except Exception as e:
            print(e)
            return None

    #restituisce [friendlyname, type]
    def getFriendlyNameAndTypeFromPod(self, pod):
        try:
            with open(SQL_DIR.joinpath("getFriendlyNameAndTypeFromPod.sql"), "r") as f:
                sql = f.read()
                f.close()
                return self.conn.cursor().execute(sql, (pod,)).fetchone()
        except Exception as e:
            print(e)
            return None




def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return conn