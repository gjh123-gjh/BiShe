#!/usr/bin/env python3
from Neo4j_red import driver
import argparse
import sys


def get_duplicate_groups(limit=1000):
    q = (
        "MATCH (n:`红色旅游`) "
        "WITH toLower(replace(n.实体名称, ' ', '')) AS key, collect(id(n)) AS ids, collect(n.实体名称) AS names, size(collect(n)) AS cnt "
        "WHERE key <> '' AND cnt > 1 "
        "RETURN key, ids, names, cnt LIMIT $limit"
    )
    with driver.session() as session:
        rows = list(session.run(q, limit=limit))
    groups = []
    for r in rows:
        groups.append({
            'key': r['key'],
            'ids': r['ids'],
            'names': r['names'],
            'cnt': r['cnt']
        })
    return groups


def try_apoc_merge(session, ids):
    # ids: list of ints; apoc.refactor.mergeNodes expects list of nodes
    cy = (
        "MATCH (n) WHERE id(n) IN $ids WITH collect(n) AS nodes "
        "CALL apoc.refactor.mergeNodes(nodes, {properties:'combine', mergeRels:true}) YIELD node RETURN id(node) AS nid"
    )
    try:
        res = session.run(cy, ids=ids)
        row = res.single()
        return True, row['nid'] if row else None
    except Exception as e:
        return False, str(e)


def fallback_merge(session, ids, canonical_id=None):
    # choose canonical id if not given: pick id whose name is longest
    if canonical_id is None:
        # fetch names to choose
        q = "MATCH (n) WHERE id(n) IN $ids RETURN id(n) AS id, n.实体名称 AS name"
        rows = list(session.run(q, ids=ids))
        if not rows:
            return None
        rows_sorted = sorted(rows, key=lambda r: (-len(str(r['name'] or '')), r['id']))
        canonical_id = rows_sorted[0]['id']

    for nid in ids:
        if nid == canonical_id:
            continue

        # outgoing
        out_q = "MATCH (o) WHERE id(o)=$id OPTIONAL MATCH (o)-[r]->(t) RETURN type(r) AS ttype, properties(r) AS props, id(t) AS tid"
        for row in session.run(out_q, id=nid):
            if row['ttype'] is None:
                continue
            rel_type = row['ttype']
            props = row['props'] or {}
            tid = row['tid']
            cy = f"MATCH (c),(t) WHERE id(c)=$cid AND id(t)=$tid MERGE (c)-[rr:`{rel_type}`]->(t) SET rr += $props"
            session.run(cy, cid=canonical_id, tid=tid, props=props)

        # incoming
        in_q = "MATCH (s)-[r]->(o) WHERE id(o)=$id RETURN type(r) AS ttype, properties(r) AS props, id(s) AS sid"
        for row in session.run(in_q, id=nid):
            rel_type = row['ttype']
            props = row['props'] or {}
            sid = row['sid']
            cy = f"MATCH (s),(c) WHERE id(s)=$sid AND id(c)=$cid MERGE (s)-[rr:`{rel_type}`]->(c) SET rr += $props"
            session.run(cy, sid=sid, cid=canonical_id, props=props)

        # delete old node
        session.run("MATCH (n) WHERE id(n)=$id DETACH DELETE n", id=nid)

    return canonical_id


def run_merge(apply=False, limit=1000):
    groups = get_duplicate_groups(limit=limit)
    print(f"发现 {len(groups)} 个重复组（按名称归一化）。")
    if not groups:
        return

    with driver.session() as session:
        for g in groups:
            ids = g['ids']
            names = g['names']
            # pick canonical id by longest name
            pairs = list(zip(ids, names))
            pairs_sorted = sorted(pairs, key=lambda x: (-len(str(x[1] or '')), x[0]))
            canonical_id = pairs_sorted[0][0]
            canonical_name = pairs_sorted[0][1]
            print(f"处理组 key={g['key']} cnt={g['cnt']} canonical_id={canonical_id} name={canonical_name} ids={ids}")

            if not apply:
                continue

            # try APOC
            ok, res = try_apoc_merge(session, ids)
            if ok:
                print(f"APOC 合并成功，新节点 id={res}")
                continue
            else:
                print(f"APOC 不可用或失败，回退手动合并：{res}")
                try:
                    newid = fallback_merge(session, ids, canonical_id=canonical_id)
                    print(f"手动合并完成，保留 id={newid}")
                except Exception as e:
                    print(f"手动合并失败: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='实际执行合并')
    parser.add_argument('--limit', type=int, default=1000)
    args = parser.parse_args()

    run_merge(apply=args.apply, limit=args.limit)


if __name__ == '__main__':
    main()
