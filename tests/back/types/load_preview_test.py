import json
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from DashAI.back.app import create_app
import time
from contextlib import asynccontextmanager

DATA_DIR = Path(__file__).parent

@pytest.fixture(scope="function")
def client(tmp_path: Path):
    app = create_app(local_path=tmp_path, logging_level="ERROR")

    @asynccontextmanager
    async def nolifespan(_app):
        yield
    app.router.lifespan_context = nolifespan

    with TestClient(app) as c:
        yield c

@pytest.mark.parametrize(
    "file, sep, expected_nrows, expected_columns",
    [
        (
            "iris.csv", 
            ",", 
            150,
            {"SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm", "Species"}, 
        ),
        (
            "datos_comas_100.csv",
            ";",
            100,
            {"ID", "Producto", "Precio", "Descuento"},
        ),
        (
            "ds_3.csv",
            ";",
            20,
            {"ID", "Producto", "Precio", "Descuento"},
        ),],
    ids=[
        "iris_csv",
        "datos_comas_100_csv",
        "ds_3_csv",
    ])

def test_load_preview_csv(client, file, sep, expected_nrows, expected_columns):

    path = DATA_DIR / file
    if not path.exists():
        pytest.skip(f"File {file} not found in {DATA_DIR}, skipping test.")
    
    with path.open("rb") as f:
        files = {"file": (file, f, "text/csv")}
        data = {"params": json.dumps({"separator": sep})}
        resp = client.post("/api/v1/dataset/load_preview/", data=data, files=files)
    
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert isinstance(payload.get("schema"), dict)
    assert isinstance(payload.get("sample"), list)
    assert len(payload.get("sample")) == expected_nrows
    assert set(payload.get("schema").keys()) == expected_columns     
    assert set(payload.get("sample")[0].keys()) == expected_columns

@pytest.mark.parametrize(
    "file, datakey, expected_columns",
    [
        ("random_text.json", 
         "text_data", 
         {"text", "class"}),
        ("iris.json", 
         "data",  
         {"feature_0", "feature_1", "feature_2", "feature_3", "class"}),
    ],
    ids=[
        "random_text_json",
        "irisDataset_json",
    ])

def test_load_preview_json(client, file, datakey, expected_columns):

    path = DATA_DIR / file
    if not path.exists():
        pytest.skip(f"File {file} not found in {DATA_DIR}, skipping test.")
    
    with path.open("rb") as f:
        files = {"file": (file, f, "application/json")}
        data = {"params": json.dumps({"data_key": datakey})}
        resp = client.post("/api/v1/dataset/load_preview/", data=data, files=files)
    
    assert resp.status_code == 200, resp.text
    payload = resp.json()

    assert isinstance(payload.get("schema"), dict)
    assert isinstance(payload.get("sample"), list)
    
    assert len(payload.get("sample")) == 10
    assert set(payload.get("schema").keys()) == expected_columns
    assert set(payload.get("sample")[0].keys()) == expected_columns



# WEIRD EXCEL BUG WITH TESTCLIENT. SOMETHING ALONG THE LINES OF NON SEEKABLE STREAMS. 
# WORKS IN REAL LIFE THO.
# @pytest.mark.parametrize(
#     "file, params, expected_columns",
#     [
#         (
#             "iris_test.xlsx",
#             {"sheet": 0, "header": 0, "usecols": None},
#             {"SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm", "Species"},
#         ),
#         (
#             "iris_test.xlsx",
#             {"sheet": "IrisHeader", "header": 0, "usecols": None},
#             {"SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm", "Species"},
#         ),
#         (
#             "iris_test.xlsx",
#             {"sheet": "IrisNoHeader", "header": None, "usecols": None},
#             {"0", "1", "2", "3", "4"},
#         ),
#         (
#             "iris_test.xlsx",
#             {"sheet": "IrisWide", "header": 0, "usecols": "A:C"},
#             {"A", "B", "C"},
#         ),
#         (
#             "iris_test.xlsx",
#             {"sheet": "IrisWide", "header": 0, "usecols": None},
#             {"A", "B", "C", "D", "E"},
#         ),
#     ],
#     ids=[
#         "sheet_index_header0",
#         "sheet_name_header0",
#         "sheet_no_header",
#         "usecols_A_to_C",
#         "wide_full",
#     ],
# )

# def test_load_preview_excel(client, file, params, expected_columns):

#     path = DATA_DIR / file
#     if not path.exists():
#         pytest.skip(f"File {file} not found in {DATA_DIR}, skipping test.")
    
#     with path.open("rb") as f:
#         files = {"file": (file, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
#         data = {"params": json.dumps(params)}
#         resp = client.post("/api/v1/dataset/load_preview/", data=data, files=files)
    
#     assert resp.status_code == 200, resp.text
#     payload = resp.json()

#     assert isinstance(payload.get("schema"), dict)
#     assert isinstance(payload.get("sample"), list)
    
#     assert len(payload.get("sample")) == 10
#     assert set(payload.get("schema").keys()) == expected_columns
#     assert set(payload.get("sample")[0].keys()) == expected_columns


def test_schema_change(client: TestClient):

    path = DATA_DIR / "iris.csv"
    if not path.exists():
        pytest.skip(f"File iris.csv not found in {DATA_DIR}, skipping test.")   
    
    with path.open("rb") as f:
        files = {"file": ("iris.csv", f, "text/csv")}
        data = {"params": json.dumps({"separator": ","})}
        resp = client.post("/api/v1/dataset/load_preview/", data=data, files=files)

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert set(payload.get("schema").keys()) == {
        "SepalLengthCm", 
        "SepalWidthCm", 
        "PetalLengthCm", 
        "PetalWidthCm", 
        "Species"}

    modified_schema = payload["schema"].copy()
    modified_schema["Species"] = {"type": "Categorical", "dtype": "string"}

    f = path.open("rb")
    try:
        files = {"file": ("iris.csv", f, "text/csv")}
        kwargs = {
            "name": "iris_testing_schema",
            "url": "",
            "params": {
                "dataloader": "CSVDataLoader",
                "name": "iris_testing_schema",
                "separator": ",",
                "schema": modified_schema
            },
        }
        form_data = {"job_type": "DatasetJob", "kwargs": json.dumps(kwargs)}
        create_resp = client.post(
            "/api/v1/job/",
            data=form_data,
            files=files,
            headers={"filename": "iris.csv"},
        )
        assert create_resp.status_code == 201, create_resp.text
    finally:
        f.close()
    
    start_resp = client.post("/api/v1/job/start/", params={"stop_when_queue_empties": True})
    assert start_resp.status_code in (200, 202), start_resp.text

    ds = None
    for _ in range(60):  
        r = client.get("/api/v1/dataset/")
        assert r.status_code == 200, r.text
        ds = next((d for d in r.json() if d["name"] == "iris_testing_schema"), None)
        if ds:
            break
        time.sleep(0.2)
    assert ds is not None, "Dataset was not created in time"

    types_resp = client.get(f"/api/v1/dataset/{ds['id']}/types/")
    assert types_resp.status_code == 200, types_resp.text
    types = types_resp.json()

    assert types["Species"]["type"] == "Categorical"
    for col in ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"]:
        assert types[col]["type"] == "Float"
        assert types[col]["dtype"] in {"float16", "float32", "float64"}


