from urllib.parse import quote

import pyarrow as pa
import pyarrow.ipc as ipc


def test_export_works_for_a_dataset_name_outside_latin1(client, tmp_path):
    dataset_dir = tmp_path / "数据"
    (dataset_dir / "dataset").mkdir(parents=True)
    table = pa.table({"a": [1, 2]})
    with ipc.new_file(str(dataset_dir / "dataset" / "data.arrow"), table.schema) as w:
        w.write_table(table)

    response = client.get(
        "/api/v1/dataset/export/csv", params={"path": dataset_dir.as_posix()}
    )

    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    assert disposition == f"attachment; filename*=utf-8''{quote('数据.csv')}"
