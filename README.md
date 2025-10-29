
# SwarmAgent — Streamlit Demo

Мини-проект, который показывает карточки (synergy/duplicate/conflict) из заранее подготовленных CSV без вызовов LLM.

## Запуск
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Данные
- `data/tasks.csv` — задачи (product, team, capability, surface, entity, contract, kpi_family, lever, goal, timeline_*)
- `data/cards.csv` — карточки (match_id, type, a_*, b_*, score, signals)
- `data/actions.csv` — лог действий (создаётся при первой записи из UI)

Через левый сайдбар можно подложить свои CSV и применить их поверх.
