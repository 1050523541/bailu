# -*- coding: utf-8 -*-
"""Build a REAL large NSFW/spoken zh→en lexicon (sqlite), not a tiny JSON toy.

Sources:
1) danbooru_zh.sqlite — broad EN/CN adult heuristics (all cn aliases)
2) maps/_download/booru_all.csv — community Danbooru zh pack (~55k Chinese)
3) Yellow-Rush danbooru/yande CSV — classic spoken zh translations
4) hard-coded TriPose spoken NSFW synonyms

Output: maps/danbooru_zh_nsfw.sqlite  (table tags: cn_name PK, name, post_count)
Also writes a tiny README sidecar; removes misleading small JSON if present.
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPS = ROOT / "maps"
DL = MAPS / "_download"
MAIN = MAPS / "danbooru_zh.sqlite"
OUT = MAPS / "danbooru_zh_nsfw.sqlite"
OUT_JSON_LEGACY = MAPS / "danbooru_zh_nsfw.json"

CN_RE = re.compile(
    r"[裸性精乳阴交射穴臀胸淫色欲肛精液潮吹内射口交自慰勃起情趣内衣内裤胸罩"
    r"露点私处下体鸡巴肉棒爱液高潮事后群交捆绑调教扶她百合耽美颜射口爆"
    r"骑乘后入开腿湿润体液无修正马赛克阿黑颜触手假阳具跳蛋中出]"
)
EN_RE = re.compile(
    r"(nude|naked|sex|pussy|penis|cock|dick|cum|semen|breast|nipple|areola|ass|butt|anal|"
    r"oral|fellatio|cunnilingus|paizuri|vaginal|clitoris|masturbat|orgasm|ejaculat|erection|"
    r"after[_ ]?sex|spread[_ ]?(legs|pussy)|insertion|penetration|bondage|bdsm|tentacle|"
    r"ahegao|nsfw|uncensored|censored|mosaic|bar[_ ]?censor|convenient[_ ]?censor|"
    r"barefoot|topless|bottomless|no[_ ]?panties|no[_ ]?bra|lingerie|panties|bra|"
    r"condom|dildo|vibrator|sex[_ ]?toy|femdom|yuri|yaoi|futanari|pregnant|"
    r"lactation|squirting|creampie|bukkake|gangbang|threesome|group[_ ]?sex|"
    r"handjob|footjob|thighjob|grinding|kissing|tongue|saliva|sweat|"
    r"aroused|lust|erotic|hentai|porn|xxx|explicit|lewd|skimpy|micro[_ ]?bikini|"
    r"covered[_ ]?nipples|see-through|transparent|wet[_ ]?(clothes|shirt|skin)|"
    r"undress|clothes[_ ]?pull|lifted[_ ]?by[_ ]?self|flashing|exhibition|"
    r"rape|forced|nonconsensual|slave|collar|leash|groping|molest|fondle|"
    r"cameltoe|bulge|tenting|cowgirl|missionary|doggy|facesitting|shibari|"
    r"whipping|gag|blindfold|handcuff|defloration|virgin|paizuri|deepthroat)",
    re.I,
)

LATIN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 \-_'()/:+.]*$")
SPLIT = re.compile(r"[,，、|/]+")

SPOKEN = {
    "nsfw": "nsfw",
    "色情": "nsfw",
    "成人": "nsfw",
    "赤裸": "nude",
    "裸体": "nude",
    "全裸": "completely nude",
    "半裸": "partially nude",
    "裸足": "barefoot",
    "赤脚": "barefoot",
    "光脚": "barefoot",
    "裸胸": "bare breasts",
    "露胸": "breasts",
    "露奶": "breasts",
    "露点": "nipples",
    "乳头": "nipples",
    "乳晕": "areolae",
    "阴部": "pussy",
    "小穴": "pussy",
    "私处": "pussy",
    "下体": "pussy",
    "阴茎": "penis",
    "鸡巴": "penis",
    "肉棒": "penis",
    "精液": "cum",
    "射精": "ejaculation",
    "内射": "cum in pussy",
    "颜射": "cum on face",
    "口爆": "cum in mouth",
    "口交": "oral",
    "乳交": "paizuri",
    "肛交": "anal",
    "性交": "sex",
    "做爱": "sex",
    "插入": "penetration",
    "后入": "sex from behind",
    "骑乘": "cowgirl position",
    "正常位": "missionary",
    "自慰": "masturbation",
    "爱液": "pussy juice",
    "潮吹": "female ejaculation",
    "高潮": "orgasm",
    "勃起": "erection",
    "事后": "after sex",
    "潮红": "flushed",
    "汗湿": "sweaty",
    "湿润皮肤": "wet skin",
    "体液": "bodily fluids",
    "胸上体液": "cum on breasts",
    "大腿体液": "cum on thighs",
    "滴落": "dripping",
    "无比基尼": "no bikini",
    "无内衣": "no underwear",
    "无内裤": "no panties",
    "无泳装": "no swimsuit",
    "只戴颈环": "choker only",
    "开腿": "spread legs",
    "张开双腿": "spread legs",
    "巨乳": "large breasts",
    "贫乳": "small breasts",
    "细致身体": "detailed body",
    "优雅情色": "elegant erotic",
    "情色": "erotic",
    "无修正": "uncensored",
    "马赛克": "mosaic censoring",
    "黑条和谐": "bar censor",
    "衣冠不整": "disheveled clothes",
    "疲惫满足": "tired, satisfied",
    "腿软": "weak legs",
    "扶着身体": "supporting own body",
    "阿黑颜": "ahegao",
    "捆绑": "bondage",
    "触手": "tentacles",
    "群交": "group sex",
    "三人行": "threesome",
    "百合": "yuri",
    "耽美": "yaoi",
    "扶她": "futanari",
    "手交": "handjob",
    "足交": "footjob",
    "中出": "creampie",
    "女上位": "cowgirl position",
    "狗爬式": "doggy style",
}


def _has_cjk(s: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in s)


def _en_tag(name: str) -> str:
    return str(name).replace("_", " ").strip()


def _put(best: dict[str, tuple[int, str]], key: str, en: str, pc: int) -> None:
    key = (key or "").strip()
    en = (en or "").strip()
    if not key or not en:
        return
    if LATIN.match(key) and not _has_cjk(key):
        return
    prev = best.get(key)
    if prev is None or pc > prev[0]:
        best[key] = (pc, en)


def _add_cn_blob(best: dict[str, tuple[int, str]], cn_blob: str, en: str, pc: int) -> None:
    parts = [cn_blob.strip()]
    for p in SPLIT.split(cn_blob):
        p = p.strip()
        if p and p not in parts:
            parts.append(p)
    for p in parts:
        _put(best, p, en, pc)
        nk = re.sub(r"\s+", "", p)
        if nk != p:
            _put(best, nk, en, pc)


def from_main_sqlite(best: dict[str, tuple[int, str]]) -> int:
    if not MAIN.is_file():
        return 0
    before = len(best)
    con = sqlite3.connect(str(MAIN))
    try:
        for name, cn_name, pc in con.execute(
            "SELECT name, cn_name, post_count FROM tags "
            "WHERE cn_name IS NOT NULL AND cn_name != ''"
        ):
            if not name:
                continue
            he = bool(EN_RE.search(name))
            hc = bool(CN_RE.search(cn_name or ""))
            if not (he or hc):
                continue
            _add_cn_blob(best, cn_name, _en_tag(name), int(pc or 0))
    finally:
        con.close()
    return len(best) - before


def from_booru_all_csv(best: dict[str, tuple[int, str]]) -> int:
    path = DL / "booru_all.csv"
    if not path.is_file():
        return 0
    before = len(best)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            if len(row) < 5:
                continue
            try:
                cat = int(row[1])
                pc = int(row[2])
            except ValueError:
                continue
            # Skip Kontext instruction junk (cat 6) and pure artist (1) noise for NSFW pack.
            if cat not in (0, 3, 4, 5):
                continue
            name = (row[0] or "").strip()
            cn = (row[4] or "").strip()
            alias = (row[3] or "").strip()
            if not name or not cn or not _has_cjk(cn):
                continue
            # Keep all general/meta with Chinese; for character/copyright keep if NSFW-ish
            if cat in (3, 4) and not (EN_RE.search(name) or CN_RE.search(cn)):
                continue
            en = _en_tag(name)
            _add_cn_blob(best, cn, en, pc)
            if alias:
                # English aliases rarely needed; Chinese sometimes pipe-separated in col4 already
                pass
    return len(best) - before


def from_yellow_rush(best: dict[str, tuple[int, str]]) -> int:
    before = len(best)
    for fname in ("yellow_rush_danbooru.csv", "yellow_rush_yande.csv"):
        path = DL / fname
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.reader(f):
                if len(row) < 2:
                    continue
                en_name = (row[0] or "").strip()
                cn = (row[1] or "").strip()
                if not en_name or not cn or not _has_cjk(cn):
                    continue
                _add_cn_blob(best, cn, _en_tag(en_name), 0)
    return len(best) - before


def main() -> None:
    best: dict[str, tuple[int, str]] = {}
    n1 = from_main_sqlite(best)
    n2 = from_booru_all_csv(best)
    n3 = from_yellow_rush(best)
    for k, v in SPOKEN.items():
        _put(best, k, v, 10_000_000)

    if OUT.exists():
        OUT.unlink()
    con = sqlite3.connect(str(OUT))
    try:
        con.execute(
            "CREATE TABLE tags ("
            "cn_name TEXT PRIMARY KEY, "
            "name TEXT NOT NULL, "
            "post_count INTEGER DEFAULT 0)"
        )
        con.executemany(
            "INSERT OR REPLACE INTO tags(cn_name, name, post_count) VALUES (?,?,?)",
            [(k, v[1], int(v[0])) for k, v in best.items()],
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)")
        con.commit()
    finally:
        con.close()

    # Replace tiny JSON with a pointer so nobody thinks 160KB is the pack.
    OUT_JSON_LEGACY.write_text(
        json.dumps(
            {
                "_comment": "DEPRECATED pointer. Real NSFW lexicon is danbooru_zh_nsfw.sqlite",
                "_sqlite": "danbooru_zh_nsfw.sqlite",
                "_entries": len(best),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    mb = OUT.stat().st_size / (1024 * 1024)
    print(
        f"wrote {OUT} size={mb:.2f}MB entries={len(best)} "
        f"(main+{n1}, booru_all+{n2}, yellow+{n3}, spoken={len(SPOKEN)})"
    )


if __name__ == "__main__":
    main()
