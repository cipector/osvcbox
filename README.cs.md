# osvcbox

Jednoduchá Django aplikace pro měsíční přehled OSVČ.

## Spuštění

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Pak otevři `http://127.0.0.1:8000/` a přihlas se vytvořeným uživatelem.

## Testovací postup

1. Přihlas se. Při prvním přístupu se automaticky vytvoří pracovní prostor pro uživatele.
2. Otevři `Pracovní prostor` a nastav `default_daily_hours`, například `8.00`, a volitelnou výchozí sazbu.
3. Otevři `Klienti` a vytvoř klienta. Volitelně nastav klientskou výchozí sazbu.
4. Otevři `Projekty` a vytvoř projekt pod klientem. Volitelně nastav projektovou sazbu.
5. Otevři `Zapsat hodiny` a přidej záznam v aktuálním měsíci. Formulář předvyplní dnešní datum, 08:00-16:30 a odečtení 30 minut na oběd. Datum můžeš vybrat i v barevném kalendáři, kde jsou odlišené víkendy a české svátky.
6. Vrať se na `Přehled`.
7. V `Přehledu` vyber měsíc nebo rok, který chceš zobrazit. Výchozí je aktuální měsíc.
8. Otevři `Rozpis`, vyber měsíc a volitelně filtruj podle klienta nebo projektu.
9. Na stránce `Rozpis` použij `Export XLSX` pro export aktuálně vyfiltrovaných záznamů do Excelu. Soubor obsahuje jen datum, začátek, konec, součet hodin a poznámku.
10. Pokud se u zápisu spleteš, v `Rozpisu` klikni u záznamu na `Upravit`.
11. Tlačítkem se symbolem `◐` v horní liště přepneš vzhled webu. Volba zůstane uložená v prohlížeči.
12. Otevři `Platby` a přidej pravidelné platby. Aplikace z nich vygeneruje QR kód pro platbu a v přehledu je odečte od částky k fakturaci jako čistou částku po těchto nákladech.

Přehled zobrazuje vybraný měsíc nebo rok, pracovní fond pondělí až pátek bez českých státních svátků, odpracované hodiny vypočtené ze začátku a konce záznamu po případném odečtení 30 minut na oběd, fakturovatelné a nefakturovatelné hodiny, saldo, celkovou částku k fakturaci a rozpad podle zákazníků a projektů.
U fondu přehled vypisuje i počet svátků, které snižují fond, včetně jejich data.

Hodinová sazba se může lišit podle projektu nebo klienta. Sazba pro fakturaci se bere v pořadí: `Project.hourly_rate_czk`, `Client.default_hourly_rate_czk`, `Workspace.default_hourly_rate_czk`, jinak `0`.
