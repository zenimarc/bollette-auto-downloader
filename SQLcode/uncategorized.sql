SELECT * 
FROM bollette
WHERE bollette.Number NOT IN(
SELECT Number
FROM PODname INNER JOIN bollette
ON bollette.POD = PODname.POD)
