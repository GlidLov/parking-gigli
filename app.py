"""Dashboard Streamlit per esplorazione interattiva dei risultati."""

import json
import math
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# === CONFIG (inline - no external module) ===
_DIR = Path(__file__).resolve().parent
DATA_DIR = _DIR / "data"
CHARTS_DIR = DATA_DIR / "charts"
RESULTS_CSV = DATA_DIR / "results.csv"
RESULTS_AREA_CSV = DATA_DIR / "results_per_area.csv"
DETECTIONS_JSON = DATA_DIR / "detections_raw.json"
DETECTIONS_DIR = DATA_DIR / "detections"

DAY_LABELS = {"2026-04-10": "Ven 10/04", "2026-04-11": "Sab 11/04", "2026-04-12": "Dom 12/04"}
DAY_COLORS = {"2026-04-10": "#2196F3", "2026-04-11": "#FF9800", "2026-04-12": "#4CAF50"}

PHOTO_INDEX_TO_AREA = {
    1: "Area 4 (NE)", 2: "Area 5 (S)", 3: "Area 5 (S)", 4: "Area 5 (S)",
    5: "Area 7 (SE)", 6: "Area 7 (SE)", 7: "Area 7 (SE)", 8: "Area 4 lato N",
    9: "Area 4 (NE)", 10: "Area 4 lato N", 11: "Area 6 (NE angolo)",
    12: "Area 3 lato N", 13: "Area 3 lato S", 14: "Area 10 (centro)",
    15: "Area 10 + Area 3", 16: "Area 4 (NE)", 17: "Area 4 (NE)",
    18: "Area 10 (centro)", 19: "Area 10 + Area 3", 20: "Area 10 (centro)",
    21: "Area 10 (centro)", 22: "Area 2 (W)", 23: "Area 1 (NW)",
    24: "Area 9 (S)", 25: "Area 9 (S)", 26: "Area 5 (S)",
}

AREA_POLYGONS = [
    {"id": 6, "label": "Area 6", "capacity": 84, "polygon": [(43.8483,11.1445),(43.8495,11.1445),(43.8495,11.1460),(43.8483,11.1460)]},
    {"id": 3, "label": "Area 3", "capacity": 243, "polygon": [(43.8476,11.1420),(43.8485,11.1420),(43.8485,11.1440),(43.8476,11.1440)]},
    {"id": 4, "label": "Area 4", "capacity": 1819, "polygon": [(43.8470,11.1420),(43.8495,11.1420),(43.8495,11.1455),(43.8470,11.1455)]},
    {"id": 1, "label": "Area 1", "capacity": 340, "polygon": [(43.8473,11.1390),(43.8495,11.1390),(43.8495,11.1420),(43.8473,11.1420)]},
    {"id": 10, "label": "Area 10", "capacity": 443, "polygon": [(43.8465,11.1408),(43.8476,11.1408),(43.8476,11.1425),(43.8465,11.1425)]},
    {"id": 2, "label": "Area 2", "capacity": 150, "polygon": [(43.8448,11.1385),(43.8473,11.1385),(43.8473,11.1408),(43.8448,11.1408)]},
    # Area 11: rimossa (contata separatamente da terra)
    # Area 8: rimossa (troppo piccola, non significativa)
    {"id": 9, "label": "Area 9", "capacity": 27, "polygon": [(43.8448,11.1420),(43.8455,11.1420),(43.8455,11.1440),(43.8448,11.1440)]},
    {"id": 5, "label": "Area 5", "capacity": 237, "polygon": [(43.8455,11.1420),(43.8465,11.1420),(43.8465,11.1445),(43.8455,11.1445)]},
    {"id": 7, "label": "Area 7", "capacity": 498, "polygon": [(43.8448,11.1435),(43.8470,11.1435),(43.8470,11.1460),(43.8448,11.1460)]},
]
PARKING_AREAS = {a["id"]: {"lat": sum(p[0] for p in a["polygon"])/4, "lon": sum(p[1] for p in a["polygon"])/4, "capacity": a["capacity"], "label": a["label"]} for a in AREA_POLYGONS}
# === END CONFIG ===

st.set_page_config(page_title="Parcheggio I Gigli - Analisi", layout="wide")


@st.cache_data(ttl=60)
def load_photo_area_map() -> dict:
    """Mappa ogni foto alla sua area parcheggio usando il mapping manuale per indice.

    Il piano di volo e' sempre lo stesso: la foto N-esima (ordinata per nome)
    di ogni missione corrisponde sempre alla stessa area.

    Returns:
        {"DJI_xxx.jpeg": "Area 4 (NE)", ...}
    """
    pass  # PHOTO_INDEX_TO_AREA already imported at top

    photo_map = {}

    # Scansiona tutte le cartelle detection per trovare le foto
    if not DETECTIONS_DIR.exists():
        return {}

    for day_dir in sorted(DETECTIONS_DIR.iterdir()):
        if not day_dir.is_dir():
            continue
        for hour_dir in sorted(day_dir.iterdir()):
            if not hour_dir.is_dir():
                continue
            photos = sorted(
                list(hour_dir.glob("*.jpeg")) + list(hour_dir.glob("*.jpg"))
            )
            for i, photo in enumerate(photos):
                # Indice 1-based come nel mapping
                idx = i + 1
                area = PHOTO_INDEX_TO_AREA.get(idx)
                if area is None and idx > 26:
                    # Foto extra (27a nelle missioni integrazione): usa l'area della 26a
                    area = PHOTO_INDEX_TO_AREA.get(26, "?")
                photo_map[photo.name] = area or "?"

    return photo_map


