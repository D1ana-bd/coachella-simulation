# Modelo Conceptual — Simulação de Gestão de Multidões no Coachella

**Cadeira:** Simulação Orientada a Dados  
**Autora:** Diana Dória
**Número:** 251923003
**Data:** Maio 2026
**GitHub:** https://github.com/D1ana-bd/coachella-simulation.git

---

## 1. Contexto e Objetivo

O Coachella é um festival de música com dezenas de milhares de pessoas e vários palcos a acontecer em simultâneo. O problema que me interessou simular foi: **como diferentes formas de gerir o acesso aos palcos afetam a experiência das pessoas?**

A ideia é perceber se ter uma app com informação em tempo real, ou um sistema de recomendações, ou simplesmente dar prioridade a VIPs, faz alguma diferença real e em que métricas.

Usei o lineup real do Coachella 2023 para tornar a simulação mais realista, com horários e palcos reais.

A simulação é **terminante**, o festival começa às 12h e acaba às 20h (480 minutos). Não há período de aquecimento porque o festival começa com o recinto vazio, o que corresponde exatamente à realidade.

---

## 2. Alternativas a Comparar

Comparei quatro políticas:

**Baseline** — sem nenhum tipo de gestão. Os agentes chegam e escolhem palco livremente com base na popularidade. É o cenário de referência.

**Informative App** — existe uma app que mostra lotação e tempos de espera em tempo real. Nem todos usam a app, modelei taxas de adoção realistas (65% do público geral, 90% dos fãs, 80% dos VIPs). Quem usa a app evita palcos congestionados.

**Active Management** — para além da app, existe um sistema que deteta palcos congestionados (acima de 85% de capacidade) e emite recomendações ativas. Os agentes podem ou não seguir a recomendação, os VIPs tendem a ignorar (30%), o público geral segue mais frequentemente (70%).

**VIP Priority** — sem app, sem gestão ativa. Apenas o facto de os VIPs terem fila prioritária e acesso exclusivo ao palco Yuma. Esta política foi propositadamente isolada para medir o **efeito puro do privilégio VIP**, comparável ao Baseline.

---

## 3. Indicadores de Desempenho

Escolhi métricas que cobrem diferentes dimensões do problema:

**Tempo médio de espera** — o quanto as pessoas esperam em fila antes de entrar num palco. É o equivalente ao tempo médio na fila da teoria clássica de filas.

**Taxa de desistência** — percentagem de pessoas que desistem da fila por falta de paciência. Mede frustração e falha do sistema.

**Throughput** — agentes servidos por hora. Mede eficiência operacional.

**Coeficiente de Gini** — mede a desigualdade nos tempos de espera entre agentes. Um Gini alto significa que alguns esperam muito mais do que outros, especialmente relevante para analisar o impacto do VIP Priority.

**Satisfaction score** — calculei um proxy simples de satisfação: `1 - (tempo_espera / paciência)`. Um valor próximo de 1 significa que a pessoa quase não esperou face à sua tolerância; próximo de 0 significa que esgotou a paciência.

**Fan satisfaction** — percentagem de fãs que conseguiram ver pelo menos um artista favorito. Interessante porque mostrou ser praticamente igual em todas as políticas o bottleneck é temporal (o artista só toca uma vez), não de gestão de acesso.

**Palcos visitados** — número médio de palcos que cada agente visita. Mede a riqueza da experiência no festival.

---

## 4. Conteúdo do Modelo

### Entidades e atributos

Tenho três tipos de entidades principais:

**Agente (participante)** — a entidade principal. Cada agente tem um perfil (General, Fan ou VIP), uma lista de artistas favoritos escolhida aleatoriamente do lineup, paciência amostrada de uma Normal, duração de visita também Normal, e uma flag de saída antecipada. Durante a simulação vai acumulando métricas pessoais: tempo total em fila, palcos visitados, favoritos vistos.

**Palco** — recurso com capacidade limitada. Guarda ocupação atual, comprimento da fila, artista em cena, e métricas acumuladas (servidos, desistências, tempos de espera).

**Concerto** — dados reais do lineup Coachella 2023. Cada concerto tem artista, palco, hora de início e duração. O `concert_scheduler` abre e fecha os palcos automaticamente.

Os três perfis de agentes têm comportamentos bastante diferentes:

- **General (70%)** — paciência média, escolhe por popularidade
- **Fan (20%)** — paciência normal para artistas genéricos, mas espera muito mais pelo artista favorito
- **VIP (10%)** — pouca paciência (está habituado a não esperar), acesso exclusivo ao Yuma

