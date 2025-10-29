
import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="SwarmAgent (Streamlit Demo)", layout="wide")

@st.cache_data
def load_data(tasks_path: str, cards_path: str):
    tasks = pd.read_csv(tasks_path)
    cards = pd.read_csv(cards_path)
    cards["cross_product"] = cards["a_prod"] != cards["b_prod"]
    cards["signals_count"] = cards["signals"].fillna("").apply(lambda s: len([x for x in s.split(", ") if x]))
    return tasks, cards

DATA_DIR = "data"
TASKS_CSV = os.path.join(DATA_DIR, "tasks.csv")
CARDS_CSV = os.path.join(DATA_DIR, "cards.csv")
# Choose a writable directory for actions log
ACTIONS_DIR = os.environ.get("ACTIONS_DIR", DATA_DIR)
try:
    # Ensure the directory exists & is writable, else fall back to /tmp
    os.makedirs(ACTIONS_DIR, exist_ok=True)
    test_path = os.path.join(ACTIONS_DIR, ".write_test")
    with open(test_path, "w") as _f:
        _f.write("ok")
    os.remove(test_path)
except Exception:
    ACTIONS_DIR = "/tmp"
ACTIONS_CSV = os.path.join(ACTIONS_DIR, "actions.csv")

tasks, cards = load_data(TASKS_CSV, CARDS_CSV)

st.sidebar.header("Фильтры")
type_filter = st.sidebar.multiselect("Тип карточки", options=sorted(cards["type"].unique()), default=list(sorted(cards["type"].unique())))
prod_filter = st.sidebar.multiselect("Продукты", options=sorted(pd.unique(tasks["product"])), default=list(sorted(pd.unique(tasks["product"]))))
cap_filter = st.sidebar.multiselect("Capability", options=sorted(pd.unique(tasks["capability"])), default=[])
only_cross = st.sidebar.checkbox("Только кросс-продукт", value=False)
min_score = st.sidebar.slider("Мин. score (для synergy/duplicate)", 0, 100, 50, step=5)
query = st.sidebar.text_input("Поиск по цели/задаче", "")

f_cards = cards[cards["type"].isin(type_filter)].copy()
f_cards = f_cards[(f_cards["a_prod"].isin(prod_filter)) | (f_cards["b_prod"].isin(prod_filter))]
if cap_filter:
    f_cards = f_cards[(f_cards["a_cap"].isin(cap_filter)) | (f_cards["b_cap"].isin(cap_filter))]
if only_cross:
    f_cards = f_cards[f_cards["cross_product"] == True]

def pass_score(row):
    if row["type"] in ["synergy", "duplicate"]:
        try:
            return int(row["score"]) >= min_score
        except Exception:
            return False
    return True
f_cards = f_cards[f_cards.apply(pass_score, axis=1)]

t = tasks.set_index("task_id")
def task_line(tid: str):
    if tid in t.index:
        row = t.loc[tid]
        return f"{tid} · {row['product']}/{row['team']} · {row['capability']} · {row['goal'][:80]}"
    return tid

st.title("SwarmAgent — Demo (без вызовов LLM)")
st.caption("Предзаготовленные карточки на основе capability/surface/entity/contract/KPI/goal.")

tab_inbox, tab_synergy, tab_conflicts, tab_duplicates, tab_overview = st.tabs(["📬 Inbox","🤝 Synergy","⚠️ Conflicts","🔁 Duplicates","📊 Overview"])

