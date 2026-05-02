import holidays


def czech_public_holidays(year):
    return set(czech_public_holidays_map(year))


def czech_public_holidays_map(year):
    return dict(holidays.country_holidays("CZ", years=[year], language="cs"))


def is_czech_business_day(day):
    return day.weekday() < 5 and day not in czech_public_holidays(day.year)