### Recursos e filas

Cada palco é um recurso SimPy com capacidade limitada. Nas políticas Baseline, App e Active Management usei `simpy.Resource`. Na política VIP Priority usei `simpy.PriorityResource` com prioridades VIP=0, Fan=1, General=2, menor número significa maior prioridade.

Quando o palco está cheio, os agentes ficam em fila. Se o tempo de espera exceder a paciência, o agente desiste,  implementado com o padrão SimPy de `yield request | env.timeout(patience)`.

### Regras de comportamento

O ciclo de vida de um agente segue a abordagem orientada a processos do SimPy:

1. Chega ao festival (entrada principal) segundo o processo de Poisson da onda em curso
2. Escolhe palco — se tem artista favorito a tocar ou a começar em menos de 20 min, vai a esse palco; senão escolhe por popularidade
3. Com app ativa, evita palcos congestionados antes de escolher
4. Desloca-se até ao palco (movimento visual no grafo)
5. Se o palco estiver fechado sem show próximo, tenta outro
6. Entra na fila com a paciência ajustada ao artista em cena
7. Se desistir, tenta outro palco ou abandona o festival
8. Com gestão ativa, após desistir num palco congestionado pode receber recomendação e seguir ou ignorar
9. Entra no palco, vê o concerto durante `watch_duration`, sai

### Variáveis aleatórias

**Chegadas** — usei distribuição Exponencial para os tempos entre chegadas porque as chegadas são independentes entre si e a taxa é aproximadamente constante dentro de cada onda. É a escolha natural para processos de Poisson. Dividi o festival em 4 ondas com taxas diferentes para modelar o comportamento real de um festival — começo calmo, pico antes dos headliners, abrandamento depois.

**Paciência e duração de visita** — usei Normal para ambas porque resultam da combinação de muitos fatores individuais (humor, cansaço, interesse no artista, etc.), o que pelo Teorema do Limite Central justifica a Normal. Valores negativos são truncados.

| Variável | Distribuição | Parâmetros por perfil |
|---|---|---|
| Paciência — General | Normal | μ=25, σ=8 min |
| Paciência — Fan (geral) | Normal | μ=20, σ=6 min |
| Paciência — Fan (favorito) | Normal | μ=50, σ=10 min |
| Paciência — VIP | Normal | μ=10, σ=3 min |
| Duração de visita — General | Normal | μ=35, σ=10 min |
| Duração de visita — Fan | Normal | μ=55, σ=5 min |
| Duração de visita — VIP | Normal | μ=30, σ=15 min |

---

## 5. Dados Utilizados e Pressupostos

### Dados reais

O único dado real que usei foi o **lineup do Coachella 2023**, artistas, palcos, horários e durações. Isto torna a simulação mais realista e fundamentada, porque os padrões de congestionamento dependem diretamente de quem está a tocar e quando.

As **capacidades dos palcos** foram calibradas para criar stress realista à escala de 10.000 agentes são proporcionalmente menores do que as capacidades reais do festival (que tem 125.000+ pessoas).

### Pressupostos

Para o que não tinha dados, assumi:

- As taxas de adoção da app (65–90%) são estimativas baseadas na penetração de smartphones em festivais nos EUA
- A compliance com recomendações (30–70% por perfil) foi definida com base em comportamento esperado: VIPs tendem a ignorar recomendações, o público geral segue mais
- As proporções de perfis (70/20/10%) refletem a estrutura típica de um festival com bilhetes VIP
- A paciência e duração de visita foram definidas com base em julgamento, não existem dados empíricos públicos para estes parâmetros

---

## 6. Simplificações

**Grafo em vez de mapa contínuo** — o layout do festival é representado como um grafo NetworkX com os palcos como nós e distâncias euclidianas como pesos das arestas. É uma simplificação em relação a um mapa real com obstáculos, mas é computacionalmente eficiente e captura bem as distâncias relativas entre palcos. Com 10.000 agentes × 30 réplicas × 4 políticas = 120 simulações, a eficiência era importante.

**Sem filas de comida, WC, ou outros serviços** — o foco é a gestão de acesso aos palcos. Adicionar estes elementos tornaria o modelo mais realista mas muito mais complexo, sem ser o foco do problema.

**Duração dos concertos fixa** — o lineup real tem horários fixos, por isso esta simplificação é razoável.

**Sem efeitos climáticos ou meteorológicos** — fora do âmbito do problema.

**Agentes não voltam a palcos já visitados** — simplificação do comportamento real onde uma pessoa pode voltar ao mesmo palco em diferentes shows.