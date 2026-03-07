import json
import csv
from Neo4j_red import driver


def export_nodes(json_path='kg_nodes.json', csv_path='kg_nodes.csv'):
    nodes = []
    keys = set()
    with driver.session() as session:
        res = session.run("MATCH (n) RETURN id(n) AS id, labels(n) AS labels, properties(n) AS props")
        for r in res:
            rec = r.data()
            props = rec.get('props') or {}
            # ensure labels are list
            labels = rec.get('labels') or []
            node = {
                'id': rec.get('id'),
                'labels': labels,
                'props': props
            }
            nodes.append(node)
            for k in props.keys():
                keys.add(k)

    # write json
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)

    # write csv (flatten props)
    fieldnames = ['id', 'labels'] + sorted(keys)
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for n in nodes:
            row = {'id': n['id'], 'labels': '|'.join(n['labels'])}
            for k in keys:
                row[k] = n['props'].get(k)
            w.writerow(row)

    print(f'导出节点：{len(nodes)} 条 -> {json_path}, {csv_path}')


def export_rels(json_path='kg_rels.json', csv_path='kg_rels.csv'):
    rels = []
    prop_keys = set()
    with driver.session() as session:
        res = session.run("MATCH (a)-[r]->(b) RETURN id(r) AS id, id(a) AS start_id, a.实体名称 AS start_name, id(b) AS end_id, b.实体名称 AS end_name, type(r) AS type, properties(r) AS props")
        for r in res:
            rec = r.data()
            props = rec.get('props') or {}
            rel = {
                'id': rec.get('id'),
                'start_id': rec.get('start_id'),
                'start_name': rec.get('start_name'),
                'end_id': rec.get('end_id'),
                'end_name': rec.get('end_name'),
                'type': rec.get('type'),
                'props': props
            }
            rels.append(rel)
            for k in props.keys():
                prop_keys.add(k)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(rels, f, ensure_ascii=False, indent=2)

    fieldnames = ['id', 'start_id', 'start_name', 'end_id', 'end_name', 'type'] + sorted(prop_keys)
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rels:
            row = {k: r.get(k) for k in ['id', 'start_id', 'start_name', 'end_id', 'end_name', 'type']}
            for k in prop_keys:
                row[k] = r['props'].get(k)
            w.writerow(row)

    print(f'导出关系：{len(rels)} 条 -> {json_path}, {csv_path}')


if __name__ == '__main__':
    export_nodes()
    export_rels()
