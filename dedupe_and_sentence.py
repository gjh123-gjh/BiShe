#!/usr/bin/env python3
from Neo4j_red import driver
import argparse
import re


def normalize_name(name: str) -> str:
    if name is None:
        return ""
    s = str(name).strip()
    # 全角转半角、小写、去标点、合并空格
    s = s.replace('（', '(').replace('）', ')')
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[\u3000\uff01-\uffef]", "", s)
    s = re.sub(r"[^0-9\w\u4e00-\u9fff ]", "", s)
    s = s.lower().strip()
    return s


def collect_nodes():
    q = "MATCH (n:`红色旅游`) RETURN id(n) AS id, n.实体名称 AS name, labels(n) AS labels"
    with driver.session() as session:
        res = session.run(q)
        rows = [r.data() for r in res]
    return rows


def find_duplicates(nodes):
    groups = {}
    for r in nodes:
        key = normalize_name(r.get('name') or '')
        groups.setdefault(key, []).append(r)
    # only groups with >1 are duplicates
    return {k: v for k, v in groups.items() if len(v) > 1 and k}


def dry_run_report(dups):
    print(f"发现 {len(dups)} 个潜在重复实体组（按名称归一化）。")
    for k, items in list(dups.items())[:20]:
        names = [it['name'] for it in items]
        ids = [it['id'] for it in items]
        print(f"组键: {k} -> ids={ids} names={names}")


def merge_group(canonical_name, group_ids):
    # group_ids: list of node ids to merge into canonical (skip canonical if exists)
    with driver.session() as session:
        # ensure canonical node exists (MERGE by name)
        session.run("MERGE (c:`红色旅游` {实体名称: $name})", name=canonical_name)

        for nid in group_ids:
            # skip if this id already has canonical name
            check = session.run("MATCH (n) WHERE id(n)=$id RETURN n.实体名称 AS name", id=nid).single()
            if not check:
                continue
            if check['name'] == canonical_name:
                continue

            # outgoing relationships from old node
            out_q = "MATCH (o) WHERE id(o)=$id OPTIONAL MATCH (o)-[r]->(t) RETURN type(r) AS ttype, properties(r) AS props, id(t) AS tid, t.实体名称 AS tname"
            out_res = session.run(out_q, id=nid)
            for row in out_res:
                if row['ttype'] is None:
                    continue
                rel_type = row['ttype']
                props = row['props'] or {}
                tid = row['tid']
                # create relationship from canonical to target
                cy = f"MATCH (c:`红色旅游` {{实体名称:$canon}}), (t) WHERE id(t)=$tid CREATE (c)-[r:`{rel_type}` $props]->(t)"
                session.run(cy, canon=canonical_name, tid=tid, props=props)

            # incoming relationships to old node
            in_q = "MATCH (s)-[r]->(o) WHERE id(o)=$id RETURN type(r) AS ttype, properties(r) AS props, id(s) AS sid, s.实体名称 AS sname"
            in_res = session.run(in_q, id=nid)
            for row in in_res:
                rel_type = row['ttype']
                props = row['props'] or {}
                sid = row['sid']
                cy = f"MATCH (s), (c:`红色旅游` {{实体名称:$canon}}) WHERE id(s)=$sid CREATE (s)-[r:`{rel_type}` $props]->(c)"
                session.run(cy, canon=canonical_name, sid=sid, props=props)

            # finally delete old node and its relationships
            session.run("MATCH (n) WHERE id(n)=$id DETACH DELETE n", id=nid)


def perform_merge(dups):
    # For each group, pick canonical name (most common original or shortest)
    for key, items in dups.items():
        names = [it['name'] for it in items if it.get('name')]
        # choose canonical: the longest non-empty name (prefer full form)
        canonical = sorted(names, key=lambda x: (-len(str(x)), str(x)))[0]
        ids = [it['id'] for it in items]
        print(f"合并组 key={key} -> canonical={canonical} ids={ids}")
        merge_group(canonical, ids)


def print_sentences(limit=50):
    with driver.session() as session:
        q1 = "MATCH (a:`红色旅游`)-[r]->(b:`红色旅游`) RETURN a.实体名称 AS a, coalesce(r.原关系, type(r)) AS rel, b.实体名称 AS b LIMIT $limit"
        for rec in session.run(q1, limit=limit):
            a, rel, b = rec['a'], rec['rel'], rec['b']
            print(f"{a}{rel}{b}")

        print('\n实体属性句子:')
        q2 = "MATCH (a:`红色旅游`)-[r:HAS_PROPERTY]->(p:Property) RETURN a.实体名称 AS a, r.属性 AS attr, p.值 AS val LIMIT $limit"
        for rec in session.run(q2, limit=limit):
            a, attr, val = rec['a'], rec['attr'], rec['val']
            print(f"{a}的{attr}是{val}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', default=True, help='只报告，不执行合并')
    parser.add_argument('--apply', action='store_true', help='实际执行合并（危险：会修改数据库）')
    parser.add_argument('--sentences', action='store_true', help='打印示例自然语言句子')
    parser.add_argument('--limit', type=int, default=50)
    args = parser.parse_args()

    nodes = collect_nodes()
    dups = find_duplicates(nodes)
    if dups:
        dry_run_report(dups)
        if args.apply:
            perform_merge(dups)
            print('合并完成。')
        else:
            print('当前为干运行。如需执行合并，请加参数 --apply（先备份数据库）。')
    else:
        print('未发现按名称归一化的重复实体。')

    if args.sentences:
        print_sentences(limit=args.limit)


if __name__ == '__main__':
    main()
