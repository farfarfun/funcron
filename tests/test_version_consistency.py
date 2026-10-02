"""版本号一致性测试：拦截 pyproject.toml 与 script/__version__.md 的漂移。

funbuild 的 `sync_all_manifest_versions()` 只同步 pyproject.toml / package.json /
pubspec.yaml，不碰 `script/__version__.md`，两处很容易漂开（本仓库就漂过
0.5.8 / 0.5.7）。这里不硬编码版本字面量，只断言两处一致。
"""


def test_pyproject_version_matches_version_md(repo_root, project_version):
    version_md = (repo_root / "script" / "__version__.md").read_text(encoding="utf-8").strip()
    assert project_version == version_md, (
        f"pyproject.toml 的 version={project_version} 与 script/__version__.md 的 {version_md} 不一致"
    )


def test_changelog_documents_current_version(repo_root, project_version):
    changelog = (repo_root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"[{project_version}]" in changelog, f"CHANGELOG.md 里没有 {project_version} 的条目"
