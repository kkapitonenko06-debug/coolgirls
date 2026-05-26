from pathlib import Path

import pandas as pd

ROOT     = Path(__file__).parent
OUT_DIR  = ROOT / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "competitor_benchmark.csv"


OUR_DRINKS = [
    {"drink_name": "Молочный чай с тапиокой",  "cost_rub": 84.7,  "our_price_rub": 250, "type": "Молочный/тапиока"},
    {"drink_name": "Клубничный Фруктовый",    "cost_rub": 90.6,  "our_price_rub": 270, "type": "Фруктовый/тапиока"},
    {"drink_name": "Габа Улун с Пудингом",    "cost_rub": 102.8, "our_price_rub": 310, "type": "Молочный/пудинг"},
    {"drink_name": "Матча Латте с Тапиокой",  "cost_rub": 115.6, "our_price_rub": 350, "type": "Матча/тапиока"},
    {"drink_name": "Кокосовый Крем Чай",      "cost_rub": 135.8, "our_price_rub": 410, "type": "Кремовый/желе"},
]

#Цены конкурентов. Источники: Lenta.ru (июль 2024), irecommend.ru, restoclub.ru

COMPETITORS = [
    #(конкурент, сегмент, напиток, цена, тип напитка)
    ("Pretty Bubble Tea", "бюджет",  "Чай черный манго-маракуйя",          300, "Фруктовый"),
    ("Pretty Bubble Tea", "бюджет",  "Чай в чайниках",                      300, "Чай базовый"),
    ("PIMS Tea",          "средний", "Матча с жасмином и молоком",           300, "Матча/молочный"),
    ("One Price Coffee",  "бюджет",  "Питахайя-малина",                      350, "Фруктовый"),
    ("One Price Coffee",  "бюджет",  "Матча",                                350, "Матча"),
    ("One Price Coffee",  "бюджет",  "Каркаде-клубника",                     350, "Фруктовый"),
    ("Zin Tea",           "бюджет",  "Жасминовый чай с личи",               360, "Фруктовый/чай"),
    ("Zin Tea",           "бюджет",  "Традиционный черный молочный чай",    360, "Молочный"),
    ("Zin Tea",           "бюджет",  "Рисовый чай",                          360, "Чай базовый"),
    ("Zin Tea",           "бюджет",  "Молочный чай каштановый",              390, "Молочный"),
    ("Nova",              "бюджет",  "Матча с черной тапиокой",              390, "Матча/тапиока"),
    ("Nova",              "бюджет",  "ЧТК с карамелью и тапиокой",          390, "Молочный/тапиока"),
    ("Nova",              "бюджет",  "Таро",                                 390, "Молочный/тапиока"),
    ("PIMS Tea",          "средний", "Кофе Гейша с шоколадным желе",        400, "Кремовый/желе"),
    ("Teahiro",           "средний", "Боба кофе Классика",                   415, "Кофейный/тапиока"),
    ("Dav Bubble Tea",    "средний", "Матча",                                450, "Матча/тапиока"),
    ("Dav Bubble Tea",    "средний", "Классический",                         450, "Молочный/тапиока"),
    ("Dav Bubble Tea",    "средний", "Зеленая дыня",                         450, "Фруктовый"),
    ("Chicha San Chen",   "средний", "Черный чай с кассией и муссом",       440, "Молочный/мусс"),
    ("Jinju",             "средний", "Мокко с карамельной тапиокой",         490, "Кофейный/тапиока"),
    ("Jinju",             "средний", "Таро с карамельной тапиокой",          490, "Молочный/тапиока"),
    ("Jinju",             "средний", "Черный чай с яичным кремом и кокосом",500, "Кремовый"),
    ("Teahiro",           "средний", "Йогурт-Манго",                         495, "Фруктовый/йогурт"),
    ("PIMS Tea",          "премиум", "Extra Lime с листьями каффир-лайма",   500, "Фруктовый/чай"),
    ("Won Cha",           "премиум", "Жасминовый молочный чай с личи",       480, "Молочный/фруктовый"),
    ("Teahiro",           "премиум", "Йогурт-Клубника",                      525, "Фруктовый/йогурт"),
    ("Teahiro",           "премиум", "Чиззо Манго",                          555, "Фруктовый/кремовый"),
    ("Chicha San Chen",   "премиум", "Манговый пирог с муссом",              570, "Фруктовый/мусс"),
    ("Chicha San Chen",   "премиум", "Тропический сливочный чай",            570, "Кремовый"),
    ("J'Pan",             "премиум", "Матча с кокосовым молоком и манго",    550, "Матча/кремовый"),
    ("J'Pan",             "премиум", "Монблан с муссом и каштаном",          550, "Кремовый"),
    ("PIMS Tea",          "премиум", "Момо с кокейча и кремом",              550, "Кремовый/фруктовый"),
    ("Won Cha",           "премиум", "Синий чай",                            540, "Чай базовый"),
    ("Won Cha",           "премиум", "Молоко с яичным пудингом",             570, "Молочный/пудинг"),
    ("Won Cha",           "премиум", "Дальгона Мята",                        770, "Кремовый премиум"),
    ("Won Cha",           "премиум", "Дальгона Какао-Мята",                  810, "Кремовый премиум"),
]


