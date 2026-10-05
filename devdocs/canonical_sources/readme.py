"""metamk の README の正本ソース。"""

from shikumi_devdoc.norms.common import canonical_source
from shikumi_devdoc.norms.document import test_target_field, title

quickstart_example = test_target_field("最小の例")
async_example = test_target_field("非同期の例")
phase_of_example = test_target_field("phase_of の例")
alias_example = test_target_field("別名の例")


@canonical_source(
    "{{project.name}}",
    filename="README.md",
    merge_policy="external",
    heading="title",
)
class README:
    r"""
    `{{project.name}}` は、テストのコードを **準備（PREPARE）・対象（MAIN）・検証（VERIFY）** の3つのフェーズに区切り、例外が通過したときに「どのフェーズで失敗したか」をその例外へ残す、ごく小さなライブラリです。

    区切りは `with` ブロックとして書くので、コードを読むだけで各部分の役割が分かります。実行時には何もしません。制御の流れを変えず、例外を握りつぶさず、置き換えません。

    > [!NOTE]
    > 現在の版 `{{project.version}}` は、設計を1からやり直した版です。この README が実装の基準です。実装の状況は [STATUS](https://github.com/minoru-jp/metamk/blob/main/STATUS.md)、旧版との違いは [CHANGELOG](https://github.com/minoru-jp/metamk/blob/main/CHANGELOG.md) を参照してください。
    """

    class SECTION_001:
        r"""
        テストの本体には、性質の異なる3種類のコードが混ざっています。

        - テスト対象を動かすための準備
        - 試したいことそのもの（テスト対象の呼び出し）
        - その結果の確認

        これらが区別されずに並んでいると、テストが失敗したとき、準備の不備なのか、対象の不具合なのか、期待のほうが誤っているのかを、トレースバックとコードを読み解いて判断することになります。読む側も、どの行が「本当に試したいこと」なのかを一目では判断できません。pytest はフィクスチャの失敗とテスト本体の失敗を区別しますが、テスト関数の内側までは区別しません。

        `{{project.name}}` は、この区別をコードの構造として書き表し、失敗した例外にも残します。
        """

        title @= "解決したいこと"

    class SECTION_002:
        r"""
        ```python
        {{quickstart_example}}
        ```

        `with Mk.VERIFY:` の中の `assert` が失敗すると（上の例で `result == 4` と書いた場合）、pytest の失敗表示には次のような行が加わります。

        ```text
        >           assert result == 4
        E           assert 3 == 4
        E           [metamk] failed in VERIFY
        ```

        `PREPARE` や `MAIN` で例外が出た場合も同様に、`failed in PREPARE`、`failed in MAIN` と表示されます。
        """

        title @= "最小の例"

        quickstart_example @= r"""
        from metamk import Mk


        def test_example():
            with Mk.PREPARE:
                data = {"x": 1, "y": 2}

            with Mk.MAIN:
                result = data["x"] + data["y"]

            with Mk.VERIFY:
                assert result == 3
        """

    class SECTION_003:
        r"""
        各フェーズは、目的ではなく **MAIN との位置関係** で定義します。

        | フェーズ | 位置 | 失敗したことの意味 |
        | --- | --- | --- |
        | `PREPARE` | MAIN より前。MAIN を実行できる状態を作る | テスト対象ではなく、環境かテストの書き方に問題がある |
        | `MAIN` | 試したいことそのもの。1つのテストに1つ | テスト対象が失敗した |
        | `VERIFY` | MAIN より後。MAIN の結果を確認する | 対象は動いたが、結果が期待と異なる |

        語彙を3つに絞ったのは、使い分けに迷う余地を減らすためです。`{{project.name}}` は、フェーズの順序も MAIN の個数も検査しません。「MAIN は1つ」「PREPARE、MAIN、VERIFY の順」は規約であり、強制はしません。
        """

        title @= "3つのフェーズ"

        class SECTION_004:
            r"""
            `with` ブロックは制御の流れを変えないので、MAIN で例外が出れば、後続のブロックには到達しません。そのため `CLEANUP` のような「必ず実行される区間」を連想させる名前を付けても、その期待を満たせません。後片付けには、pytest のフィクスチャや `try` / `finally` を使ってください。
            """

            title @= "後片付けのフェーズはありません"

    class SECTION_005:
        r"""
        フェーズのブロック（`with Mk.PREPARE:` など）は、次のとおり動作します。

        - ブロックが正常に終わったときは、何も起こりません。
        - 例外がブロックを通過したときは、その例外に (1) 通過したフェーズ名の記録と (2) 注記 `[metamk] failed in <phase>` の追加を行い、例外はそのまま再送出します。握りつぶさず、置き換えず、トレースバックも変えません。注記は `BaseException.add_note()` で追加します。
        - 例外が複数のフェーズを通過したとき（ブロックの入れ子など）は、最も内側のフェーズだけを記録し、注記は1回だけ付けます。
        - 同じ例外オブジェクトが後から別のフェーズを通過しても、記録は最初のフェーズのままです。
        - 例外の種類は問いません。`BaseException` を継承するものすべてが対象で、`asyncio.CancelledError` も含みます。
        - 記録や注記に失敗しても、元の例外の送出を妨げません。
        - 状態を持ちません。フェーズの順序や回数、現在どのフェーズにいるかを覚えず、検査もしません。
        """

        title @= "動作の約束"

    class SECTION_006:
        r"""
        `with` ブロックの中では `await` を使えるので、非同期コードのための別の API はありません（`async with` は不要です）。`{{project.name}}` 自身は何も `await` しません。

        ```python
        {{async_example}}
        ```

        状態を持たないため、複数のタスクやスレッドから同じ `Mk.MAIN` などを同時に使っても、互いに干渉しません。

        フェーズはデコレータとしては使えません。関数を飾る形式を単純に提供すると、非同期関数ではコルーチンを作った時点でブロックを抜けてしまい、記録が行われなくなるためです。
        """

        title @= "非同期コード"

        async_example @= r"""
        import asyncio

        from metamk import Mk


        async def test_async_example():
            with Mk.PREPARE:
                await asyncio.sleep(0)
                data = [1, 2, 3]

            with Mk.MAIN:
                await asyncio.sleep(0)
                total = sum(data)

            with Mk.VERIFY:
                assert total == 6
        """

    class SECTION_007:
        r"""
        例外に記録されたフェーズ名は `phase_of()` で取り出せます。人間が読む注記ではなく、pytest のレポートなどで機械的に扱いたい場合に使います。

        ```python
        {{phase_of_example}}
        ```

        `phase_of(exc)` は `"PREPARE"`、`"MAIN"`、`"VERIFY"` のいずれか、または記録がなければ `None` を返します。例外自身に記録がなければ `__cause__`、`__context__` の順に連鎖をたどり、最初に見つかった記録を返します（循環していても停止します）。

        連鎖をたどるのは、例外が別の例外へ変換されることがあるためです。たとえば `asyncio.timeout()` の内側にある MAIN が時間切れになると、MAIN を通過した `CancelledError` は、外側で `TimeoutError` に変換されます。変換後の例外には記録が付きませんが、元の例外が `__context__` に残るので、`phase_of()` は `"MAIN"` を返せます。
        """

        title @= "フェーズ名を取り出す"

        phase_of_example @= r"""
        from metamk import Mk, phase_of

        try:
            with Mk.MAIN:
                raise ValueError("boom")
        except ValueError as e:
            assert phase_of(e) == "MAIN"
        """

    class SECTION_008:
        r"""
        `Mk.PREPARE` などは単なる属性なので、使う側で別名を付けられます。

        ```python
        {{alias_example}}
        ```

        記録されるフェーズ名は、別名に関係なく `"PREPARE"`、`"MAIN"`、`"VERIFY"` です。
        """

        title @= "別名を付ける"

        alias_example @= r"""
        from metamk import Mk

        PREPARE, MAIN, VERIFY = Mk.PREPARE, Mk.MAIN, Mk.VERIFY


        def test_example():
            with PREPARE:
                data = [1, 2, 3]

            with MAIN:
                total = sum(data)

            with VERIFY:
                assert total == 6
        """

    class SECTION_009:
        r"""
        `{{project.name}}` は、次のことをしません。

        - 例外を握りつぶす、置き換える、変換する。
        - 結果の真偽を評価する。検証の書き方（`assert` など）は自由です。
        - フェーズの順序や個数を強制する。
        - 後片付けの実行を保証する。
        - フックや設定を提供する。
        - pytest のプラグインを提供する（現時点では未提供です。[STATUS](https://github.com/minoru-jp/metamk/blob/main/STATUS.md) を参照してください）。
        """

        title @= "しないこと"

    class SECTION_010:
        r"""
        ```bash
        pip install metamk
        ```

        Python `{{project.requires-python}}` が必要です。標準ライブラリのみを使い、外部依存はありません。型注釈を付けて提供し、PEP 561 の `py.typed` を同梱します。
        """

        title @= "インストールと要件"

    class SECTION_011:
        r"""
        このリポジトリの文書は [shikumi-devdoc](https://github.com/minoru-jp/shikumi-devdoc) で管理しています。正本ソースと、そこから生成した正本（canonical document）は `devdocs/` にあり、日本語で記述しています。トップレベルの公開文書は、その正本を英語に翻訳したものです。

        - [STATUS](https://github.com/minoru-jp/metamk/blob/main/STATUS.md): 現在の開発状況
        - [CHANGELOG](https://github.com/minoru-jp/metamk/blob/main/CHANGELOG.md): 変更履歴
        """

        title @= "文書"

    class SECTION_012:
        r"""
        MIT License。[`LICENSE`](https://github.com/minoru-jp/metamk/blob/main/LICENSE) を参照してください。
        """

        title @= "ライセンス"
