SELECT Number, friendlyName, Date, Amount, tipo
FROM bollette INNER JOIN PODname
ON bollette.POD == PODname.POD
WHERE PODname.friendlyName == ? AND (Date BETWEEN ? AND ?);