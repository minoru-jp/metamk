"""metamk の Project Status の正本ソース。"""

from shikumi_devdoc.fields.status import GENERAL, condition, kind
from shikumi_devdoc.norms.common import canonical_source
from shikumi_devdoc.norms.document import title


@canonical_source(
    "{{project.name}} Project Status",
    filename="STATUS.md",
    merge_policy="external",
    heading="identity",
)
class PROJECT_STATUS:
    r"""
    `{{project.name}}` の現在状態と、現在から見た将来の告知を記述する。
    過去の状態変化は保持せず、実際に起きた利用者向け変更は CHANGELOG が担当する。
    """

    class STATUS_001:
        r"""
        現在の開発段階は Alpha。現在の公開版は `{{project.version}}` で、設計を1からやり直した版である。
        """

        title @= "Development stage"

    class STATUS_002:
        r"""
        現在の対象 Python バージョン範囲は `{{project.requires-python}}`。例外へ注記を付ける `BaseException.add_note()` が 3.11 で導入されたことによる。
        """

        title @= "Supported Python"

    class STATUS_003:
        r"""
        `{{project.name}}` の設計は README に記述している。README が実装の基準であり、実装は README の記述に従って行う。README と実装が食い違う場合は、実装ではなく README の記述を先に見直す。

        実装は README の記述に従っている。README のコード例と表示例、「動作の約束」の各項目、公開名は、`tests/` のテストで検証している。
        """

        title @= "Design and implementation"

    class STATUS_004:
        r"""
        PyPI に公開済みの `0.0.x` は旧設計であり、`{{project.version}}` とは互換性がない。旧設計の `Mk` / `Mark` と、そのフェーズ・フック・非同期専用層は引き継いでいない。変更の詳細は CHANGELOG を参照する。
        """

        title @= "Relationship to 0.0.x"

    class STATUS_005:
        r"""
        文書は `shikumi-devdoc` で管理する。正本ソースは `devdocs/canonical_sources/`、そこから生成した正本は `devdocs/canonical_documents/` にあり、いずれも日本語で記述する。リポジトリのトップレベルにある README、STATUS、CHANGELOG は、その正本を英語に翻訳した公開文書である。翻訳は `shikumi-devdoc` の機能ではなく、このリポジトリの公開工程が担当する。正本の生成には optional dependency `docs`（`shikumi-devdoc`）を使用する。
        """

        title @= "Documentation system"

    class STATUS_006:
        r"""
        開発では、format と lint に ruff、型検査に basedpyright、テストに pytest を使用する。ruff は `0.16.10`、basedpyright は `1.40.2` に固定し、それぞれ optional dependency `lint`、`typecheck` として宣言する。pytest は `test` として `>=8.0` を宣言する。いずれも実行時の依存ではない。
        """

        title @= "Development tools"

    class STATUS_007:
        r"""
        `ruff format --check .`、`ruff check .`、`basedpyright`、`basedpyright -p tests/typing`、`pytest` がいずれも clean である。`src/metamk` は basedpyright のデフォルト設定（recommended）で、利用側の型の契約（`with` ブロック内で代入した名前が「未束縛の可能性あり」と判定されないこと）は `tests/typing` の standard モードで検査し、どちらも 0 errors / 0 warnings である。

        公開は release workflow が checks の成功を条件とするため、公開した版は Python 3.11 から 3.14 の pytest を含むすべての checks を通過している。
        """

        title @= "Quality checks"

    class STATUS_008:
        r"""
        配布は PyPI で行い、ソースリポジトリは [GitHub](https://github.com/minoru-jp/metamk) で公開する。

        GitHub Actions の品質検証は再利用可能な `checks.yml` に集約している。ruff の format check と lint、basedpyright（`src/metamk` と `tests/typing`）、Python 3.11 から 3.14 の pytest を実行する。CI ではツールが存在しないことを理由にテストをスキップせず、失敗として扱う。

        通常の CI（`ci.yml`）は `main` への push と pull request でこの共通 checks を呼び出し、あわせて wheel と sdist を build して `scripts/check_dist.py` で検証する。検証の内容は、wheel の中身が期待どおりであること、実行時依存が無いこと、`twine check --strict`、別の仮想環境へインストールしての動作確認である。

        GitHub Release を publish すると、release workflow（`release.yml`）が同じ共通 checks を最初に実行する。すべて成功した場合だけ、tag が `v<project version>` と一致すること、CHANGELOG に当該版の項目があることを確認して wheel と sdist を build・検証し、その検証済みの artifact だけを PyPI の Trusted Publishing で公開する。PyPI の API token は保管しない。

        GitHub Actions の参照はコミット SHA に固定し、Dependabot で更新する。

        PyPI 側の Trusted Publisher の登録と GitHub の `pypi` environment の作成は、リポジトリの外の設定である。`{{project.version}}` はこの release workflow で公開した。
        """

        title @= "Distribution and CI status"

    class NOTICE_001:
        r"""
        例外へ記録したフェーズ名を pytest のレポート（error と failure の区別など）へ反映する仕組みは、現時点では提供しない。フェーズ名は `phase_of()` で機械的に取り出せるが、pytest との連携方法は未定である。
        """

        title @= "pytest integration is undecided"
        kind @= GENERAL
        condition @= "連携の方針が決まるまで。"

    class NOTICE_002:
        r"""
        `{{project.version}}` から 1.0 までの間は、公開 API を予告なく変更することがある。
        """

        title @= "API stability before 1.0"
        kind @= GENERAL
        condition @= "最初のメジャーバージョンを公開するまで。"