with tab_inbox:
    st.subheader("Свежие карточки (фильтры слева)")
    st.write(f"Найдено: **{len(f_cards)}**")
    for _, row in f_cards.sort_values(by=["type","score","signals_count"], ascending=[True, False, False]).head(100).iterrows():
        with st.expander(f"[{row['type'].upper()}] {task_line(row['a_id'])} ⟷ {task_line(row['b_id'])} (signals: {row['signals']} | score: {row['score']} | cross: {'yes' if row['cross_product'] else 'no'})"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**A:** " + task_line(row['a_id']))
                st.json(t.loc[row['a_id']][["product","team","capability","surface","entity","contract","kpi_family","lever","goal","timeline_start","timeline_end"]].to_dict())
            with col2:
                st.markdown("**B:** " + task_line(row['b_id']))
                st.json(t.loc[row['b_id']][["product","team","capability","surface","entity","contract","kpi_family","lever","goal","timeline_start","timeline_end"]].to_dict())
            st.markdown("**Signals:** " + (row["signals"] or ""))
            st.markdown("---")
            st.markdown("**Действия:**")
            act = st.radio("Выбери действие", ["meet (20 мин)","adr (черновик)","dismiss"], key=f"act_{row['match_id']}", horizontal=True)
            if st.button("Выполнить", key=f"btn_{row['match_id']}"):
                action_row = {
                    "ts": datetime.utcnow().isoformat(),
                    "match_id": row["match_id"],
                    "type": row["type"],
                    "action": act.split(" ")[0],
                    "a_id": row["a_id"],
                    "b_id": row["b_id"]
                }
                try:
                    if os.path.exists(ACTIONS_CSV):
                        log = pd.read_csv(ACTIONS_CSV)
                        log = pd.concat([log, pd.DataFrame([action_row])], ignore_index=True)
                    else:
                        log = pd.DataFrame([action_row])
                    log.to_csv(ACTIONS_CSV, index=False)
                    st.success("Зафиксировано.")
                except Exception as e:
                    st.error(f"Не удалось записать действие: {e}")

with tab_synergy:
    st.subheader("Синергии")
    g = f_cards[f_cards["type"]=="synergy"].copy()
    st.write(f"Всего синергий (после фильтров): **{len(g)}**")
    st.dataframe(g[["match_id","a_id","a_prod","a_cap","b_id","b_prod","b_cap","score","signals"]], use_container_width=True)

with tab_conflicts:
    st.subheader("Конфликты")
    g = f_cards[f_cards["type"]=="conflict"].copy()
    st.write(f"Всего конфликтов: **{len(g)}**")
    st.dataframe(g[["match_id","a_id","a_prod","a_cap","b_id","b_prod","b_cap","signals"]], use_container_width=True)

with tab_duplicates:
    st.subheader("Дубликаты")
    g = f_cards[f_cards["type"]=="duplicate"].copy()
    st.write(f"Всего дубликатов: **{len(g)}**")
    st.dataframe(g[["match_id","a_id","a_prod","a_cap","b_id","b_prod","b_cap","score","signals"]], use_container_width=True)

with tab_overview:
    st.subheader("Обзор портфеля")
    left, right = st.columns(2)
    with left:
        st.markdown("**Карточки по продуктам (A-сторона):**")
        counts = f_cards.groupby(["a_prod","type"]).size().unstack(fill_value=0)
        st.dataframe(counts)
    with right:
        st.markdown("**Карточки по capability (топ-15):**")
        cap_counts = pd.concat([f_cards["a_cap"], f_cards["b_cap"]]).value_counts().head(15)
        st.dataframe(cap_counts.to_frame("count"))
    st.markdown("---")
    st.markdown("**Tasks:**")
    st.dataframe(tasks[["task_id","product","team","capability","surface","entity","contract","kpi_family","lever","goal","timeline_start","timeline_end"]], use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.header("Обновление данных")
u_tasks = st.sidebar.file_uploader("Загрузить tasks.csv", type=["csv"], key="u_tasks")
u_cards = st.sidebar.file_uploader("Загрузить cards.csv", type=["csv"], key="u_cards")
if st.sidebar.button("Применить загруженные CSV"):
    if u_tasks is not None:
        pd.read_csv(u_tasks).to_csv(TASKS_CSV, index=False)
    if u_cards is not None:
        pd.read_csv(u_cards).to_csv(CARDS_CSV, index=False)
    st.success("Данные обновлены. Перезапусти страницу.")
