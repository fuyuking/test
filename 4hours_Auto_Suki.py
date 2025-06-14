import requests
import json
import traceback
import time
from datetime import datetime, timedelta

####################################################
# フォロワーの記事をいいねを押すスクリプト
####################################################

####################################################
# Variable
####################################################
user_name = "dongmu"
email_address = "fuyuki1974@gmail.com"
password = "nfuyuki55"

# スキ実行間隔（秒）
sleep_time = 1

####################################################
# Function 
####################################################

# noteの認証を実施する
def note_auth(session):
    
    user_data = {
        "login":    email_address,
        "password": password
    }

    # 認証
    url = 'https://note.com/api/v1/sessions/sign_in'
    r = session.post(url, json=user_data)

    # ログインエラー判定
    r2 = json.loads(r.text)
    if "error" in r2:
        raise Exception("Login Error")
    else:
        return session

# APIからデータを取得する関数
def get_api_data(session, url, method="get", headers=""):
    # メソッド変更
    if method == "post":
        r = session.post(url, headers=headers)
    else:
        r = session.get(url, headers=headers)
    return r.json()

# 該当ユーザのフォロワー情報を出力する
def get_followers(session):
    
    followers = []
    page = 1

    while True:
        url = f'https://note.com/api/v2/creators/{user_name}/followers?page={page}'
        datas = get_api_data(session, url)
        for i in datas["data"]["follows"]:
            followers.append(i["urlname"])

        # 最終ページチェック
        if datas["data"]["isLastPage"]:
            break
        else:
            page += 1
    return followers

# フォロワーの記事データを一気に出力する
# 結果は記事IDで出力する
def get_article(session, followers):

    articles = []

    # 4時間前のUNIX時間を取得する
    n = datetime.now() - timedelta(hours=4)
    four_hours_ago = int(n.timestamp())

    for follower in followers:

        # フォロワーの記事を取得する
        url = f'https://note.com/api/v2/creators/{follower}/contents?kind=note'
        datas = get_api_data(session, url)

        for i in datas["data"]["contents"]:
            # 記事の発行日時を取得する
            n = datetime.fromisoformat(i["publishAt"])
            publish_time = int(n.timestamp())
            # 4時間以内に発行された記事であるかどうかをチェックする
            if publish_time > four_hours_ago:
                articles.append(i["key"])

    return articles

# 該当記事にスキを付与する
def hit_like(session, articles):
    for article in articles:
        url = f'https://note.com/api/v3/notes/{article}/likes'
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Content-Length': '0',
            'Te': 'trailers',
            'Host': 'note.com',
            'Origin': 'https://note.com',
        }
        datas = get_api_data(session, url, "post", headers)
        # 画面出力
        print(f'記事ID:{article} response:{datas}')
        # API負荷軽減のため
        time.sleep(sleep_time)

####################################################
# MAIN
####################################################
if __name__ == '__main__':
    try:
        now = datetime.now()
        print('---Start Script---')
        print(f'start :{now}')
        print('------')

        # sessionオブジェクト生成
        session = requests.session()

        # 認証
        session = note_auth(session)

        # フォロワー情報を取得する
        followers = get_followers(session)

        # 記事を取得する
        articles = get_article(session, followers)

        # 記事にスキをする
        hit_like(session, articles)

    except Exception as e:
        print(f'caught {type(e)}: {e}')
        print(traceback.format_exc())

    finally:
        finish = datetime.now()
        print(' ---Finish---')
        print(f'start :{finish}')
