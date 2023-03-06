
import os
from pathlib import Path
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from adjustText import adjust_text
import warnings


# global settings
warnings.filterwarnings("ignore")
plt.rcParams.update({"font.size": 20})

g18 = [
    "USA", "CHN", "JPN", "DEU", "GBR", "IND",
    "FRA", "ITA", "CAN", "KOR", "RUS", "AUS",
    "BRA", "ESP", "MEX", "IND", "SAU", "CHE"]

folder_path = Path(os.path.dirname(__file__), "data")

# loading country codes lookup
code_country = pd.read_excel(
    folder_path / "country_codes_ISO_3166-1_alpha-3.xlsx",
    names=["code", "country"], usecols=[0, 1])

code_country = code_country.set_index("code").to_dict()["country"]
code_country = {k: v.lower() for k,v in code_country.items()}
code_country["DEU"] = "germany"
code_country["EURO"] = code_country["EA19"] = "euro zone"
country_code = {v: k for k, v in code_country.items()}

# loading exchange rates data
exchange_rates_temp = pd.read_csv(folder_path / "exchange_rates.csv",
    header=0, usecols=["LOCATION", "TIME", "Value"])
exchange_rates_temp = exchange_rates_temp.rename(
    columns={
        "LOCATION": "code",
        "TIME": "year",
        "Value": "exchange_rate"
    })
exchange_rates_temp.code = exchange_rates_temp.code.replace("EU27_2020", "EURO")

# preprocessing exchange rates 
years = list(set(exchange_rates_temp["year"]))
codes = list(set(exchange_rates_temp["code"]))

exchange_rates = pd.DataFrame([], columns=years, index=codes)

for code in codes:

    for year in years:

        mask = (exchange_rates_temp["year"].eq(year) & exchange_rates_temp["code"].eq(code))
        rate = exchange_rates_temp[mask]["exchange_rate"].values

        # converting all to US$
        if code == "USA":
            exchange_rates.at[code, year] = rate[0] if len(rate) else np.nan
        else:
            exchange_rates.at[code, year] = 1 / rate[0] if len(rate) else np.nan

for code in exchange_rates.index:
    exchange_rates.at[code, "country"] = code_country[code]

exchange_rates = exchange_rates[list(range(1994, 2022))]
exchange_rates = exchange_rates[exchange_rates.index.isin(g18)]
    

# loading and preprocessing government debt data
gov_debt = pd.read_excel(folder_path / "central_government_debt.xlsx", header=0)
gov_debt = gov_debt.rename(columns={
    "Central Government Debt (Percent of GDP)": "country"})

gov_debt.country = gov_debt.country.str.lower()

for country in gov_debt.country:
    gov_debt.at[gov_debt["country"].eq(country), "code"] = country_code[country.lower().strip()]

gov_debt = gov_debt.set_index("code")
gov_debt = gov_debt[gov_debt.index.isin(g18)]
gov_debt = gov_debt[list(range(1994, 2022))]
gov_debt.columns = list(map(int, gov_debt.columns))

# scaling data
exchange_rates_scaled = exchange_rates.copy()
for col in range(1994, 2021):
  
    X = exchange_rates_scaled[col].values.astype(float)
    X_not_null = X[~np.isnan(X)]
    X_min, X_max = min(X_not_null), max(X_not_null)
    exchange_rates_scaled[col] = (X - X_min) / (X_max - X_min) # 0 - 1 (relativo à US$ base 2021)

gov_debt_scaled = gov_debt.copy()
for col in range(1994, 2022):

    X = gov_debt_scaled[col].values.astype(float)
    X_not_null = X[~np.isnan(X)]
    X_min, X_max = min(X_not_null), max(X_not_null)
    gov_debt_scaled[col] = (X - X_min) / (X_max - X_min) # 0 - 1 (relativo à US$ base 2021)

# interpolation (NaN)
gov_debt_scaled.at["IND", 1997] = (gov_debt_scaled.loc["IND", 1996] + gov_debt_scaled.loc["IND", 1998]) / 2


# initialize plot
plt.ion()
fig = plt.figure(figsize=(19.18, 9.58))
plt.grid(color="gray", linestyle=":", linewidth=0.5)

# initialize paths tracker
paths = {}

# filter desired countries
g18 = [code for code in list(code_country.keys()) if code in exchange_rates_scaled.index]

for year in range(1994, 2022):

    annotations, texts, euro_zone = [], [], []
    euro_rate = None
    euro_zone_xmin = 1
    euro_zone_xmax = 0

    for i, code in enumerate(g18):

        # get country exchange rate and debt
        rate = exchange_rates_scaled.loc[code, year]
        debt = gov_debt_scaled.loc[code, year]

        if code not in paths:
            paths[code] = {"x": [], "y": [], "color": "black"}

        euro_zone = any([
            code == "DEU" and year >= 1998, # Alemanha, França, Espanha e Itália: adoção ao bloco econômico: 1 de janeiro de 1999 (fechamento do ano 1998)
            code == "FRA" and year >= 1998,
            code == "ESP" and year >= 1998,
            code == "ITA" and year >= 1998
        ])

        if euro_zone:
            euro_zone_xmin = min(debt, euro_zone_xmin)
            euro_zone_xmax = max(debt, euro_zone_xmax)
            euro_rate = rate

        if code == "GBR": code = "GBR (libra)"

        if code == "BRA": color = "#009c3b"; size = 200
        elif code == "USA": color = "#002868"; size = 200
        elif code == "CHN": color = "#EE1C25"; size = 200
        else: color = "black"; size = 130

        annotations += [(debt, rate, code, color, size)]

        # updating paths tracker
        if code in ["BRA", "USA", "CHN"]:
            
            paths[code]["x"].append(debt)
            paths[code]["y"].append(rate)
            paths[code]["color"] = color

    # clean the current figure and refresh
    plt.clf()

    plt.title(year, fontsize=30)

    for debt, rate, code, color, size in annotations:
      
        plt.scatter(x=debt, y=rate, c=color, marker="o", s=size, alpha=0.7)
        texts += [plt.text(debt, rate, code)]

        # tracking evolution
        if code in paths.keys():
            plt.plot(paths[code]["x"], paths[code]["y"], color=color, alpha=0.5, markersize=10)

    adjust_text(texts, only_move={"points": "y", "texts": "y"})

    plt.ylabel("Poder de compra internacional (US$ base 2021)")
    plt.ylim(-0.1, 1.6)

    plt.xlabel("Dívida pública")
    plt.xlim(-0.1, 1.1)

    if year >= 1998:
        plt.axhline(euro_rate, xmin=euro_zone_xmin, xmax=euro_zone_xmax, linestyle="--")

    if not i:
        plt.show()
    else:
        fig.canvas.draw()
    
    plt.pause(0.4) # don't rush