def build_market_stats(competitors):
    df = pd.DataFrame(competitors, columns=[
        "competitor", "segment", "drink_name", "price_rub", "type"
    ])
    return df

def print_market_overview(df):
    print("\n" + "=" * 65)
    print("Рынок бабл-ти, г. Москва, ценовые сегменты")
    print("=" * 65)

    overall_min    = df["price_rub"].min()
    overall_max    = df["price_rub"].max()
    overall_median = df["price_rub"].median()
    overall_mean   = df["price_rub"].mean()

    print(f"\n  Всего позиций в выборке: {len(df)}")
    print(f"  Конкурентов:             {df['competitor'].nunique()}")
    print(f"  Диапазон цен:            {overall_min:.0f} – {overall_max:.0f} ₽")
    print(f"  Медианная цена:          {overall_median:.0f} ₽")
    print(f"  Средняя цена:            {overall_mean:.0f} ₽")

    print(f"\n  {'Сегмент':<12} {'Позиций':>8}  {'Мин':>6}  {'Медиана':>8}  {'Макс':>6}  {'Конкуренты'}")
    print("  " + "-" * 62)
    for seg, grp in df.groupby("segment", sort=False):
        names = ", ".join(grp["competitor"].unique())
        print(f"  {seg:<12} {len(grp):>8}  {grp['price_rub'].min():>5.0f}₽"
              f"  {grp['price_rub'].median():>7.0f}₽  {grp['price_rub'].max():>5.0f}₽  {names}")

def print_our_positioning(our_drinks, df):
    print("\n" + "=" * 65)
    print("Наше позиционирование на рынке")
    print("=" * 65)

    market_min    = df["price_rub"].min()
    market_median = df["price_rub"].median()
    market_max    = df["price_rub"].max()
    budget_max    = df[df["segment"] == "бюджет"]["price_rub"].max()
    mid_max       = df[df["segment"] == "средний"]["price_rub"].max()

    fmt = "{:<28}  {:>8}  {:>10}  {:>8}  {}"
    print(f"\n  {fmt.format('Наш напиток', 'Цена, ₽', 'vs медиана', 'Сегмент', 'Ближайший конкурент')}")
    print("  " + "-" * 75)

    for drink in our_drinks:
        price = drink["our_price_rub"]
        vs_median = (price - market_median) / market_median * 100

        if price <= budget_max:
            segment = "бюджет"
        elif price <= mid_max:
            segment = "средний"
        else:
            segment = "премиум"

#Ближайший конкурент по цене
        closest = df.iloc[(df["price_rub"] - price).abs().argsort()[:1]]
        nearest = f"{closest['competitor'].values[0]} ({closest['price_rub'].values[0]:.0f}₽)"

        arrow = "↓" if vs_median < 0 else "↑"
        print(f"  {fmt.format(drink['drink_name'], f'{price}₽', f'{arrow}{abs(vs_median):.0f}% медианы', segment, nearest)}")

    print(f"\n  Медиана рынка: {market_median:.0f} ₽  |  "
          f"Бюджет: до {budget_max:.0f} ₽  |  "
          f"Средний: до {mid_max:.0f} ₽  |  "
          f"Премиум: от {mid_max+1:.0f} ₽")

def print_margin_at_market_price(our_drinks, df):
    print("\n" + "=" * 65)
    print("МАРЖА ПРИ РЫНОЧНЫХ ЦЕНАХ")
    print("=" * 65)
    market_median = df["price_rub"].median()
    budget_median = df[df["segment"] == "бюджет"]["price_rub"].median()

    fmt = "{:<28}  {:>8}  {:>10}  {:>10}  {:>10}"
    print(f"\n  {fmt.format('Напиток', 'Себест.', 'При бюдж.ц.', 'При рын.ц.', 'При нашей ц.')}")
    print("  " + "-" * 72)

    for drink in our_drinks:
        cost = drink["cost_rub"]
        margin_budget = (budget_median - cost) / budget_median * 100
        margin_market = (market_median - cost) / market_median * 100
        margin_ours   = (drink["our_price_rub"] - cost) / drink["our_price_rub"] * 100
        col1 = f"{cost:.0f}₽"
        col2 = f"{margin_budget:.0f}% ({budget_median:.0f}₽)"
        col3 = f"{margin_market:.0f}% ({market_median:.0f}₽)"
        col4 = f"{margin_ours:.0f}% ({drink['our_price_rub']}₽)"
        print(f"  {fmt.format(drink['drink_name'], col1, col2, col3, col4)}")


def main():
    df = build_market_stats(COMPETITORS)
    df.to_csv(OUT_PATH, index=False)

    print_market_overview(df)
    print_our_positioning(OUR_DRINKS, df)
    print_margin_at_market_price(OUR_DRINKS, df)

    print(f"\nФайл сохранен")

if __name__ == "__main__":
    main()
