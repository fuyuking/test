from google.oauth2.service_account import Credentials
import gspread
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

# ======================================
# ���[����DB�̏����X�N���C�s���O����֐�
# ======================================
def fetch_ramen_info(url):
    """
    ���[����DB�̓X�܃y�[�WURL����
    �X���A�Z��(�X�֔ԍ��A�s���{���A�s�撬����)�A�d�b�ԍ��A��x���A���Ȑ��A�A�N�Z�X�A���ԏ�A�J�X���Ȃǂ��擾��
    dict �ŕԂ��T���v���֐��B
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # ------------------------------
        # �X�� (��: <h1 itemprop="name" class="p-reservation-shopName">�Z�Z</h1>)
        # ------------------------------
        name_tag = soup.select_one('h1[itemprop="name"]')
        shop_name = name_tag.get_text(strip=True) if name_tag else ""

        # ------------------------------
        # �Z�� (��: <p class="address">��123-4567<br>�����s�Z�Z�s�c</p>)
        # ------------------------------
        address_tag = soup.select_one('p.address')
        address_str = address_tag.get_text(separator=' ', strip=True) if address_tag else ""
        # ��: address_str = "��958-0261 �V��������s�����33-1" �̂悤�ȕ�����ɂȂ�z��

        # �X�֔ԍ����擾 (�u��xxxx-xxxx�v�̌`��z��)
        postal_code = ""
        if address_str.startswith("��"):
            # �u���v����菜���Ă���A�ŏ��̋󔒋�؂�(���邢�͉��s)�܂ł�X�֔ԍ��Ƃ݂Ȃ���
            # ��: "958-0261 �V�����c" �̌`�ɂȂ�̂� split() �Ŏ��o��
            splitted = address_str[1:].split(maxsplit=1)  # [ "958-0261", "�V��������s�c"]
            if splitted:
                postal_code = splitted[0]  # "958-0261"
            # address_str �̐擪����(���{�X�֔ԍ�)����菜���čēx���`
            address_str = address_str.replace("��" + postal_code, "").strip()

        # ������ address_str ��: "�V��������s�����33-1" �Ȃ�
        prefecture = ""
        city = ""
        street = ""
        # ���K�\����p���ēs���{���𒊏o (�����s�A�k�C���A���s�{�A���{�AXX��)
        match = re.search(r'(�����s|�k�C��|(?:���s|���)�{|.{1,3}��)(.*)', address_str)
        if match:
            prefecture = match.group(1).strip()
            remainder = match.group(2).strip()
            # remainder ��: "����s�����33-1"
            # �����ł́A�c������̂܂� city �ɓ���� street �͋�ɂ����
            # ���^�p�łׂ͍�����E�s�E���E�Ԓn�Ȃǂ�����ɐ��K�\���Ő؂蕪���邱�Ƃ�����
            city = remainder
        else:
            # �}�b�`���Ȃ��ꍇ�͑S�̂� city �ɂ����
            city = address_str

        # ------------------------------
        # �d�b�ԍ��E��x���E���Ȑ��E�A�N�Z�X�E���ԏ�E�J�X���Ȃ�
        # (��: <ul class="shop-detail-info"><li>�d�b�ԍ�: �Z�Z</li><li>��x��: �c</li></ul>)
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
            # text ��: "�d�b�ԍ�: 075-xxx-xxxx"
            if ":" not in text:
                continue
            label, value = text.split(":", 1)
            label = label.strip()
            value = value.strip()
            if label == "�d�b�ԍ�":
                phone = value
            elif label == "��x��":
                holiday = value
            elif label == "���Ȑ�":
                seats = value
            elif label == "�A�N�Z�X":
                access = value
            elif label == "���ԏ�":
                parking = value
            elif label == "�J�X��":
                open_date = value
            # ���̑��u�c�Ǝ��ԁv�Ȃǂ�����Γ��l�ɏ����\

        # �܂Ƃ߂ĕԂ�
        return {
            "shop_name": shop_name,
            "postal_code": postal_code,
            "prefecture": prefecture,
            "city": city,      # ���̗�ł͓s���{���ȍ~���ׂĂ� city �Ɋi�[
            "street": street,  # �]�͂�����΂���ɕ���
            "phone": phone,
            "holiday": holiday,
            "seats": seats,
            "access": access,
            "parking": parking,
            "open_date": open_date
        }

    except Exception as e:
        print(f"���̎擾���ɃG���[���������܂���: {e}")
        # �擾���s���͋�̎�����Ԃ�
        return {}

# ======================================
# Spreadsheet���X�V����֐�
# ======================================
def update_spreadsheet():
    """
    Google Spreadsheet ���� A��(URL) ��ǂݍ��݁A
    ���[����DB��������X�N���C�s���O���� C��ȍ~�ɏ������ށB
    �V�[�g�̗�\���͈ȉ���z��(1�s�ڂ̓w�b�_):
       A: �����N
       B: �d��(OK�Ȃ�)
       C: �X�V�N����
       D: �X��
       E: �X�֔ԍ�
       F: �s���{��
       G: ��s����(�Ԓn�܂�)
       H: (�Ԓn��������ɕ����������ꍇ�p�E����͖��g�p)
       I: �d�b�ԍ�
       J: ��x��
       K: ���Ȑ�
       L: �A�N�Z�X
       M: ���ԏ�
       N: �I�[�v����
    """

    # ------------------------------
    # 1. Google Spreadsheet �ɐڑ�
    # ------------------------------
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    credentials = Credentials.from_service_account_file(
        "PATH/TO/YOUR_SERVICE_ACCOUNT.json",  # �T�[�r�X�A�J�E���gJSON�t�@�C���̃p�X
        scopes=scopes
    )
    gc = gspread.authorize(credentials)

    # Spreadsheet��URL
    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1MfMNO9MAwSFYFsn-jvaQxXyKnICx3sBORK7rqL0DdBM/edit?gid=1400209973#gid=1400209973"  # ���ۂ�URL���w��
    spreadsheet = gc.open_by_url(spreadsheet_url)

    # �V�[�g�� (��F�u���[�����X�v)
    worksheet = spreadsheet.worksheet("���[�����X")

    # ------------------------------
    # 2. �V�[�g�̃f�[�^���擾
    # ------------------------------
    all_data = worksheet.get_all_values()
    if not all_data:
        print("�V�[�g�Ƀf�[�^������܂���B")
        return

    # A��FURL ���܂܂��2�s�ڈȍ~������
    for row_idx, row_data in enumerate(all_data[1:], start=2):
        url = row_data[0].strip()  # A��i0�Ԗځj��URL

        if not url:
            # URL����Ȃ�X�L�b�v
            continue

        print(f"[{row_idx}�s��] URL({url})��������擾��...")
        info = fetch_ramen_info(url)

        if not info:
            print(f"�擾�G���[�̂��߃X�L�b�v: {url}")
            continue

        # ------------------------------
        # 3. �X�v���b�h�V�[�g�X�V
        # ------------------------------
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # C��: �X�V����
        worksheet.update_cell(row_idx, 3, now_str)

        # D��: �X��
        worksheet.update_cell(row_idx, 4, info["shop_name"])
        # E��: �X�֔ԍ�
        worksheet.update_cell(row_idx, 5, info["postal_code"])
        # F��: �s���{��
        worksheet.update_cell(row_idx, 6, info["prefecture"])
        # G��: ��s����(�{�T���v���ł͔Ԓn�܂�)
        worksheet.update_cell(row_idx, 7, info["city"])
        # H��: (street) ����͋�̂܂܂ɂ��Ă�����
        worksheet.update_cell(row_idx, 8, info["street"])
        # I��: �d�b�ԍ�
        worksheet.update_cell(row_idx, 9, info["phone"])
        # J��: ��x��
        worksheet.update_cell(row_idx, 10, info["holiday"])
        # K��: ���Ȑ�
        worksheet.update_cell(row_idx, 11, info["seats"])
        # L��: �A�N�Z�X
        worksheet.update_cell(row_idx, 12, info["access"])
        # M��: ���ԏ�
        worksheet.update_cell(row_idx, 13, info["parking"])
        # N��: �I�[�v����
        worksheet.update_cell(row_idx, 14, info["open_date"])

    print("Spreadsheet�̍X�V���������܂����B")


# ------------------------------
# �X�N���v�g���s
# ------------------------------
if __name__ == "__main__":
    update_spreadsheet()
