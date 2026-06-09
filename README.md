# 🦉 ONPE Oracle

**Análisis cuantitativo de resultados electorales de segunda vuelta ONPE con simulación de sensibilidad JEE.**

Scrapea datos en vivo de la página oficial de ONPE, proyecta votos pendientes y simula la asignación de actas impugnadas (JEE) para estimar el impacto en el resultado final.

## Cómo funciona

1. **Scraping** — Lanza un navegador headless con Playwright y extrae actas, votos y porcentajes de las 25 regiones (24 departamentos + extranjero) desde `resultadosegundavuelta.onpe.gob.pe`.
2. **Proyección** — Escala los votos pendientes por región usando la densidad de votantes por acta (210 nacional, 150 extranjero) y la tendencia histórica de votos emitidos.
3. **Simulación JEE** — Permite asignar los votos impugnados de forma global (slider JP/K) o por región según el historial de cada departamento.
4. **Dashboard** — Genera un HTML interactivo con tabla de proyección, cards de resumen y filtros.

## Requisitos

- Python 3.9+
- Playwright (se instala automáticamente con `requirements.txt`)
- Navegadores Chromium (se instalan con `playwright install chromium`)

## Instalación

```bash
python -m venv venv
.\venv\Scripts\Activate   # Windows
pip install -r requirements.txt
playwright install chromium
```

## Uso

```bash
python main.py
```

El script abre la página de ONPE, extrae los datos de todas las regiones y genera:

- `exports/resultados_onpe_YYYYMMDD_HHMMSS.json` — datos crudos
- `exports/dashboard_onpe_YYYYMMDD_HHMMSS.html` — dashboard interactivo (se abre automáticamente)

## Dashboard

Cuatro cards principales:

| Card | Descripción |
|---|---|
| **Resultado Actual** | % de votos válidos JP vs K con el conteo actual |
| **Ganador Proyectado Final** | Projected winner incluyendo pendientes y JEE |
| **Pendientes ONPE** | Votos regulares por contabilizar + diferencia neta |
| **Pendientes JEE** | Votos impugnados en revisión + diferencia neta |

El panel JEE permite alternar entre:
- **Control Global (Slider):** asigna un % fijo de votos JEE a cada candidato
- **Escalado por Región (Histórico):** asigna según la tendencia real de votos emitidos en cada región

La tabla muestra por región: actas, % pendiente, % JEE, % votos JP/K, proyecciones y diferencias acumuladas. Se puede filtrar, ocultar regiones sin pendientes/JEE, y ordenar por cualquier columna.

## Estructura

```
onpe_oracle/
├── main.py              # scraper + generación de dashboard
├── templates/
│   └── dashboard.html   # template del dashboard ({{JSON_DATA}})
├── exports/             # output con timestamp
│   └── .gitkeep
├── requirements.txt
└── .gitignore
```
