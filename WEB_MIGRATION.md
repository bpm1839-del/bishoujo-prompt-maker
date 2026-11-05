# WEBアプリ化のための引き継ぎ

このリポジトリは美少女プロンプトメーカー Ver.1.4 のWindows/Tkinter版です。WEB版はまだ実装していません。既存の動作・プリセット・保存形式を確認するための原本として利用できます。

## ファイルの役割

| ファイル | 役割 |
| --- | --- |
| app.py | Tkinter UIとJSON読込・保存、お気に入り、操作履歴。WEB化ではここを画面と状態管理へ置き換える |
| core.py | プリセット検証、単一選択グループ、矛盾警告、ランダム、強調度、英語生成、個別コピー文字列 |
| features.py | 衣装ごとの色指定、完成サイズと推奨生成サイズ、人物配置の定義 |
| defaults.json | 初期612件の日本語→英語辞書。ID・出力先・カテゴリ・排他グループ・強調度を持つ |
| models.json | モデルごとの前置・品質タグ・Negativeの初期プロファイル |
| prompt_help.py | 日本語翻訳索引、括弧・強調・改行を扱うタグ位置解析。Tkinterには依存しない |
| tooltips.py | Tkinter用ポップアップ。WEB側ではホバーUIへ置き換える |
| ui_style.py | Tkinterの配色と一覧グリッド線。WEB側ではCSS等へ置き換える |

## 維持する機能

Positive/Negativeの分離、既存5カテゴリ、選択・検索、追加・編集・複製・削除、強調度0.5〜1.5（0.1刻み）、項目ロック・ランダム、個別コピーと全文コピー、直接編集と上書き前確認、翻訳ツールチップ、お気に入り、選択中だけの表示、選択を戻す履歴。
年齢・身長・体型・バストサイズは各1件または指定なし。衣装の色は衣装ごとの設定とし、複合衣装は構成タグごとに色を選ぶ。旧「服の色」タグは互換用データとして残して通常非表示。

壁紙は完成サイズと最初の生成サイズを区別する。Forgeへ自動接続・自動送信する実装はありません。ユーザーが英語プロンプトと設定値を手動で渡す構造です。

## 保存形式と移行

Windows版はsession.json / favorites.json / presets.json / models.json / catalog.jsonをユーザー保存先へ保存します。追加翻訳は任意のtranslations.jsonです。実ユーザーの保存ファイルはこのリポジトリに含めていません。

- プリセットIDはお気に入り・選択・ロック・強調度の参照キーなので維持する。
- 作業schema_versionは3、辞書catalog versionは14。過去のフィールドがない場合は既存の既定値で補完する。
- colorsはclothing_colors: {preset_id: {original_english_atom: color_english}}。
- wallpaperは {size: サイズ選択肢の名前, placement: 配置選択肢の名前}。
- お気に入りには選択ID、ロック、強調度、モデル、生成設定、ランダム対象、英語本文、衣装色、壁紙設定を保存する。
- 利用者の既存データを初期化せず、WEB側へインポートする機能を設ける場合は明示操作にする。

## テスト

```text
python -m unittest discover -v
```

基本テスト63件はGUIなしで実行できます。test_gui*.pyはデスクトップ上のTkinterを必要とし、WEBのテストとは別です。tests内のJSONは過去に配布した初期辞書のテスト用フィクスチャです。

## 未実装の次回候補（Ver.1.4にはまだ追加していない）

- 瞳：detailed eyes / beautiful eyes / eye reflection。sparkling eyesは既存なので重複させない。
- 肌：smooth skin / soft skin / shiny skin / wet skin / detailed skin / skin pores / subsurface scattering。
- 画風：semi-realistic（補助翻訳辞書には訳があるが、初期プリセットとしては未追加）。
- 衣装：bra / lace bra / sports bra / frilled bra / strapless bra / bralette / seamless bra / floral print bra。

上記は会話で採用された候補の記録であり、この公開作業でコードや辞書へ追加したものではありません。
