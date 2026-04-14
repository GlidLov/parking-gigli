from pathlib import Path

# Percorsi relativi alla cartella deploy
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CHARTS_DIR = DATA_DIR / "charts"
RESULTS_CSV = DATA_DIR / "results.csv"
RESULTS_AREA_CSV = DATA_DIR / "results_per_area.csv"
DETECTIONS_JSON = DATA_DIR / "detections_raw.json"
DETECTIONS_DIR = DATA_DIR / "detections"

# Etichette giorni
DAY_LABELS = {
    "2026-04-10": "Ven 10/04",
    "2026-04-11": "Sab 11/04",
    "2026-04-12": "Dom 12/04",
}
DAY_COLORS = {
    "2026-04-10": "#2196F3",
    "2026-04-11": "#FF9800",
    "2026-04-12": "#4CAF50",
}

# Mapping manuale foto -> area (indice 1-based nel piano di volo)
PHOTO_INDEX_TO_AREA = {
    1:  "Area 4 (NE)",
    2:  "Area 5 (S)",
    3:  "Area 5 (S)",
    4:  "Area 5 (S)",
    5:  "Area 7 (SE)",
    6:  "Area 7 (SE)",
    7:  "Area 7 (SE)",
    8:  "Area 4 lato N",
    9:  "Area 4 (NE)",
    10: "Area 4 lato N",
    11: "Area 6 (NE angolo)",
    12: "Area 3 lato N",
    13: "Area 3 lato S",
    14: "Area 10 (centro)",
    15: "Area 10 + Area 3",
    16: "Area 4 (NE)",
    17: "Area 4 (NE)",
    18: "Area 10 (centro)",
    19: "Area 10 + Area 3",
    20: "Area 10 (centro)",
    21: "Area 10 (centro)",
    22: "Area 2 (W)",
    23: "Area 1 (NW)",
    24: "Area 9 (S)",
    25: "Area 9 (S)",
    26: "Area 5 (S)",
}

# Poligoni GPS aree parcheggio
AREA_POLYGONS = [
    {"id": 6,  "label": "Area 6",  "capacity": 84,
     "polygon": [(43.8483, 11.1445), (43.8495, 11.1445), (43.8495, 11.1460), (43.8483, 11.1460)]},
    {"id": 3,  "label": "Area 3",  "capacity": 243,
     "polygon": [(43.8476, 11.1420), (43.8485, 11.1420), (43.8485, 11.1440), (43.8476, 11.1440)]},
    {"id": 4,  "label": "Area 4",  "capacity": 1819,
     "polygon": [(43.8470, 11.1420), (43.8495, 11.1420), (43.8495, 11.1455), (43.8470, 11.1455)]},
    {"id": 1,  "label": "Area 1",  "capacity": 340,
     "polygon": [(43.8473, 11.1390), (43.8495, 11.1390), (43.8495, 11.1420), (43.8473, 11.1420)]},
    {"id": 10, "label": "Area 10", "capacity": 443,
     "polygon": [(43.8465, 11.1408), (43.8476, 11.1408), (43.8476, 11.1425), (43.8465, 11.1425)]},
    {"id": 2,  "label": "Area 2",  "capacity": 150,
     "polygon": [(43.8448, 11.1385), (43.8473, 11.1385), (43.8473, 11.1408), (43.8448, 11.1408)]},
    {"id": 11, "label": "Area 11", "capacity": 371,
     "polygon": [(43.8458, 11.1420), (43.8465, 11.1420), (43.8465, 11.1435), (43.8458, 11.1435)]},
    {"id": 8,  "label": "Area 8",  "capacity": 70,
     "polygon": [(43.8448, 11.1408), (43.8458, 11.1408), (43.8458, 11.1420), (43.8448, 11.1420)]},
    {"id": 9,  "label": "Area 9",  "capacity": 27,
     "polygon": [(43.8448, 11.1420), (43.8455, 11.1420), (43.8455, 11.1440), (43.8448, 11.1440)]},
    {"id": 5,  "label": "Area 5",  "capacity": 237,
     "polygon": [(43.8455, 11.1420), (43.8465, 11.1420), (43.8465, 11.1445), (43.8455, 11.1445)]},
    {"id": 7,  "label": "Area 7",  "capacity": 498,
     "polygon": [(43.8448, 11.1435), (43.8470, 11.1435), (43.8470, 11.1460), (43.8448, 11.1460)]},
]
