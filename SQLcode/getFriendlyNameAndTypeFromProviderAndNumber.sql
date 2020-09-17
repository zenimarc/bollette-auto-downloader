SELECT friendlyName, tipo
FROM bollette INNER JOIN PODname
ON bollette.POD == PODname.POD
WHERE bollette.Provider = ? AND bollette.Number = ?;