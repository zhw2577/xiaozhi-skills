#!/usr/bin/env python3
"""Build a self-contained DSH student skill bundle; no dependencies or install scripts."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
MANUAL_ONLY = {"xiaozhi-learning-dna", "xiaozhi-im-reminder"}
REVIEWED_DEV_RESOURCE = {
    "student/general/xiaozhi-learning-dna/schemas/validate.js":
        "fad1ff6d385afc5233848865cab1474b49b499fe7e14e0a5dacf4a37c9a369c2"
}
INTRO = """## DSH Web 运行约定（dsh-web-2）

开始教学前读取本技能目录的 `dsh-platform.md`。使用当前会话实际可用的图片理解能力，不绑定模型厂商和型号。
看不清的数字、符号、图形条件先确认；不按画面比例补条件，沿用学生已经给出的题干和步骤。
只调用当前会话实际提供的工具，跨技能时按准确名字加载，不把 depends_on/JSON 交接当执行结果。
本适配包不提供长期档案、历史统计、主动提醒后端：M/X/T 默认按缺失处理；不以通用记忆工具代替档案权限，不声称已入队或推送。
周报仅用本次会话或用户提供的数据。文档仅按用户要求使用实际可用的官方 Office 技能及依赖加载工具。
平台工具能力以上述约定和实际可用工具为准，教学与授权规则继续遵守下文及 shared 中的上游约定。

---

"""


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output):
    output = output.resolve()
    # Never clean or overwrite arbitrary directories, and never mutate source skills.
    if output.exists():
        raise SystemExit("Output must be a new directory: " + str(output))
    if output == ROOT or ROOT in output.parents:
        raise SystemExit("Output must be outside the source checkout")
    source_skills = sorted((ROOT / "student").glob("*/*/SKILL.md"))
    if len(source_skills) != 49:
        raise SystemExit("Expected the reviewed 49 student skills; re-review upstream changes")
    output.mkdir(parents=True)
    packages = output / "skills"
    packages.mkdir()
    entries = []
    for source in source_skills:
        name = source.parent.name
        raw = source.read_text(encoding="utf-8")
        match = re.fullmatch(r"---\n(.*?)\n---\n(.*)", raw, re.S)
        if not match or f"name: {name}\n" not in match[1] + "\n":
            raise ValueError("Unexpected frontmatter: " + str(source))
        front, body = match.groups()
        if re.search(r"^(user-invocable|disable-model-invocation):", front, re.M):
            raise ValueError("Review upstream invocation policy before overriding")
        front = re.sub(r"^compatibility:.*$", "compatibility: DeepSeek Harness Web 0.2.1-rc.5 (dsh-web-2)", front, flags=re.M)
        front += "\nuser-invocable: true\n"
        if name in MANUAL_ONLY:
            front += "disable-model-invocation: true\n"
        target = packages / name
        target.mkdir()
        # Preserve resource trees; the one reviewed JS file is a dev-only schema
        # example validator. It is copied for reference integrity, never executed.
        for child in source.parent.rglob("*"):
            if child.is_symlink():
                raise ValueError("Unexpected symlink: " + str(child))
            if child.is_file() and child.name != "SKILL.md":
                if child.suffix not in {".md", ".json"}:
                    expected = REVIEWED_DEV_RESOURCE.get(child.relative_to(ROOT).as_posix())
                    normalized_hash = hashlib.sha256(child.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                    if expected != normalized_hash:
                        raise ValueError("Review non-data skill resource: " + str(child))
                dest = target / child.relative_to(source.parent)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(child, dest)
        (target / "SKILL.md").write_text("---\n" + front.rstrip() + "\n---\n\n" + INTRO + body.lstrip(), encoding="utf-8", newline="\n")
        shutil.copyfile(ROOT / "dsh/platform.md", target / "dsh-platform.md")
        shutil.copyfile(ROOT / "LICENSE", target / "LICENSE")
        entries.append({"name": name, "source": source.relative_to(ROOT).as_posix(), "manual_only": name in MANUAL_ONLY})
    # Validate references within each independent package, including nested resources.
    pattern = re.compile(r"(?<![\w./:@-])((?:(?:\.{1,2}|[\w-]+)/)+[\w-]+(?:\.[\w-]+)*\.(?:md|json|js|mjs|py|ya?ml))(?![\w/-])", re.ASCII)
    for entry in entries:
        base = packages / entry["name"]
        for file in base.rglob("*"):
            local = file.relative_to(base)
            if not (file.name in {"SKILL.md", "SKILL.lite.md", "dsh-platform.md"}
                    or (local.parts[0] == "references" and file.suffix == ".md")
                    or (local.parts[0] == "shared" and file.suffix in {".md", ".json"})
                    or (local.parts[0] == "schemas" and file.suffix == ".json")):
                continue
            for ref in set(pattern.findall(file.read_text(encoding="utf-8"))):
                if ref.startswith("scripts/"):
                    continue
                candidates = [(base / ref).resolve(), (file.parent / ref).resolve()]
                if not any(p.is_relative_to(base.resolve()) and p.is_file() for p in candidates):
                    raise ValueError(f"Broken or escaping reference: {file}: {ref}")
    commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    dirty = bool(subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all"], text=True).strip())
    manifest = {
        "adaptation": "dsh-web-2", "upstream": "https://github.com/qizhitang/xiaozhi-skills",
        "source_commit": commit,
        "upstream_commit": "c6d628d0602d16585be31abb17bfc4ea0c725b01", "source_dirty": dirty,
        "upstream_version": json.loads((ROOT / "package.json").read_text())["version"],
        "source_note": "Built from fork working tree; source_commit/source_dirty describe build provenance, and file hashes identify the installed resources",
        "capabilities": {"O": "current-model-native-vision", "F": "existing-tools-and-office", "M": False, "X": False, "T": False},
        "skills": entries,
        "files": {p.relative_to(packages).as_posix(): sha256(p) for p in sorted(packages.rglob("*")) if p.is_file()},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    archive = output / "xiaozhi-dsh-student-dsh-web-2.tar.gz"
    def private_metadata_filter(info):
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        info.mtime = 0
        info.mode = 0o700 if info.isdir() else 0o600
        return info
    with archive.open("wb") as raw_archive:
        with gzip.GzipFile(filename="", fileobj=raw_archive, mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as tar:
                tar.add(packages, arcname="skills", filter=private_metadata_filter)
                tar.add(output / "manifest.json", arcname="manifest.json", filter=private_metadata_filter)
    print(json.dumps({"skills": len(entries), "files": len(manifest["files"]), "manual_only": sorted(MANUAL_ONLY), "archive": archive.name, "sha256": sha256(archive)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.output)
