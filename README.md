# IRPF Calculator — Spain (Castilla-La Mancha)

A rule-based simulator for the Spanish personal income tax return (**Declaración de la Renta / IRPF**), built to help estimate a full annual tax liability from manually entered data — no scraping, no integration with the Spanish Tax Agency (AEAT), no personal data leaves your machine.

> ⚠️ **Not an official tool.** This is a personal, non-commercial project. It is not affiliated with, endorsed by, or connected to the Agencia Tributaria (AEAT). Results are estimates for planning purposes only — always cross-check against [Renta WEB](https://sede.agenciatributaria.gob.es) before filing.

## What it does

- Models a taxpayer's full fiscal profile — employment/pension income, rental income, investment income, self-employment, capital gains, personal/family minimums — and computes the resulting Spanish IRPF liability for a given tax year.
- Covers both the **national (estatal)** and **regional (autonómica)** scales, currently parameterized for **Castilla-La Mancha**.
- Ships with a **Streamlit web UI** to fill in a full tax profile through a guided form, and a **what-if salary raise simulator** to see the real marginal impact (SS contributions + IRPF) of a gross salary increase, per payer, before it happens.
- Runs entirely **offline and locally** — a `run.bat` script bootstraps a local Python virtual environment and dependencies with no manual setup.

## Why

Off-the-shelf tax software either requires trusting a third party with real financial data, or doesn't let you freely simulate "what if my salary goes up by X" scenarios with real marginal-rate accuracy across combined income sources. This project exists to answer exactly that kind of question — precisely, locally, and inspectable.

## Architecture

The project separates **tax rules** from **calculation logic** from **the interface**, so that updating a fiscal year or adding a region doesn't require touching business logic:

```
irpf_calculator/
├── params/                  # Fiscal parameters as YAML, one file per year/region
│   ├── 2026_estatal.yaml    #   national brackets, personal/family minimums, deductions
│   └── 2026_clm.yaml        #   Castilla-La Mancha regional brackets and deductions
├── domain/
│   └── models.py            # Typed dataclasses: the tax profile data contract
├── engine/                  # One module per income block — no I/O, pure calculation
│   ├── parametros.py        #   YAML loader + progressive bracket calculator
│   ├── minimos.py           #   personal / family / disability minimums
│   ├── trabajo.py           #   employment & pension income
│   ├── capital_inmobiliario.py   # rental income & imputed property income
│   ├── capital_mobiliario.py     # dividends, interest, life insurance annuities
│   ├── actividades_economicas.py # self-employment (all three regimes)
│   ├── ganancias_patrimoniales.py # capital gains, incl. age-65 exemptions
│   ├── deducciones_estatales.py  # national tax credits
│   ├── deducciones_clm.py        # Castilla-La Mancha regional tax credits
│   └── liquidacion.py       # orchestrator — wires every block into a final result
├── app.py                   # Streamlit UI (the entry point most users want)
├── requirements.txt
├── run.bat                  # Windows one-click installer + launcher
└── tests/
    └── test_caso_jubilado.py # end-to-end synthetic scenario
```

Because tax parameters live in versioned YAML files rather than hardcoded constants, extending the tool to a new fiscal year or a new Autonomous Community is a matter of adding a new `params/<year>_<region>.yaml` file — the calculation engine itself doesn't change.

## Coverage

| Income / deduction block | Status |
|---|---|
| Employment & pension income (multiple payers) | ✅ |
| Personal, family, ascendant/descendant, and disability minimums | ✅ |
| Rental income (with post-2024 reduction regime) | ✅ |
| Imputed income from non-rented, non-primary properties | ✅ |
| Investment income (dividends, interest, life annuities) | ✅ |
| Self-employment (direct estimation & modules) | ✅ |
| Capital gains, incl. reinvestment and age-65 exemptions | ✅ |
| Pension plan contributions | ✅ |
| National tax credits (housing, maternity, large family, donations) | ✅ |
| Castilla-La Mancha regional credits (birth, large family, rent, per-child) | ✅ (main ones — a few minor regional credits are marked `pending_verification` in the YAML) |
| Joint vs. individual filing | ✅ |

## The salary raise simulator

Beyond a static calculation, the app includes a dedicated **"what happens if I get a raise"** tool:

- Set a different raise for **each income source independently** (monthly gross, annual gross, or % increase).
- The engine re-runs the **entire annual liquidation** with the new figures — so the marginal effect on tax respects real progressivity across your combined income, instead of estimating the raise in isolation.
- Shows the before/after comparison: gross/net annual and monthly, total tax, total Social Security contributions, the effective marginal rate of the raise itself ("how many cents of every extra euro actually reach you"), and the resulting year-end balance (owed vs. refunded).
- Includes a **per-payer breakdown** table (gross and contributions are exact per payer; the IRPF share is proportionally allocated, since Spanish income tax is computed jointly and progressively, not payer by payer).

## Getting started

### Windows (recommended path)

1. Download and extract this repository.
2. Double-click `run.bat`.
3. First run: creates a local virtual environment (`.venv`) inside the project folder and installs dependencies. Nothing is installed system-wide.
4. Subsequent runs are instant — it reuses the existing environment and opens the app in your browser.

**Requirement:** Python 3.10+ installed and available on `PATH`. `run.bat` will tell you if it can't find it.

### macOS / Linux / manual setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Command-line / programmatic use

The engine is fully decoupled from the UI and can be used directly:

```python
from domain.models import PerfilFiscal, DatosPersonales, RendimientoTrabajo, TipoDeclaracion
from engine.liquidacion import liquidar

perfil = PerfilFiscal(
    anio_fiscal=2026,
    datos_personales=DatosPersonales(edad=30, ccaa_residencia="Castilla-La Mancha",
                                      tipo_declaracion=TipoDeclaracion.INDIVIDUAL),
    rendimientos_trabajo=[
        RendimientoTrabajo(concepto="salario", integro_anual=32000, retenciones_soportadas=4200)
    ],
)

liquidacion = liquidar(perfil, ccaa="Castilla-La Mancha")
print(liquidacion.resultado_declaracion)  # positive = owed, negative = refund
```

See `tests/test_caso_jubilado.py` for a full synthetic example (pension + rental income + primary residence sale with the over-65 exemption).

## Data & privacy

- No network calls, no telemetry, no external services. Everything runs on your machine.
- The Streamlit app can **export/import a full profile** as a local `.irpf` file (pickle-based) so you don't have to re-enter data across sessions — this file never leaves your computer unless you move it yourself.
- If you intend to use this with someone else's real financial data (e.g. helping a family member), treat that exported file like any other sensitive personal document.

## Known limitations

- **Not certified or audited by any tax authority.** It's a personal-project rule engine — always validate results against the official AEAT Renta WEB simulator before filing anything.
- Several Castilla-La Mancha regional deductions (disability-related, elderly ascendants, childcare) are stubbed with `pending_verification: true` in `params/2026_clm.yaml` and not yet implemented in `engine/deducciones_clm.py`.
- Some parameters (e.g. exact work-income reduction thresholds, filing obligation limits) are annotated `VERIFICAR` in the YAML because different official sources gave slightly inconsistent figures at the time of writing — cross-check before relying on them.
- Per-payer IRPF in the breakdown table is a **proportional allocation**, not an independent calculation — Spanish income tax is inherently computed on combined, progressive income.
- Currently scoped to one Autonomous Community (Castilla-La Mancha). Adding another region means adding its `params/<year>_<region_code>.yaml` and its own deduction module.

## Roadmap ideas

- [ ] Complete the remaining Castilla-La Mancha regional deductions
- [ ] Add additional Autonomous Communities
- [ ] PDF/export summary of the calculated result
- [ ] Automated regression tests comparing output against known Renta WEB results
- [ ] Multi-year parameter history for year-over-year comparison

## License

Personal project — no license file included by default. Add one (MIT/Apache-2.0/etc.) before treating this as reusable by others.
