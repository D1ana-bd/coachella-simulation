# Coachella Crowd Simulation

Simulação de gestão de multidões e acesso a palcos num festival de música (Coachella), desenvolvida no âmbito da unidade curricular de **Simulação Orientada a Dados**.

---

## Descrição

Este projeto simula o comportamento de festivaleiros ao longo de um dia de festival, modelando chegadas, escolha de palcos, filas de espera e saídas. O objetivo é comparar diferentes políticas de gestão de multidões e avaliar o seu impacto na experiência dos participantes.

O projeto está dividido em 4 fases progressivas:

| Fase | Descrição | Estado |
|------|-----------|--------|
| Fase 1 | Simulação base — esqueleto funcional com 3 palcos e agentes simples | ✅ Concluída |
| Fase 2 | Perfis de agentes — General, Fan e VIP com comportamentos distintos | 🔄 Em desenvolvimento |
| Fase 3 | Políticas de gestão — 4 políticas comparadas estatisticamente | ⏳ Pendente |
| Fase 4 | Análise e apresentação — visualizações e relatório final | ⏳ Pendente |

---

## 🏗️ Estrutura do Projeto

```
coachella-simulation/
│
├── main.py                          # Entry point — orquestra SimPy + Pygame
├── requirements.txt                 # Dependências do projeto
├── README.md                        # Este ficheiro
│
├── src/
│   └── coachella/
│       ├── __init__.py
│       ├── config.py                # Parâmetros globais da simulação
│       │
│       ├── simulation/
│       │   ├── __init__.py
│       │   ├── environment.py       # Palcos, recursos SimPy e métricas
│       │   └── events.py            # Processos dos agentes e concert scheduler
│       │
│       ├── visualization/
│       │   ├── __init__.py
│       │   └── map.py               # Grafo NetworkX + rendering Pygame
│       │
│       ├── utils/
│       │   ├── __init__.py
│       │   └── logger.py            # Logger com formato JSON
│       │
│       └── data/                    # Outputs da simulação (CSV de métricas)
│
├── tests/
│   ├── simulation_tests/
│   │   ├── test_environment.py      # 27 testes
│   │   └── test_events.py           # 20 testes
│   ├── visualization/
│   │   └── test_map.py              # 25 testes
│   └── main/
│       └── test_main.py             # 12 testes
│
└── logs/                            # Logs em formato JSON
```

---

## Tecnologias

| Biblioteca | Versão | Uso |
|------------|--------|-----|
| **SimPy** | ≥4.0 | Motor de simulação de eventos discretos |
| **Pygame** | ≥2.0 | Visualização em tempo real |
| **NetworkX** | ≥3.0 | Grafo de distâncias entre palcos |
| **Pandas** | ≥2.0 | Análise de métricas (fases seguintes) |
| **Matplotlib** | ≥3.7 | Gráficos comparativos (fases seguintes) |
| **NumPy** | ≥1.24 | Cálculos numéricos |
| **SciPy** | ≥1.10 | Testes estatísticos (fases seguintes) |
| **Seaborn** | ≥0.12 | Visualizações avançadas (fases seguintes) |

---

##  Instalação

**1. Clonar o repositório**
```bash
git clone https://github.com/username/coachella-simulation.git
cd coachella-simulation
```

**2. Criar ambiente virtual**
```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

**3. Instalar dependências**
```bash
pip install -r requirements.txt
```

---

## Correr a Simulação

```bash
python main.py
```

A janela Pygame abre com o mapa do festival. Prima **Q** ou feche a janela para sair.

**Controlos de velocidade** — no `src/coachella/config.py`:
```python
SIM_SPEED = 0.05    # mais lento → mais fácil de observar
SIM_SPEED = 1.0     # velocidade normal
```

---

## Correr os Testes

```bash
# Todos os testes
pytest tests/ -v

# Por módulo
pytest tests/simulation_tests/test_environment.py -v
pytest tests/simulation_tests/test_events.py -v
pytest tests/visualization/test_map.py -v
pytest tests/main/test_main.py -v
```

**Resultado esperado:** 84 testes, todos a passar ✅

---

## Modelo de Simulação — Fase 1

### Palcos
Três palcos com características distintas:

| Palco | Capacidade | Popularidade |
|-------|-----------|--------------|
| Main Stage | 80 | 50% |
| Sahara Stage | 50 | 30% |
| Outdoor Stage | 30 | 20% |

### Agentes
- **Chegadas:** processo de Poisson (distribuição exponencial entre chegadas)
- **Escolha de palco:** ponderada pela popularidade
- **Paciência:** uniforme entre 10–40 minutos
- **Renege pattern:** se a espera exceder a paciência, o agente desiste e tenta outro palco com a paciência restante descontada
- **Movimento:** animação visual desde a entrada do festival até ao palco destino

### Concertos
- Horários fixos definidos no `config.py`
- Processo `concert_scheduler` abre/fecha cada palco nos horários corretos
- Agentes que chegam fora do horário só esperam se o próximo show for em menos de 20 minutos

### Mapa
- Representado como grafo não-dirigido completo (K3) com NetworkX
- Arestas pesadas pela distância euclidiana entre palcos
- Suporta queries: palco mais próximo, caminho mais curto (Dijkstra)

---

## Métricas Recolhidas

A cada 10 minutos simulados é feito um snapshot de cada palco:

| Métrica | Descrição |
|---------|-----------|
| `occupancy` | Número de agentes dentro do palco |
| `queue_length` | Número de agentes em fila |
| `total_served` | Total de agentes servidos |
| `total_reneged` | Total de desistências |
| `avg_wait_time` | Tempo médio de espera em minutos |
| `active_show` | Se há concerto a decorrer |

Os dados são exportados para `src/coachella/data/metrics.csv`.

---

## Outputs

Após correr a simulação:
- **`src/coachella/data/metrics.csv`** — snapshots das métricas ao longo do tempo
- **`logs/project.log`** — log completo em formato JSON com todos os eventos

---

## Autora

Diana — Licenciatura em Ciência de Dados Aplicada  
Unidade Curricular: Simulação Orientada a Dados