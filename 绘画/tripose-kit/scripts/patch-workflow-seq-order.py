# -*- coding: utf-8 -*-
"""Wire TriPoseSeqGate: Save1→lane2, Save2→lane3 so outputs run 正常→赤裸→事后."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / "workflows" / "CF-TriPose-SDXL-template.json"

N_SW1, N_SW2, N_SW3 = 121, 122, 123
N_SAMP1, N_SAMP2, N_SAMP3 = 14, 15, 16
N_REF1, N_REF2, N_REF3 = 113, 115, 117
N_SAVE1, N_SAVE2 = 24, 25
N_GATE2, N_GATE3 = 136, 137


def main() -> None:
    wf = json.loads(WF.read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in wf["nodes"]}
    links = wf["links"]

    # Drop SW2/SW3 MODEL → sampler/refine links (will go through gates)
    drop_pairs = {
        (N_SW2, N_SAMP2),
        (N_SW2, N_REF2),
        (N_SW3, N_SAMP3),
        (N_SW3, N_REF3),
    }
    new_links = []
    for L in links:
        if (L[1], L[3]) in drop_pairs and L[5] == "MODEL":
            # unlink from source outputs
            src = nodes[L[1]]
            for o in src.get("outputs") or []:
                if o.get("links") and L[0] in o["links"]:
                    o["links"] = [x for x in o["links"] if x != L[0]]
            continue
        new_links.append(L)
    links = new_links

    # Ensure SW nodes expose enabled BOOLEAN output in graph JSON
    for nid in (N_SW1, N_SW2, N_SW3):
        outs = nodes[nid].setdefault("outputs", [])
        if len(outs) < 2:
            outs.append(
                {
                    "name": "enabled",
                    "type": "BOOLEAN",
                    "links": [],
                    "slot_index": 1,
                }
            )
        else:
            outs[1]["name"] = "enabled"
            outs[1]["type"] = "BOOLEAN"
            outs[1]["links"] = list(outs[1].get("links") or [])
            outs[1]["slot_index"] = 1

    def add_node(node: dict) -> None:
        wf["nodes"].append(node)
        nodes[node["id"]] = node

    def alloc_link() -> int:
        wf["last_link_id"] = int(wf.get("last_link_id") or 0) + 1
        return wf["last_link_id"]

    def connect(src: int, src_slot: int, dst: int, dst_slot: int, typ: str) -> int:
        lid = alloc_link()
        links.append([lid, src, src_slot, dst, dst_slot, typ])
        # source output links
        outs = nodes[src].setdefault("outputs", [])
        while len(outs) <= src_slot:
            outs.append({"name": typ, "type": typ, "links": [], "slot_index": len(outs)})
        o = outs[src_slot]
        o.setdefault("links", [])
        if lid not in o["links"]:
            o["links"].append(lid)
        o["slot_index"] = src_slot
        # dest input link
        ins = nodes[dst].setdefault("inputs", [])
        while len(ins) <= dst_slot:
            ins.append({"name": typ, "type": typ, "link": None})
        ins[dst_slot]["link"] = lid
        return lid

    # Gate nodes (compact, near switches — do not move existing layout)
    for nid, title, pos in (
        (N_GATE2, "串行·等正常后再赤裸", [1408.0, 160.0]),
        (N_GATE3, "串行·等赤裸后再事后", [1664.0, 160.0]),
    ):
        if nid in nodes:
            continue
        add_node(
            {
                "id": nid,
                "type": "TriPoseSeqGate",
                "pos": pos,
                "size": [240.0, 80.0],
                "flags": {},
                "order": 3,
                "mode": 0,
                "inputs": [
                    {"name": "model", "type": "MODEL", "link": None},
                    {"name": "prior_lane_on", "type": "BOOLEAN", "link": None},
                    {
                        "name": "prior_image",
                        "type": "IMAGE",
                        "link": None,
                        "shape": 7,
                    },
                ],
                "outputs": [
                    {"name": "model", "type": "MODEL", "links": [], "slot_index": 0}
                ],
                "properties": {"Node name for S&R": "TriPoseSeqGate"},
                "widgets_values": [True],
                "title": title,
            }
        )

    # SW2 → Gate2 ← SW1.enabled, Save1
    connect(N_SW2, 0, N_GATE2, 0, "MODEL")
    connect(N_SW1, 1, N_GATE2, 1, "BOOLEAN")
    connect(N_SAVE1, 0, N_GATE2, 2, "IMAGE")
    connect(N_GATE2, 0, N_SAMP2, 0, "MODEL")
    connect(N_GATE2, 0, N_REF2, 0, "MODEL")

    # SW3 → Gate3 ← SW2.enabled, Save2
    connect(N_SW3, 0, N_GATE3, 0, "MODEL")
    connect(N_SW2, 1, N_GATE3, 1, "BOOLEAN")
    connect(N_SAVE2, 0, N_GATE3, 2, "IMAGE")
    connect(N_GATE3, 0, N_SAMP3, 0, "MODEL")
    connect(N_GATE3, 0, N_REF3, 0, "MODEL")

    wf["links"] = links
    wf["last_node_id"] = max(n["id"] for n in wf["nodes"])
    note = nodes.get(99) or next(
        (n for n in wf["nodes"] if n.get("type") == "Note"), None
    )
    if note and isinstance(note.get("widgets_values"), list) and note["widgets_values"]:
        text = str(note["widgets_values"][0])
        if "出图顺序" not in text:
            note["widgets_values"][0] = (
                text.rstrip()
                + "\n• 出图顺序串行：正常 → 赤裸 → 事后（上路关则不阻塞）"
            )

    WF.write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"patched {WF}")
    print(f"nodes={wf['last_node_id']} links={wf['last_link_id']}")


if __name__ == "__main__":
    main()