@st.cache_data(ttl=60)
def load_photo_counts() -> dict:
    """Conta veicoli (solo car) per ogni foto, da detections_raw.json.

    Returns:
        {("2026-04-10", "1000", "DJI_xxx.jpeg"): 85, ...}
    """
    raw_path = DETECTIONS_JSON
    if not raw_path.exists():
        return {}

    def normalize_hour(h):
        s = str(h).zfill(4)
        hh, mm = int(s[:2]), int(s[2:])
        if mm >= 30: hh += 1
        return f"{hh:02d}00"

    with open(raw_path) as f:
        raw = json.load(f)

    counts = {}
    for day, missions in raw.items():
        for hour, dets in missions.items():
            norm_hour = normalize_hour(hour)
            for d in dets:
                name = d.get("photo", "")
                if not name:
                    continue
                key = (day, norm_hour, name)
                if key not in counts:
                    counts[key] = 0
                if d.get("class_name") == "car":
                    counts[key] += 1

    return counts


@st.cache_data(ttl=60)
def load_area_data() -> pd.DataFrame:
    """Carica il CSV con i conteggi per area, interpolando 08:00/09:00 del venerdì."""
    area_csv = RESULTS_AREA_CSV
    if not area_csv.exists():
        return pd.DataFrame()
    df = pd.read_csv(area_csv)
    # Interpola 08:00 e 09:00 del venerdì 10/04 (mancanti) usando ratio da sab/dom
    fri = "2026-04-10"
    df["ora"] = df["ora"].astype(int)
    fri_hours = set(df[df["giorno"] == fri]["ora"].unique())
    if 800 not in fri_hours or 900 not in fri_hours:
        other_days = df[df["giorno"] != fri]
        fri_df = df[df["giorno"] == fri]
        new_rows = []
        for area in fri_df["area"].unique():
            fri_area = fri_df[fri_df["area"] == area]
            if fri_area.empty:
                continue
            first_h = fri_area["ora"].min()  # tipicamente 1000
            first_row = fri_area[fri_area["ora"] == first_h].iloc[0]
            # Calcola ratio medio da altri giorni: h/first_h
            for h in [800, 900]:
                if h in fri_hours:
                    continue
                ratios = []
                for od in other_days["giorno"].unique():
                    od_area = other_days[(other_days["giorno"] == od) & (other_days["area"] == area)]
                    h_row = od_area[od_area["ora"] == h]
                    ref_row = od_area[od_area["ora"] == first_h]
                    if not h_row.empty and not ref_row.empty and ref_row["total"].values[0] > 0:
                        ratios.append(h_row["total"].values[0] / ref_row["total"].values[0])
                if not ratios:
                    continue
                r = sum(ratios) / len(ratios)
                ora_str = str(h).zfill(4)
                new_rows.append({
                    "giorno": fri, "ora": h,
                    "ora_label": f"{ora_str[:2]}:{ora_str[2:]}",
                    "area": area,
                    "car": round(first_row["car"] * r),
                    "bus": round(first_row["bus"] * r),
                    "truck": round(first_row["truck"] * r),
                    "total": round(first_row["total"] * r),
                })
        if new_rows:
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            df = df.sort_values(["giorno", "ora", "area"]).reset_index(drop=True)
    return df


@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    if not RESULTS_CSV.exists():
        st.error(f"CSV non trovato: {RESULTS_CSV}. Esegui prima la pipeline.")
        st.stop()
    return pd.read_csv(RESULTS_CSV)


