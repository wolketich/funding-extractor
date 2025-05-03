import pandas as pd
from datetime import datetime, timedelta

def process_funding_periods(file_path: str, claim_until_str: str = "17/08/2025"):
    # Завантаження даних
    df = pd.read_excel(file_path)
    df = df[['Allocation Description', 'Allocation Date']].dropna()

    # Обробка: витяг годин і конвертація дат
    def parse_allocation(row):
        hours = float(row['Allocation Description'].split(" ")[0])
        sunday = datetime.strptime(row['Allocation Date'], "%d/%m/%Y")
        monday = sunday - timedelta(days=6)
        return pd.Series([hours, monday.date(), sunday.date()], index=["Hours", "StartDate", "EndDate"])

    df_parsed = df.apply(parse_allocation, axis=1)
    df_parsed.sort_values("StartDate", inplace=True)
    df_parsed.reset_index(drop=True, inplace=True)

    # Межі CHICK
    chick_end = datetime.strptime(claim_until_str, "%d/%m/%Y").date()
    chick_start = chick_end - timedelta(weeks=52) + timedelta(days=1)

    # Фільтрація періодів
    df_filtered = df_parsed[
        (df_parsed["StartDate"] <= chick_end) & (df_parsed["EndDate"] >= chick_start)
    ].copy()

    # Обрізка по межах CHICK
    df_filtered["StartDate"] = df_filtered["StartDate"].apply(lambda d: max(d, chick_start))
    df_filtered["EndDate"] = df_filtered["EndDate"].apply(lambda d: min(d, chick_end))

    # Групування підряд періодів з однаковими годинами
    grouped = []
    current_group = {
        "Start Date": df_filtered.loc[0, "StartDate"].strftime("%d/%m/%Y"),
        "End Date": df_filtered.loc[0, "EndDate"].strftime("%d/%m/%Y"),
        "Weekly Hours": df_filtered.loc[0, "Hours"]
    }

    for i in range(1, len(df_filtered)):
        row = df_filtered.loc[i]
        prev_row = df_filtered.loc[i - 1]
        if row["Hours"] == current_group["Weekly Hours"] and row["StartDate"] == prev_row["StartDate"] + timedelta(days=7):
            current_group["End Date"] = row["EndDate"].strftime("%d/%m/%Y")
        else:
            grouped.append(current_group)
            current_group = {
                "Start Date": row["StartDate"].strftime("%d/%m/%Y"),
                "End Date": row["EndDate"].strftime("%d/%m/%Y"),
                "Weekly Hours": row["Hours"]
            }
    grouped.append(current_group)

    result_df = pd.DataFrame(grouped)
    return result_df

# Приклад використання:
if __name__ == "__main__":
    input_path = "test.xlsx"  # змінити на шлях до вашого файлу
    output_df = process_funding_periods(input_path)
    output_df.to_csv("funding_periods_filtered.csv", index=False)
    print("Saved to funding_periods_filtered.csv")