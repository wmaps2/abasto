# Abasto

Sistema de planificación de demanda y reposición para retail.

## Módulos

| Fase | Módulo | Descripción |
|------|--------|-------------|
| 1 | **Forecast** | Planificación de demanda semanal con AutoETS y overrides manuales |
| 2 | **Compra** | Revisión periódica de reposición con nivel de servicio endógeno |

## Stack

- Python
- Streamlit
- statsforecast

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
streamlit run app.py
```
