from google.oauth2.service_account import Credentials
import gspread
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

# ======================================
# ラーメンDBの情報をスクレイピングする関数
# ======================================
def fetch_ramen_info(url):
    """
    ラーメンDBの店舗ページURLから
    店名、住所(郵便番号、都道府県、市区町村等)、電話番号、定休日、座席数、アクセス、駐車場、開店日などを取得し
    dict で返すサンプル関数。
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # ------------------------------
        # 店名 (例: <h1 itemprop="name" class="p-reservation-shopName">〇〇</h1>)
        # ------------------------------
        name_tag = soup.select_one('h1[itemprop="name"]')
        shop_name = name_tag.get_text(strip=True) if name_tag else ""

        # ------------------------------
        # 住所 (例: <p class="address">〒123-4567<br>東京都〇〇市…</p>)
        # ------------------------------
        address_tag = soup.select_one('p.address')
        address_str = address_tag.get_text(separator=' ', strip=True) if address_tag else ""
        # 例: address_str = "〒958-0261 新潟県村上市小岩内33-1" のような文字列になる想定

        # 郵便番号を取得 (「〒xxxx-xxxx」の形を想定)
        postal_code = ""
        if address_str.startswith("〒"):
            # 「〒」を取り除いてから、最初の空白区切り(あるいは改行)までを郵便番号とみなす例
            # 例: "958-0261 新潟県…" の形になるので split() で取り出し
            splitted = address_str[1:].split(maxsplit=1)  # [ "958-0261", "新潟県村上市…"]
            if splitted:
                postal_code = splitted[0]  # "958-0261"
            # address_str の先頭部分(〒＋郵便番号)を取り除いて再度整形
            address_str = address_str.replace("〒" + postal_code, "").strip()

        # ここで address_str 例: "新潟県村上市小岩内33-1" など
        prefecture = ""
        city = ""
        street = ""
        # 正規表現を用いて都道府県を抽出 (東京都、北海道、京都府、大阪府、XX県)
        match = re.search(r'(東京都|北海道|(?:京都|大阪)府|.{1,3}県)(.*)', address_str)
        if match:
            prefecture = match.group(1).strip()
            remainder = match.group(2).strip()
            # remainder 例: "村上市小岩内33-1"
            # ここでは、残りをそのまま city に入れて street は空にする例
            # 実運用では細かく区・市・町・番地などをさらに正規表現で切り分けることを検討
            city = remainder
        else:
            # マッチしない場合は全体を city にする例
            city = address_str

        # ------------------------------
        # 電話番号・定休日・座席数・アクセス・駐車場・開店日など
        # (例: <ul class="shop-detail-info"><li>電話番号: 〇〇</li><li>定休日: …</li></ul>)
        # ------------------------------
        phone = ""
        holiday = ""
        seats = ""
        access = ""
        parking = ""
        open_date = ""

        detail_list = soup.select("ul.shop-detail-info li")
        for li in detail_list:
            text = li.get_text(strip=True)
            # text 例: "電話番号: 075-xxx-xxxx"
            if ":" not in text:
                continue
            label, value = text.split(":", 1)
            label = label.strip()
            value = value.strip()
            if label == "電話番号":
                phone = value
            elif label == "定休日":
                holiday = value
            elif label == "座席数":
                seats = value
            elif label == "アクセス":
                access = value
            elif label == "駐車場":
                parking = value
            elif label == "開店日":
                open_date = value
            # その他「営業時間」などがあれば同様に処理可能

        # まとめて返す
        return {
            "shop_name": shop_name,
            "postal_code": postal_code,
            "prefecture": prefecture,
            "city": city,      # この例では都道府県以降すべてを city に格納
            "street": street,  # 余力があればさらに分割
            "phone": phone,
            "holiday": holiday,
            "seats": seats,
            "access": access,
            "parking": parking,
            "open_date": open_date
        }

    except Exception as e:
        print(f"情報の取得中にエラーが発生しました: {e}")
        # 取得失敗時は空の辞書を返す
        return {}

# ======================================
# Spreadsheetを更新する関数
# ======================================
def update_spreadsheet():
    """
    Google Spreadsheet から A列(URL) を読み込み、
    ラーメンDBから情報をスクレイピングして C列以降に書き込む。
    シートの列構成は以下を想定(1行目はヘッダ):
       A: リンク
       B: 重複(OKなど)
       C: 更新年月日
       D: 店名
       E: 郵便番号
       F: 都道府県
       G: 区市町村(番地含む)
       H: (番地等をさらに分割したい場合用・今回は未使用)
       I: 電話番号
       J: 定休日
       K: 座席数
       L: アクセス
       M: 駐車場
       N: オープン日
    """

    # ------------------------------
    # 1. Google Spreadsheet に接続
    # ------------------------------
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    credentials = Credentials.from_service_account_file(
        "PATH/TO/YOUR_SERVICE_ACCOUNT.json",  # サービスアカウントJSONファイルのパス
        scopes=scopes
    )
    gc = gspread.authorize(credentials)

    # SpreadsheetのURL
    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1MfMNO9MAwSFYFsn-jvaQxXyKnICx3sBORK7rqL0DdBM/edit?gid=1400209973#gid=1400209973"  # 実際のURLを指定
    spreadsheet = gc.open_by_url(spreadsheet_url)

    # シート名 (例：「ラーメン店」)
    worksheet = spreadsheet.worksheet("ラーメン店")

    # ------------------------------
    # 2. シートのデータを取得
    # ------------------------------
    all_data = worksheet.get_all_values()
    if not all_data:
        print("シートにデータがありません。")
        return

    # A列：URL が含まれる2行目以降を処理
    for row_idx, row_data in enumerate(all_data[1:], start=2):
        url = row_data[0].strip()  # A列（0番目）にURL

        if not url:
            # URLが空ならスキップ
            continue

        print(f"[{row_idx}行目] URL({url})から情報を取得中...")
        info = fetch_ramen_info(url)

        if not info:
            print(f"取得エラーのためスキップ: {url}")
            continue

        # ------------------------------
        # 3. スプレッドシート更新
        # ------------------------------
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # C列: 更新日時
        worksheet.update_cell(row_idx, 3, now_str)

        # D列: 店名
        worksheet.update_cell(row_idx, 4, info["shop_name"])
        # E列: 郵便番号
        worksheet.update_cell(row_idx, 5, info["postal_code"])
        # F列: 都道府県
        worksheet.update_cell(row_idx, 6, info["prefecture"])
        # G列: 区市町村(本サンプルでは番地含む)
        worksheet.update_cell(row_idx, 7, info["city"])
        # H列: (street) 今回は空のままにしておく例
        worksheet.update_cell(row_idx, 8, info["street"])
        # I列: 電話番号
        worksheet.update_cell(row_idx, 9, info["phone"])
        # J列: 定休日
        worksheet.update_cell(row_idx, 10, info["holiday"])
        # K列: 座席数
        worksheet.update_cell(row_idx, 11, info["seats"])
        # L列: アクセス
        worksheet.update_cell(row_idx, 12, info["access"])
        # M列: 駐車場
        worksheet.update_cell(row_idx, 13, info["parking"])
        # N列: オープン日
        worksheet.update_cell(row_idx, 14, info["open_date"])

    print("Spreadsheetの更新が完了しました。")


# ------------------------------
# スクリプト実行
# ------------------------------
if __name__ == "__main__":
    update_spreadsheet()
