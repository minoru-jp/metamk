"""metamk の CHANGELOG の正本ソース。"""

from shikumi_devdoc.fields.changelog import (
    added,
    changed,
    released_on,
    removed,
    version,
)
from shikumi_devdoc.norms.common import canonical_source


@canonical_source(
    "metamk 変更履歴",
    filename="CHANGELOG.md",
    merge_policy="forbidden",
    heading="identity",
)
class CHANGELOG:
    """`metamk` の版ごとの変更履歴を記録する。`0.1.0` より前（`0.0.x`）は旧設計であり、この変更履歴には引き継がない。"""

    class V0_1_0:
        """設計を1からやり直した版。旧設計の `0.0.x` とは互換性が一切ない。"""

        version @= "0.1.0"
        released_on @= "2026-10-05"

        added @= "`Mk.PREPARE`、`Mk.MAIN`、`Mk.VERIFY` を追加した。テストのコードを準備・対象・検証に区切る `with` ブロックで、例外が通過すると、通過したフェーズ名を例外へ記録し、注記 `[metamk] failed in <phase>` を追加する。例外は握りつぶさず、置き換えず、そのまま再送出する。"
        added @= "`phase_of(exc)` を追加した。例外に記録されたフェーズ名を取り出す。例外自身、`__cause__`、`__context__` の順に連鎖をたどる。"
        added @= "非同期コードの対応を追加した。`with` ブロックの中で `await` できるため、非同期専用の API は設けない。"
        added @= "GitHub Actions のワークフローを追加した。再利用可能な `checks.yml`（ruff、basedpyright、Python 3.11 から 3.14 の pytest）、push と pull request で動く `ci.yml`、GitHub Release の publish で動く `release.yml` である。`release.yml` は checks と tag・版の照合、配布物の検証を通ったものだけを PyPI の Trusted Publishing で公開する。"
        added @= "`shikumi-devdoc` による文書体系を導入した。正本ソースと正本は `devdocs/` に日本語で記述し、トップレベルの README、STATUS、CHANGELOG はその英訳として公開する。"

        changed @= "設計を1からやり直した。目的を「テストの構造を明示し、失敗したフェーズを例外に残すこと」に絞り、実行時の機構を最小にした。"
        changed @= "対象の Python を 3.11 以上に引き上げた。例外への注記に `BaseException.add_note()` を使用する。"

        removed @= "状態機械によるフェーズ順序の検証を行う `Mark`、`Phase`、`PhaseError`、およびフック（`on_result`、`on_positive`、`on_negative`、`on_error_in_phase_block`、`on_phase_transition_error`）を削除した。"
        removed @= "フェーズ `invariant`、`setup`、`before`、`cleanup`、`after`、`final`、`invoke` と、対応する `as_*_block` を削除した。フェーズは PREPARE、MAIN、VERIFY の3つに絞った。"
        removed @= "関数や awaitable を受け取って真偽を評価する呼び出し形式（`before`、`after`、`invariant`）と、値を受け取る `MAIN(value)` を削除した。対象のコードは、値ではなく `with Mk.MAIN:` のブロックとして書く。"
        removed @= "非同期専用の名前空間 `Mk.a` を削除した。"
