import random

def joke():
    jokes = [
        "プログラマーの好きなシューズは？\nアディダス（アディーダス）... 'ADD-ee-DAS'（ADDとDAS命令を連想させる）",
        "なぜコンピュータは歌がうまいの？\nだって、データをいつもメロディアス（melodious）に処理するから！",
        "なぜプログラマーはカフェインを摂取するの？\nだって、コードの実行速度を上げるためにオーバークロック（overclock）しないと！"
    ]
    return random.choice(jokes)

def main():
    print("笑いたいですか？(はい/いいえ)")
    user_response = input().lower()

    if user_response == "はい":
        print(joke())
    elif user_response == "いいえ":
        print("わかりました。次回お楽しみに！")
    else:
        print("入力が無効です。再度お試しください。")

if __name__ == "__main__":
    main()
