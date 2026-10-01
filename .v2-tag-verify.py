"""Verify backported CardKit v2 parsing on /opt/data/hermes-fork adapter.py (main base)."""
import re, json, sys
sys.path.insert(0, '/opt/hermes')

src = open('/opt/data/hermes-fork/plugins/platforms/feishu/adapter.py').read()

consts_lines = []
for p in [
    r'_MARKDOWN_SPECIAL_CHARS_RE\s*=\s*re\.compile\([^)]+(?:\)[^=]*)\)',
    r'_MENTION_PLACEHOLDER_RE = re\.compile\([^)]+\)',
    r'_WHITESPACE_RE = re\.compile\([^)]+\)',
    r'_MULTISPACE_RE = re\.compile\([^)]+\)',
    r'FALLBACK_INTERACTIVE_TEXT = .+',
    r'_RICH_BLOCK_TAGS = \{[^}]+\}',
    r'_SUPPORTED_CARD_TEXT_KEYS = \([^)]+\)',
    r'_SKIP_TEXT_KEYS = \{[^}]+\}',
]:
    m = re.search(p, src)
    if m:
        consts_lines.append(m.group(0).rstrip())
consts = "\n".join(consts_lines)

fn_names = [
    '_normalize_feishu_text', '_first_non_empty_text', '_first_text_field',
    '_find_first_text', '_unique_lines', '_is_style_enabled',
    '_walk_nodes', '_collect_text_segments', '_collect_card_lines',
    '_collect_action_labels', '_find_header_title', '_normalize_interactive_message',
]
fns = "\n\n".join(
    re.search(rf'def {n}.*?(?=\n(?:@|def |class ))', src, re.S).group(0)
    for n in fn_names
)

prelude = ("import re, json\n"
           "from collections import OrderedDict\n"
           "from dataclasses import dataclass, field\n"
           "from typing import Any, Dict, List, Optional\n\n"
           "@dataclass(frozen=True)\n"
           "class FeishuMentionRef:\n"
           "    key: str\n"
           "    user_id: str = ''\n"
           "    name: str = ''\n"
           "    is_all: bool = False\n\n"
           "@dataclass(frozen=True)\n"
           "class FeishuNormalizedMessage:\n"
           "    raw_type: str = ''\n"
           "    text_content: str = ''\n"
           "    preferred_message_type: str = 'text'\n"
           "    image_keys: List[str] = field(default_factory=list)\n"
           "    media_refs: List = field(default_factory=list)\n"
           "    mentions: List[FeishuMentionRef] = field(default_factory=list)\n"
           "    relation_kind: str = 'plain'\n"
           "    metadata: Dict[str, Any] = field(default_factory=dict)\n\n")

ns = {}
exec(prelude + consts + "\n\n" + fns, ns)
norm = ns["_normalize_interactive_message"]

CASES = [
    ("旧版卡片 markdown/div（回归）", {
        "card": {
            "header": {"title": {"tag": "plain_text", "content": "Footer 实现"}},
            "elements": [
                {"tag": "markdown", "content": "旧版 markdown 元素必须仍然工作。"},
                {"tag": "div", "text": {"tag": "lark_md", "content": "div 里的 lark_md"}},
            ],
        },
    }),
    ("v2 tag_type=markdown", {
        "body": {"elements": [{"tag_type": "markdown", "content": "v2 markdown 正文"}]},
    }),
    ("v2 element_type=text_run 嵌套", {
        "body": {"elements": [
            {"element_type": "text_run", "text_run": {"content": "嵌套 text_run 内容"}},
        ]},
    }),
    ("v2 div+text_run 组合", {
        "body": {"elements": [
            {"tag_type": "div", "text": {"tag": "lark_md", "content": "div 内容"}},
            {"element_type": "text_run", "text_run": {"content": "第二段"}},
        ]},
    }),
    ("v2 按钮 label（含 type='primary' 样式）", {
        "body": {"elements": [
            {"tag_type": "action", "actions": [
                {"tag_type": "button", "text": {"content": "确认"}, "type": "primary"},
            ]},
        ]},
    }),
    ("60 行截断边界（应保留 50 行）", {
        "body": {"elements": [
            {"tag_type": "markdown", "content": "\n".join("第%d行" % i for i in range(1, 61))},
        ]},
    }),
    ("双重编码 card 字符串", {
        "card": json.dumps({"body": {"elements": [
            {"tag_type": "markdown", "content": "双重编码场景正文"},
        ]}}),
    }),
]

ok = 0
for name, payload in CASES:
    r = norm("interactive", payload)
    text = r.text_content if hasattr(r, "text_content") else r["text"]
    print("--- %s ---" % name)
    print("  text=%r" % text[:80])
    print()
    ok += 1
print("ran %d cases" % ok)
