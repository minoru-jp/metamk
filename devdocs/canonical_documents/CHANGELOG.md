<!--
この文書は `shikumi-devdoc` によって生成された canonical document です。
Canonical source は `devdocs/canonical_sources/changelog.py` です。
直接編集しないでください。

公開文書作成方針

- `devdocs/canonical_documents/` にある日本語 canonical document を英語へ翻訳し、リポジトリのトップレベルに公開文書（README.md、STATUS.md、CHANGELOG.md）として配備する。
- 翻訳では意味、構造、情報量を維持し、内容を勝手に追加・削除・要約しない。
- canonical document に `shikumi-devdoc:translation-metadata` が含まれる場合は、その `preserve_spelling` 指定の用語の表記を変更しない。
- コード、Python 識別子、コマンド、ファイルパス、URL は、翻訳上の必要がない限り変更しない。
- このコメントブロックと `shikumi-devdoc:translation-metadata` は published document には含めない。
- published document は canonical document から派生する公開成果物として扱い、内容の変更が必要な場合は canonical source または realization context へ戻して canonical document を再生成する。
-->

# metamk 変更履歴

`metamk` の版ごとの変更履歴を記録する。`0.1.0` より前（`0.0.x`）は旧設計であり、この変更履歴には引き継がない。

## V0_1_0

設計を1からやり直した版。旧設計の `0.0.x` とは互換性が一切ない。

version: 0.1.0

released on: 2026-10-05

Added:

- `Mk.PREPARE`、`Mk.MAIN`、`Mk.VERIFY` を追加した。テストのコードを準備・対象・検証に区切る `with` ブロックで、例外が通過すると、通過したフェーズ名を例外へ記録し、注記 `[metamk] failed in <phase>` を追加する。例外は握りつぶさず、置き換えず、そのまま再送出する。
- `phase_of(exc)` を追加した。例外に記録されたフェーズ名を取り出す。例外自身、`__cause__`、`__context__` の順に連鎖をたどる。
- 非同期コードの対応を追加した。`with` ブロックの中で `await` できるため、非同期専用の API は設けない。
- GitHub Actions のワークフローを追加した。再利用可能な `checks.yml`（ruff、basedpyright、Python 3.11 から 3.14 の pytest）、push と pull request で動く `ci.yml`、GitHub Release の publish で動く `release.yml` である。`release.yml` は checks と tag・版の照合、配布物の検証を通ったものだけを PyPI の Trusted Publishing で公開する。
- `shikumi-devdoc` による文書体系を導入した。正本ソースと正本は `devdocs/` に日本語で記述し、トップレベルの README、STATUS、CHANGELOG はその英訳として公開する。

Changed:

- 設計を1からやり直した。目的を「テストの構造を明示し、失敗したフェーズを例外に残すこと」に絞り、実行時の機構を最小にした。
- 対象の Python を 3.11 以上に引き上げた。例外への注記に `BaseException.add_note()` を使用する。

Removed:

- 状態機械によるフェーズ順序の検証を行う `Mark`、`Phase`、`PhaseError`、およびフック（`on_result`、`on_positive`、`on_negative`、`on_error_in_phase_block`、`on_phase_transition_error`）を削除した。
- フェーズ `invariant`、`setup`、`before`、`cleanup`、`after`、`final`、`invoke` と、対応する `as_*_block` を削除した。フェーズは PREPARE、MAIN、VERIFY の3つに絞った。
- 関数や awaitable を受け取って真偽を評価する呼び出し形式（`before`、`after`、`invariant`）と、値を受け取る `MAIN(value)` を削除した。対象のコードは、値ではなく `with Mk.MAIN:` のブロックとして書く。
- 非同期専用の名前空間 `Mk.a` を削除した。
