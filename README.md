# Coachella Crowd Simulation

Simulação de gestão de multidões num festival de música inspirado no Coachella, desenvolvida em Python para a cadeira de Simulação Orientada a Dados.

O objetivo é comparar quatro políticas de gestão de acesso a palcos e perceber qual tem melhor impacto na experiência dos participantes.

---

## Estrutura do Projeto

```
coachella-simulation/
├── src/coachella/
│   ├── simulation/          # Motor SimPy — agentes, palcos, políticas, runner
│   ├── visualization/       # Mapa Pygame + rendering
│   ├── analysis/            # Estatísticas e gráficos
│   ├── data/                # Lineup Coachella 2023
│   ├── assets/              # Imagens e sprites
│   └── config.py            # Parâmetros centrais
├── tests/                   # testes (pytest)
├── notebooks/
│   └── coachella_analysis.ipynb   # Relatório de análise completo
├── results/                 # CSVs e gráficos gerados
├── docs/
│   ├── conceptual_model.md  # Modelo conceptual
│   └── results.md           # Resultados e conclusões
├── main.py                  # Visualização Pygame interativa
├── run_analysis.py          # Análise comparativa das 4 políticas
└── README.md
```

---

## Instalação

```bash
git clone https://github.com/diana/coachella-simulation
cd coachella-simulation
pip install -r requirements.txt
```

Dependências principais: `simpy`, `pygame`, `networkx`, `numpy`, `scipy`, `pandas`, `matplotlib`, `pytest`

---

## Como Correr

### Visualização interativa

```bash
python main.py
```

Abre um menu onde podes escolher a política a simular. A simulação corre em tempo real com mapa pixel art, sprites dos agentes e HUD com métricas ao vivo.

### Análise comparativa (30 réplicas × 4 políticas)

```bash
python run_analysis.py
```

Corre 120 simulações e gera CSVs e gráficos em `results/`. Para uma corrida rápida:

```bash
python run_analysis.py --replicas 5
```

### Notebook de análise

Abrir `notebooks/coachella_analysis.ipynb` num ambiente Jupyter. Contém a análise completa com gráficos, testes estatísticos e conclusões.

---

## As 4 Políticas

| Política | Descrição |
|---|---|
| **Baseline** | Sem controlo — agentes escolhem livremente |
| **Informative App** | App com lotação em tempo real; agentes evitam palcos congestionados |
| **Active Management** | Recomendações dinâmicas quando há congestionamento |
| **VIP Priority** | Fila prioritária para VIPs + palco Yuma exclusivo |

---

## Resultados Principais

A Informative App e o Active Management reduzem o tempo médio de espera em 82% face ao Baseline, e as desistências caem de ~16 para menos de 1 por simulação. As duas políticas são estatisticamente equivalentes entre si (p > 0.95).

O VIP Priority comporta-se como o Baseline em espera média, mas é a política mais desigual (Gini = 0.962 vs 0.906 das políticas inteligentes).

Resultados detalhados em `docs/results.md` e `notebooks/coachella_analysis.ipynb`.

---

## Documentação

- `docs/conceptual_model.md` — modelo conceptual completo
- `docs/results.md` — descrição das experiências, resultados e conclusões

---
## Autora

Diana Dória — Licenciatura em Ciência de Dados Aplicada  
Unidade Curricular: Simulação Orientada a Dados