def main():
    st.title("Parcheggio Centro Commerciale I Gigli")
    st.subheader("Analisi Occupazione da Foto Drone")

    df = load_data()

    day_labels = DAY_LABELS
    colors = DAY_COLORS

    # Sidebar filtri
    st.sidebar.header("Filtri")
    days = sorted(df["giorno"].unique())
    selected_days = st.sidebar.multiselect(
        "Giorni",
        days,
        default=days,
        format_func=lambda d: day_labels.get(d, d),
    )

    hours = sorted(df["ora_label"].unique())
    hour_range = st.sidebar.select_slider(
        "Fascia oraria",
        options=hours,
        value=(hours[0], hours[-1]),
    )
    h_start, h_end = hours.index(hour_range[0]), hours.index(hour_range[1])
    selected_hours = hours[h_start:h_end + 1]

    df_filtered = df[
        (df["giorno"].isin(selected_days)) &
        (df["ora_label"].isin(selected_hours))
    ]

    # KPI — font ridotto per evitare troncamento
    st.markdown("""<style>
    [data-testid="stMetric"] { font-size: 0.85rem; }
    [data-testid="stMetricValue"] { font-size: 1.3rem; }
    [data-testid="stMetricLabel"] { font-size: 0.75rem; }
    </style>""", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Totale rilevamenti", f"{df_filtered['total'].sum():,}")
    col2.metric("Media oraria", f"{df_filtered['total'].mean():.0f}")
    col3.metric("Picco max", f"{df_filtered['total'].max():,}")
    if len(df_filtered) > 0:
        peak_row = df_filtered.loc[df_filtered["total"].idxmax()]
        col4.metric("Ora picco",
                     f"{day_labels.get(peak_row['giorno'], peak_row['giorno'])} {peak_row['ora_label']}")

    st.divider()

    # Grafico andamento
    tab1, tab2, tab3, tab4 = st.tabs(["Andamento Orario", "Heatmap", "Confronto Giorni", "Per Area"])

    with tab1:
        def ora_to_float(v):
            s = str(v).zfill(4)
            return int(s[:2]) + int(s[2:]) / 60

        fig, ax = plt.subplots(figsize=(12, 5))
        pass  # colors already defined from DAY_COLORS
        for day in sorted(df_filtered["giorno"].unique()):
            day_df = df_filtered[df_filtered["giorno"] == day].sort_values("ora")
            x_vals = [ora_to_float(o) for o in day_df["ora"]]
            ax.plot(x_vals, day_df["total"],
                    marker="o", linewidth=2, markersize=6,
                    color=colors.get(day, "gray"),
                    label=day_labels.get(day, day))

        all_hours = sorted(df_filtered["ora"].unique())
        tick_vals = [ora_to_float(h) for h in all_hours]
        tick_labels = [f"{str(h).zfill(4)[:2]}:{str(h).zfill(4)[2:]}" for h in all_hours]
        ax.set_xticks(tick_vals)
        ax.set_xticklabels(tick_labels, rotation=45, ha="right")
        ax.set_xlabel("Ora")
        ax.set_ylabel("Veicoli totali")
        ax.set_title("Occupazione Parcheggio - Andamento Orario")
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        st.pyplot(fig)

    with tab2:
        if not df_filtered.empty:
            pivot = df_filtered.pivot_table(
                index="giorno", columns="ora_label", values="total", aggfunc="first"
            )
            fig2, ax2 = plt.subplots(figsize=(14, 4))
            im = ax2.imshow(pivot.values, cmap="YlOrRd", aspect="auto")
            ax2.set_xticks(range(len(pivot.columns)))
            ax2.set_xticklabels(pivot.columns, rotation=45, ha="right")
            ax2.set_yticks(range(len(pivot.index)))
            ax2.set_yticklabels([day_labels.get(d, d) for d in pivot.index])
            for i in range(len(pivot.index)):
                for j in range(len(pivot.columns)):
                    val = pivot.values[i, j]
                    if not pd.isna(val):
                        ax2.text(j, i, f"{int(val)}", ha="center", va="center",
                                 fontsize=10, fontweight="bold",
                                 color="white" if val > pivot.values[~pd.isna(pivot.values)].mean() else "black")
            plt.colorbar(im, ax=ax2, label="Veicoli")
            plt.tight_layout()
            st.pyplot(fig2)

    with tab3:
        fig3, ax3 = plt.subplots(figsize=(14, 5))
        common = df_filtered.groupby("ora_label").filter(
            lambda g: g["giorno"].nunique() >= 2
        )
        if not common.empty:
            ch = sorted(common["ora_label"].unique())
            cd = sorted(common["giorno"].unique())
            bw = 0.8 / len(cd)
            for i, day in enumerate(cd):
                dd = common[common["giorno"] == day]
                vals = [dd[dd["ora_label"] == h]["total"].values[0]
                        if len(dd[dd["ora_label"] == h]) > 0 else 0 for h in ch]
                x = [j + i * bw for j in range(len(ch))]
                ax3.bar(x, vals, bw, label=day_labels.get(day, day),
                        color=colors.get(day, "gray"), alpha=0.85)
            ax3.set_xticks([j + bw * (len(cd) - 1) / 2 for j in range(len(ch))])
            ax3.set_xticklabels(ch, rotation=45)
            ax3.legend()
        ax3.set_ylabel("Veicoli")
        ax3.grid(True, alpha=0.3, axis="y")
        plt.tight_layout()
        st.pyplot(fig3)

    with tab4:
        df_area = load_area_data()
        if df_area.empty:
            st.info("Dati per area non disponibili. Esegui il reprocessing.")
        else:
            pass  # AREA_POLYGONS already imported at top
            area_cap = {a["label"]: a["capacity"] for a in AREA_POLYGONS}

            def _ora_float(v):
                s = str(int(v)).zfill(4)
                return int(s[:2]) + int(s[2:]) / 60

            def _set_ora_ticks(ax, df_sub):
                all_h = sorted(df_sub["ora"].unique())
                tv = [_ora_float(h) for h in all_h]
                tl = [f"{str(int(h)).zfill(4)[:2]}:{str(int(h)).zfill(4)[2:]}" for h in all_h]
                ax.set_xticks(tv)
                ax.set_xticklabels(tl, rotation=45, ha="right")

            df_area["ora"] = df_area["ora"].astype(int)
            df_area_f = df_area[
                (df_area["giorno"].isin(selected_days)) &
                (df_area["ora_label"].isin(selected_hours))
            ]
            # Escludi "Fuori area" dai grafici
            df_area_f = df_area_f[df_area_f["area"] != "Fuori area"]

            if not df_area_f.empty:
                all_areas = sorted(df_area_f["area"].unique())
                sel_areas = st.multiselect("Aree", all_areas, default=all_areas, key="area_sel")
                df_area_f = df_area_f[df_area_f["area"].isin(sel_areas)]

                area_colors_map = dict(zip(sorted(all_areas), plt.cm.tab20.colors))

                # --- 1. Tabella riepilogativa ---
                st.subheader("Riepilogo per Area")
                summary_rows = []
                for area in sorted(sel_areas):
                    cap = area_cap.get(area, 0)
                    adf = df_area_f[df_area_f["area"] == area]
                    for day in sorted(adf["giorno"].unique()):
                        ddf = adf[adf["giorno"] == day]
                        if ddf.empty:
                            continue
                        max_v = int(ddf["car"].max())
                        peak_row = ddf.loc[ddf["car"].idxmax()]
                        occ = round(max_v / cap * 100, 1) if cap > 0 else 0
                        summary_rows.append({
                            "Area": area,
                            "Posti": cap,
                            "Giorno": day_labels.get(day, day),
                            "Media": round(ddf["car"].mean()),
                            "Max": max_v,
                            "Ora picco": peak_row["ora_label"],
                            "Occ. max %": occ,
                        })
                if summary_rows:
                    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

                # --- 2. Heatmap occupazione % per giorno ---
                st.subheader("Heatmap Occupazione % per Area")
                hm_day = st.selectbox("Giorno", sorted(df_area_f["giorno"].unique()),
                                       format_func=lambda d: day_labels.get(d, d), key="hm_day")
                df_hm = df_area_f[df_area_f["giorno"] == hm_day]
                if not df_hm.empty:
                    pivot_raw = df_hm.pivot_table(index="area", columns="ora_label", values="car", aggfunc="first")
                    pivot = pivot_raw.fillna(0)
                    pct = pivot.astype(float).copy()
                    for area in pct.index:
                        cap = area_cap.get(area, 1)
                        pct.loc[area] = pct.loc[area] / cap * 100

                    from matplotlib.colors import LinearSegmentedColormap
                    hm_cmap = LinearSegmentedColormap.from_list("occ", [
                        (0.0, "#1a9641"),
                        (0.3, "#a6d96a"),
                        (0.5, "#ffffbf"),
                        (0.7, "#fdae61"),
                        (1.0, "#d7191c"),
                    ])

                    fig_hm, ax_hm = plt.subplots(figsize=(16, max(4, len(pivot.index) * 0.7)))
                    im = ax_hm.imshow(pct.values, cmap=hm_cmap, aspect="auto", vmin=0, vmax=100)
                    ax_hm.set_xticks(range(len(pivot.columns)))
                    ax_hm.set_xticklabels(pivot.columns, rotation=45, ha="right")
                    ax_hm.set_yticks(range(len(pivot.index)))
                    ax_hm.set_yticklabels([f"{a} ({area_cap.get(a, '?')}p)" for a in pivot.index])
                    for i in range(len(pivot.index)):
                        for j in range(len(pivot.columns)):
                            val = pivot.values[i, j]
                            pval = pct.values[i, j]
                            if not pd.isna(val):
                                color = "black"
                                ax_hm.text(j, i, f"{int(val)}\n{pval:.0f}%", ha="center", va="center",
                                           fontsize=8, fontweight="bold", color=color)
                    plt.colorbar(im, ax=ax_hm, label="% Occupazione", shrink=0.8)
                    ax_hm.set_title(f"Occupazione per Area - {day_labels.get(hm_day, hm_day)}")
                    plt.tight_layout()
                    st.pyplot(fig_hm)

                # --- 3. Andamento per area (singolo giorno) ---
                st.subheader("Andamento Orario per Area")
                and_day = st.selectbox("Giorno", sorted(df_area_f["giorno"].unique()),
                                        format_func=lambda d: day_labels.get(d, d), key="and_day")
                df_ad = df_area_f[df_area_f["giorno"] == and_day]
                fig_a, ax_a = plt.subplots(figsize=(14, 6))
                for area in sorted(df_ad["area"].unique()):
                    adf = df_ad[df_ad["area"] == area].sort_values("ora")
                    cap = area_cap.get(area, 0)
                    lbl = f"{area} ({cap}p)" if cap else area
                    xv = [_ora_float(o) for o in adf["ora"]]
                    ax_a.plot(xv, adf["car"],
                              marker="o", linewidth=2, markersize=5,
                              color=area_colors_map.get(area, "gray"), label=lbl)
                _set_ora_ticks(ax_a, df_ad)
                ax_a.set_xlabel("Ora")
                ax_a.set_ylabel("Auto")
                ax_a.set_title(f"Andamento per Area - {day_labels.get(and_day, and_day)}")
                ax_a.legend(loc="upper left", fontsize=8, ncol=2)
                ax_a.grid(True, alpha=0.3)
                plt.tight_layout()
                st.pyplot(fig_a)

                # --- 3b. Andamento per singola area (3 giorni sovrapposti) ---
                st.subheader("Andamento Singola Area - Confronto Giorni")
                single_area = st.selectbox("Area", sorted(sel_areas), key="single_area")
                sa_cap = area_cap.get(single_area, 0)
                sa_df = df_area_f[df_area_f["area"] == single_area]

                fig_sa, ax_sa = plt.subplots(figsize=(14, 5))
                for day in sorted(sa_df["giorno"].unique()):
                    ddf = sa_df[sa_df["giorno"] == day].sort_values("ora")
                    xv = [_ora_float(o) for o in ddf["ora"]]
                    ax_sa.plot(xv, ddf["car"],
                               marker="o", linewidth=2, markersize=6,
                               color=colors.get(day, "gray"),
                               label=day_labels.get(day, day))
                sa_max = sa_df["car"].max()
                sa_ytop = max(sa_max, sa_cap) * 1.1 if sa_cap > 0 else sa_max * 1.15
                ax_sa.set_ylim(0, max(sa_ytop, 5))
                if sa_cap > 0:
                    ax_sa.axhline(sa_cap, color="red", linestyle="--", alpha=0.6, linewidth=1.5,
                                  label=f"Capacita ({sa_cap})")
                _set_ora_ticks(ax_sa, sa_df)
                ax_sa.set_xlabel("Ora")
                ax_sa.set_ylabel("Auto")
                ax_sa.set_title(f"{single_area} — Andamento 3 Giorni")
                ax_sa.legend()
                ax_sa.grid(True, alpha=0.3)
                plt.tight_layout()
                st.pyplot(fig_sa)

                # Mini-griglia: tutti i grafici per area
                st.subheader("Panoramica Tutte le Aree")
                areas_sorted = sorted(sel_areas)
                n_areas = len(areas_sorted)
                cols_per_row = 3
                for row_start in range(0, n_areas, cols_per_row):
                    row_areas = areas_sorted[row_start:row_start + cols_per_row]
                    st_cols = st.columns(len(row_areas))
                    for ci, area in enumerate(row_areas):
                        with st_cols[ci]:
                            cap = area_cap.get(area, 0)
                            adf = df_area_f[df_area_f["area"] == area]
                            fig_mini, ax_mini = plt.subplots(figsize=(5, 3))
                            for day in sorted(adf["giorno"].unique()):
                                ddf = adf[adf["giorno"] == day].sort_values("ora")
                                xv = [_ora_float(o) for o in ddf["ora"]]
                                ax_mini.plot(xv, ddf["car"],
                                             marker=".", linewidth=1.5, markersize=3,
                                             color=colors.get(day, "gray"))
                            # Scala Y: 0 fino a max(dati, capacita) + 10% margine
                            max_val = adf["car"].max()
                            y_top = max(max_val, cap) * 1.1 if cap > 0 else max_val * 1.15
                            ax_mini.set_ylim(0, max(y_top, 5))

                            if cap > 0:
                                ax_mini.axhline(cap, color="red", linestyle="--", alpha=0.4, linewidth=1)
                            # Tick semplificati per mini-grafici
                            mini_hours = sorted(adf["ora"].unique())
                            mini_tv = [_ora_float(h) for h in mini_hours]
                            mini_tl = [f"{str(int(h)).zfill(4)[:2]}:00" for h in mini_hours]
                            step = max(1, len(mini_tv) // 5)
                            ax_mini.set_xticks(mini_tv[::step])
                            ax_mini.set_xticklabels(mini_tl[::step], rotation=45, ha="right", fontsize=6)
                            ax_mini.set_title(f"{area} ({cap}p)", fontsize=10)
                            ax_mini.tick_params(axis="y", labelsize=7)
                            ax_mini.grid(True, alpha=0.2)
                            plt.tight_layout()
                            st.pyplot(fig_mini)

                # --- 4. Picco per area (bar chart 3 giorni) ---
                st.subheader("Picco Giornaliero per Area")
                days_in = sorted(df_area_f["giorno"].unique())
                areas_in = sorted(df_area_f["area"].unique())
                n_d = len(days_in)
                bw = 0.8 / max(n_d, 1)
                fig_pk, ax_pk = plt.subplots(figsize=(14, 6))
                for i, day in enumerate(days_in):
                    vals = []
                    for area in areas_in:
                        adf = df_area_f[(df_area_f["area"] == area) & (df_area_f["giorno"] == day)]
                        vals.append(int(adf["car"].max()) if not adf.empty else 0)
                    x = [j + i * bw for j in range(len(areas_in))]
                    ax_pk.bar(x, vals, bw, label=day_labels.get(day, day),
                              color=colors.get(day, "gray"), alpha=0.85)
                # Linee capacita
                for j, area in enumerate(areas_in):
                    cap = area_cap.get(area, 0)
                    if cap > 0:
                        ax_pk.plot([j - 0.1, j + n_d * bw], [cap, cap],
                                   color="red", linewidth=1, linestyle="--", alpha=0.5)
                ax_pk.set_xticks([j + bw * (n_d - 1) / 2 for j in range(len(areas_in))])
                ax_pk.set_xticklabels(areas_in, rotation=35, ha="right", fontsize=9)
                ax_pk.set_ylabel("Auto (picco)")
                ax_pk.set_title("Picco per Area e Giorno (linea rossa = capacita)")
                ax_pk.legend()
                ax_pk.grid(True, alpha=0.2, axis="y")
                plt.tight_layout()
                st.pyplot(fig_pk)

                # --- 5. Tabella pivot dettaglio ---
                st.subheader("Dettaglio Numerico")
                det_day = st.selectbox("Giorno", sorted(df_area_f["giorno"].unique()),
                                        format_func=lambda d: day_labels.get(d, d), key="det_day")
                df_det = df_area_f[df_area_f["giorno"] == det_day]
                pivot_det = df_det.pivot_table(index="area", columns="ora_label", values="car", aggfunc="first")
                st.dataframe(pivot_det, use_container_width=True)
            else:
                st.info("Nessun dato per i filtri selezionati.")

    # Tabella dati
    st.divider()
    st.subheader("Dati Tabulari")
    display_df = df_filtered[["giorno", "ora_label", "car", "bus", "truck", "total"]].copy()
    display_df.columns = ["Giorno", "Ora", "Auto", "Bus", "Camion", "Totale"]
    display_df["Giorno"] = display_df["Giorno"].map(lambda d: day_labels.get(d, d))
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Confronto foto tra giorni
    st.divider()
    st.subheader("Confronto Foto tra Giorni")

    # Verifica se le foto sono disponibili localmente
    _has_photos = DETECTIONS_DIR.exists() and any(DETECTIONS_DIR.iterdir()) if DETECTIONS_DIR.exists() else False
    if not _has_photos:
        st.info("Le foto annotate non sono disponibili in questa versione cloud. "
                "Per visualizzare le foto con le detection, usa la versione locale della dashboard.")
    else:
        st.caption("Seleziona un'ora e una foto per confrontare la stessa posizione in giorni diversi.")

    cmp_col1, cmp_col2 = st.columns(2)
    with cmp_col1:
        # Ore comuni a tutti i giorni selezionati
        all_days = sorted(df["giorno"].unique())
        cmp_days = st.multiselect(
            "Giorni da confrontare",
            all_days,
            default=all_days,
            format_func=lambda d: day_labels.get(d, d),
            key="cmp_days",
        )
    with cmp_col2:
        # Ore disponibili per almeno 2 dei giorni selezionati
        if len(cmp_days) >= 2:
            from collections import Counter
            hour_counts = Counter()
            for d in cmp_days:
                for h in df[df["giorno"] == d]["ora"].unique():
                    hour_counts[h] += 1
            common_hours = sorted([h for h, c in hour_counts.items() if c >= 2])
            cmp_hour = st.selectbox(
                "Ora",
                common_hours,
                format_func=lambda h: f"{str(h).zfill(4)[:2]}:{str(h).zfill(4)[2:]}",
                key="cmp_hour",
            )
        else:
            cmp_hour = None
            st.info("Seleziona almeno 2 giorni.")

    if cmp_hour is not None and len(cmp_days) >= 2:
        hour_str = str(cmp_hour).zfill(4)

        # Raccogli foto per ogni giorno a quell'ora
        day_photos = {}
        for d in sorted(cmp_days):
            d_dir = DETECTIONS_DIR / d / hour_str
            if d_dir.exists():
                day_photos[d] = sorted(d_dir.glob("*.jpeg")) + sorted(d_dir.glob("*.jpg"))

        if day_photos:
            import base64 as b64mod

            area_map = load_photo_area_map()

            # Trova l'indice massimo di foto tra i giorni
            max_photos = max(len(p) for p in day_photos.values())

            # Etichette area per lo slider
            # Usa le foto del giorno con piu' foto come riferimento
            ref_day = max(day_photos, key=lambda d: len(day_photos[d]))
            ref_photos = day_photos[ref_day]

            def cmp_photo_label(idx):
                if idx < len(ref_photos):
                    area = area_map.get(ref_photos[idx].name, "?")
                    return f"Foto {idx+1} - {area}"
                return f"Foto {idx+1}"

            photo_idx = st.selectbox(
                "Posizione drone",
                range(max_photos),
                format_func=cmp_photo_label,
                key="cmp_photo_idx",
            )

            # Conteggi per-foto (solo area inquadrata)
            photo_counts = load_photo_counts()
            metric_cols = st.columns(len(cmp_days))
            for i, d in enumerate(sorted(cmp_days)):
                with metric_cols[i]:
                    photos_d = day_photos.get(d, [])
                    label = day_labels.get(d, d)
                    if photo_idx < len(photos_d):
                        key = (d, hour_str, photos_d[photo_idx].name)
                        count = photo_counts.get(key, 0)
                        st.metric(label, f"{count} auto (in foto)")
                    else:
                        st.metric(label, "N/D")

            # Prepara immagini base64 per i giorni selezionati
            sorted_days = sorted(cmp_days)
            imgs_b64 = []
            img_labels = []
            for d in sorted_days:
                photos_d = day_photos.get(d, [])
                if photo_idx < len(photos_d):
                    with open(photos_d[photo_idx], "rb") as f:
                        imgs_b64.append(b64mod.b64encode(f.read()).decode())
                    img_labels.append(day_labels.get(d, d))
                else:
                    imgs_b64.append("")
                    img_labels.append(day_labels.get(d, d) + " (N/D)")

            n = len(imgs_b64)
            pct = f"{100/n:.1f}%"

            # HTML: immagini affiancate con zoom/pan sincronizzato
            imgs_html = ""
            for i, (b, label) in enumerate(zip(imgs_b64, img_labels)):
                if b:
                    imgs_html += f'''
                    <div class="pane" style="width:{pct}">
                        <div class="pane-label">{label}</div>
                        <div class="pane-clip"><img class="si" src="data:image/jpeg;base64,{b}" /></div>
                    </div>'''
                else:
                    imgs_html += f'''
                    <div class="pane" style="width:{pct}">
                        <div class="pane-label">{label}</div>
                        <div class="pane-clip" style="display:flex;align-items:center;justify-content:center;color:#888;">
                            Non disponibile</div>
                    </div>'''

            st.components.v1.html(f"""
            <style>
                * {{ margin:0; padding:0; box-sizing:border-box; }}
                html, body {{ overflow:hidden; background:#0a0a0a; }}
                .lb-bg {{
                    width: 100%; height: 880px;
                    display: flex; gap: 2px;
                    cursor: grab;
                }}
                .lb-bg:active {{ cursor: grabbing; }}
                .pane {{
                    flex: 1; position: relative; overflow: hidden;
                    min-width: 0; height: 880px;
                }}
                .pane-label {{
                    position: absolute; top: 10px; left: 10px; z-index: 5;
                    background: rgba(0,0,0,0.75); color: #fff; padding: 5px 14px;
                    border-radius: 5px; font-size: 15px; font-weight: bold;
                    font-family: sans-serif;
                }}
                .si {{
                    position: absolute; transform-origin: 0 0; max-width: none;
                }}
                .lb-controls {{
                    position: absolute; top: 12px; right: 12px; z-index: 100;
                    display: flex; gap: 5px;
                }}
                .lb-controls button {{
                    width: 40px; height: 40px; font-size: 20px;
                    border: none; border-radius: 7px;
                    background: rgba(255,255,255,0.88); cursor: pointer; font-weight: bold;
                }}
                .lb-controls button:hover {{ background: #fff; }}
                .lb-info {{
                    position: absolute; bottom: 12px; right: 12px; z-index: 100;
                    background: rgba(0,0,0,0.65); color: #fff; padding: 4px 12px;
                    border-radius: 5px; font-family: monospace; font-size: 13px;
                }}
            </style>
            <div style="position:relative;width:100%;height:880px;">
            <div class="lb-bg" id="lbBg">
                {imgs_html}
            </div>
            <div class="lb-controls">
                <button onclick="szi()">+</button>
                <button onclick="szo()">&minus;</button>
                <button onclick="srs()">&#8634;</button>
            </div>
            <div class="lb-info" id="sinfo">100%</div>
            </div>
            <script>
            (function() {{
                const bg = document.getElementById('lbBg');
                const imgs = bg.querySelectorAll('.si');
                const info = document.getElementById('sinfo');
                let s = 1, px = 0, py = 0;
                let iw = 4032, ih = 3024;  // image natural size
                let dr = false, ox, oy;

                function clamp() {{
                    // Keep image covering the pane — never show black
                    if (imgs.length === 0) return;
                    const clip = imgs[0].parentElement;
                    const cw = clip.clientWidth, ch = clip.clientHeight;
                    const sw = iw * s, sh = ih * s;

                    // If image is smaller than pane, center it
                    if (sw <= cw) {{
                        px = (cw - sw) / 2;
                    }} else {{
                        // Don't let right edge go past right of pane
                        if (px > 0) px = 0;
                        // Don't let left edge go past left of pane
                        if (px + sw < cw) px = cw - sw;
                    }}
                    if (sh <= ch) {{
                        py = (ch - sh) / 2;
                    }} else {{
                        if (py > 0) py = 0;
                        if (py + sh < ch) py = ch - sh;
                    }}
                }}

                function upd() {{
                    clamp();
                    imgs.forEach(img => {{
                        img.style.transform = `translate(${{px}}px,${{py}}px) scale(${{s}})`;
                    }});
                    info.textContent = Math.round(s * 100) + '%';
                }}

                function fit() {{
                    if (imgs.length === 0) return;
                    const clip = imgs[0].parentElement;
                    const cw = clip.clientWidth || clip.offsetWidth || 400;
                    const ch = clip.clientHeight || clip.offsetHeight || 880;
                    const img0 = imgs[0];
                    iw = img0.naturalWidth || 4032;
                    ih = img0.naturalHeight || 3024;
                    s = Math.min(cw / iw, ch / ih);
                    px = (cw - iw * s) / 2;
                    py = (ch - ih * s) / 2;
                    upd();
                }}

                // Fit on load — retry with delay to handle iframe rendering
                let loaded = 0;
                function tryFit() {{
                    if (imgs.length === 0) return;
                    const clip = imgs[0].parentElement;
                    if (clip.clientWidth > 0 && clip.clientHeight > 0) {{
                        fit();
                    }} else {{
                        setTimeout(tryFit, 100);
                    }}
                }}
                imgs.forEach(img => {{
                    img.addEventListener('load', function() {{
                        loaded++;
                        if (loaded === imgs.length) tryFit();
                    }});
                    if (img.complete) loaded++;
                }});
                if (loaded === imgs.length && imgs.length > 0) tryFit();
                // Extra fallback
                setTimeout(tryFit, 500);

                // Wheel zoom towards cursor
                bg.addEventListener('wheel', function(e) {{
                    e.preventDefault();
                    const clip = imgs[0].parentElement;
                    const pr = clip.getBoundingClientRect();
                    const mx = e.clientX - pr.left, my = e.clientY - pr.top;
                    const os = s;
                    s = Math.max(0.1, Math.min(30, s * (e.deltaY > 0 ? 0.9 : 1.1)));
                    px = mx - (mx - px) * (s / os);
                    py = my - (my - py) * (s / os);
                    upd();
                }});

                // Drag pan
                bg.addEventListener('mousedown', function(e) {{
                    if (e.target.tagName === 'BUTTON') return;
                    dr = true; ox = e.clientX - px; oy = e.clientY - py;
                }});
                bg.addEventListener('mousemove', function(e) {{
                    if (!dr) return;
                    px = e.clientX - ox; py = e.clientY - oy;
                    upd();
                }});
                bg.addEventListener('mouseup', function() {{ dr = false; }});
                bg.addEventListener('mouseleave', function() {{ dr = false; }});

                // Double-click zoom
                bg.addEventListener('dblclick', function(e) {{
                    if (e.target.tagName === 'BUTTON') return;
                    const clip = imgs[0].parentElement;
                    const pr = clip.getBoundingClientRect();
                    const mx = e.clientX - pr.left, my = e.clientY - pr.top;
                    const os = s;
                    s = Math.min(30, s * 2);
                    px = mx - (mx - px) * (s / os);
                    py = my - (my - py) * (s / os);
                    upd();
                }});

                window.szi = function() {{
                    const clip = imgs[0].parentElement;
                    const cx = clip.clientWidth/2, cy = clip.clientHeight/2, os = s;
                    s = Math.min(30, s * 1.4);
                    px = cx - (cx - px) * (s / os); py = cy - (cy - py) * (s / os); upd();
                }};
                window.szo = function() {{
                    const clip = imgs[0].parentElement;
                    const cx = clip.clientWidth/2, cy = clip.clientHeight/2, os = s;
                    s = Math.max(0.1, s / 1.4);
                    px = cx - (cx - px) * (s / os); py = cy - (cy - py) * (s / os); upd();
                }};
                window.srs = function() {{ fit(); }};
            }})();
            </script>
            """, height=900)
        else:
            st.warning("Nessuna foto annotata trovata per i giorni selezionati.")

    # Foto annotate singole
    st.divider()
    st.subheader("Foto con Detection")
    col_day, col_hour = st.columns(2)
    with col_day:
        view_day = st.selectbox("Giorno", sorted(df["giorno"].unique()),
                                format_func=lambda d: day_labels.get(d, d),
                                key="photo_day")
    with col_hour:
        available_hours = sorted(df[df["giorno"] == view_day]["ora"].unique())
        view_hour = st.selectbox("Ora", available_hours,
                                  format_func=lambda h: f"{str(h).zfill(4)[:2]}:{str(h).zfill(4)[2:]}",
                                  key="photo_hour")

    det_dir = DETECTIONS_DIR / view_day / str(view_hour).zfill(4)
    if det_dir.exists():
        photos = sorted(det_dir.glob("*.jpeg")) + sorted(det_dir.glob("*.jpg"))
        if photos:
            import base64

            area_map = load_photo_area_map()

            # Costruisci etichette per ogni foto: "Foto 3 - Area 4 (NE)"
            def photo_label(i):
                name = photos[i].name
                area = area_map.get(name, "?")
                return f"Foto {i+1} - {area}"

            # Selettore foto con etichetta area
            selected_idx = st.selectbox(
                "Seleziona foto",
                range(len(photos)),
                format_func=photo_label,
                key="det_photo_select",
            )

            # Carica SOLO la foto selezionata in base64
            selected_photo = photos[selected_idx]
            with open(selected_photo, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            photo_name = selected_photo.name
            photo_area = area_map.get(photo_name, "")

            # Lightbox overlay con zoom e pan — una sola foto
            st.components.v1.html(f"""
            <style>
                .viewer {{
                    width: 100%;
                    height: 90vh;
                    overflow: hidden;
                    position: relative;
                    background: #111;
                    cursor: grab;
                    border-radius: 8px;
                }}
                .viewer:active {{ cursor: grabbing; }}
                .viewer img {{
                    position: absolute;
                    transform-origin: 0 0;
                    max-width: none;
                }}
                .v-controls {{
                    position: absolute;
                    top: 10px; right: 10px;
                    z-index: 10;
                    display: flex; gap: 5px;
                }}
                .v-controls button {{
                    width: 40px; height: 40px;
                    font-size: 20px;
                    border: none; border-radius: 6px;
                    background: rgba(255,255,255,0.9);
                    cursor: pointer; font-weight: bold;
                }}
                .v-controls button:hover {{ background: #fff; }}
                .v-info {{
                    position: absolute;
                    bottom: 10px; left: 10px;
                    color: #fff;
                    background: rgba(0,0,0,0.6);
                    padding: 4px 10px;
                    border-radius: 4px;
                    font-family: monospace;
                    font-size: 14px;
                    z-index: 10;
                }}
            </style>
            <div class="viewer" id="vw">
                <div class="v-controls">
                    <button onclick="zi()">+</button>
                    <button onclick="zo()">&minus;</button>
                    <button onclick="rs()">&#8634;</button>
                </div>
                <img id="vi" src="data:image/jpeg;base64,{b64}" />
                <div class="v-info" id="vinfo">{photo_name}</div>
            </div>
            <script>
                const C=document.getElementById('vw'), I=document.getElementById('vi'),
                      N=document.getElementById('vinfo');
                let s=1,px=0,py=0,dr=false,ox,oy;
                function up(){{I.style.transform=`translate(${{px}}px,${{py}}px) scale(${{s}})`;
                    N.textContent='{photo_name} | {photo_area} | '+Math.round(s*100)+'%';}}
                I.onload=function(){{
                    const cw=C.clientWidth,ch=C.clientHeight,iw=I.naturalWidth,ih=I.naturalHeight;
                    s=Math.min(cw/iw,ch/ih);px=(cw-iw*s)/2;py=(ch-ih*s)/2;up();}};
                C.addEventListener('wheel',function(e){{e.preventDefault();
                    const r=C.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top,os=s;
                    s=Math.max(0.1,Math.min(30,s*(e.deltaY>0?0.9:1.1)));
                    px=mx-(mx-px)*(s/os);py=my-(my-py)*(s/os);up();}});
                C.addEventListener('mousedown',function(e){{dr=true;ox=e.clientX-px;oy=e.clientY-py;}});
                C.addEventListener('mousemove',function(e){{if(!dr)return;px=e.clientX-ox;py=e.clientY-oy;up();}});
                C.addEventListener('mouseup',function(){{dr=false;}});
                C.addEventListener('mouseleave',function(){{dr=false;}});
                C.addEventListener('dblclick',function(e){{
                    const r=C.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top,os=s;
                    s=Math.min(30,s*2);px=mx-(mx-px)*(s/os);py=my-(my-py)*(s/os);up();}});
                function zi(){{const cx=C.clientWidth/2,cy=C.clientHeight/2,os=s;
                    s=Math.min(30,s*1.4);px=cx-(cx-px)*(s/os);py=cy-(cy-py)*(s/os);up();}}
                function zo(){{const cx=C.clientWidth/2,cy=C.clientHeight/2,os=s;
                    s=Math.max(0.1,s/1.4);px=cx-(cx-px)*(s/os);py=cy-(cy-py)*(s/os);up();}}
                function rs(){{I.onload();}}
            </script>
            """, height=850)


if __name__ == "__main__":
    main()
