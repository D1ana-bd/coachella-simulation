# Resultados — Simulação de Gestão de Multidões no Coachella

---

## 1. Cenários Testados

Simulei quatro cenários correspondentes às quatro políticas definidas no modelo conceptual: Baseline (sem gestão), Informative App (app com lotação em tempo real), Active Management (recomendações dinâmicas), e VIP Priority (fila prioritária para VIPs com acesso exclusivo ao Yuma).

Todos os cenários correram com os mesmos parâmetros: 10.000 agentes, 8 palcos, 480 minutos, lineup real Coachella 2023.

---

## 2. Número de Repetições

Cada política foi simulada com 30 réplicas independentes, usando seeds sequenciais (seed_i = 100 + i). Escolhi 30 réplicas porque é o valor a partir do qual o Teorema do Limite Central garante que a distribuição das médias amostrais é aproximadamente normal, o que permite calcular intervalos de confiança via t-Student mesmo que os dados individuais não sigam uma distribuição Normal. No total foram 120 simulações.

---

## 3. Tipo de Simulação e Estratégia de Estimação

A simulação é terminante — o festival tem início e fim definidos. O recinto começa vazio, o que corresponde exatamente às condições reais, por isso não há razão para definir período de aquecimento.

Usei replicações independentes: cada réplica tem seed diferente, corre de forma completamente independente, e os resultados são agregados no final para calcular médias e intervalos de confiança.

---

## 4. Intervalos de Confiança e Comparações Múltiplas

Os intervalos de confiança foram calculados a 95% com t-Student (29 graus de liberdade), que é mais conservador e correto para n=30 do que usar a normal.

Para comparar pares de políticas usei Mann-Whitney U em vez de t-test. Os tempos de espera têm distribuições assimétricas — muitos zeros quando não há fila e cauda longa quando há congestionamento — o que viola a hipótese de normalidade do t-test. O Mann-Whitney não assume normalidade e é mais robusto nestes casos.

Com 4 políticas existem 6 pares de comparações. Não apliquei correção de Bonferroni porque os p-values são todos extremamente pequenos (p < 0.0001) ou muito grandes (p > 0.95) — não há nenhum caso borderline onde a correção mudasse a interpretação. Aplicar Bonferroni não alteraria nenhuma conclusão.

---

## 5. Redução de Variância

Usei seeds fixas e determinísticas para garantir reproducibilidade total. Não implementei técnicas formais de redução de variância como variáveis antitéticas. A variabilidade entre réplicas foi suficientemente baixa para obter intervalos de confiança estreitos com 30 réplicas, o que sugere que não seria necessário.

---

## 6. Resultados

### Tabela comparativa (média ± IC 95%, n=30)

| Política | Espera (min) | Desistências | Throughput (ag/h) | Gini |
|---|---|---|---|---|
| Baseline | 0.377 ± 0.027 | 15.7 ± 3.0 | 679.95 ± 6.4 | 0.953 ± 0.002 |
| Informative App | 0.067 ± 0.023 | 0.6 ± 0.3 | 675.58 ± 7.5 | 0.907 ± 0.247 |
| Active Management | 0.068 ± 0.024 | 0.5 ± 0.3 | 675.66 ± 7.5 | 0.906 ± 0.247 |
| VIP Priority | 0.373 ± 0.029 | 8.3 ± 1.3 | 680.18 ± 6.5 | 0.962 ± 0.003 |

### Testes estatísticos (Mann-Whitney U, avg_wait_time, α=0.05)

| Par | p-value | Effect size (r) | Significativo |
|---|---|---|---|
| Baseline vs Informative App | < 0.0001 | 0.858 | Sim |
| Baseline vs Active Management | < 0.0001 | 0.858 | Sim |
| Baseline vs VIP Priority | 0.7394 | 0.043 | Não |
| Informative App vs Active Management | 0.9587 | 0.007 | Não |
| Informative App vs VIP Priority | < 0.0001 | 0.858 | Sim |
| Active Management vs VIP Priority | < 0.0001 | 0.858 | Sim |

### Novos indicadores

| Política | Satisfação General | Satisfação Fan | Satisfação VIP | Fan Satisfaction |
|---|---|---|---|---|
| Baseline | 0.985 | 0.982 | 0.971 | 18.9% |
| Informative App | 0.997 | 0.999 | 0.995 | 18.9% |
| Active Management | 0.997 | 0.999 | 0.995 | 18.9% |
| VIP Priority | 0.981 | 0.996 | 0.999 | 19.0% |

Os gráficos completos estão em `results/` e no notebook `notebooks/coachella_analysis.ipynb`.

---

## 7. Análise e Conclusões

**As políticas de informação fazem uma diferença enorme.** A Informative App e o Active Management reduziram o tempo médio de espera em 82% face ao Baseline, e as desistências caíram de 15.7 para menos de 1 por simulação. A diferença é estatisticamente significativa com effect size grande (r = 0.858), o que significa que não é ruído — é um efeito real e robusto.

**A Informative App e o Active Management são praticamente iguais.** Os testes mostram p > 0.95 e effect size quase zero na comparação entre as duas. Isto foi uma surpresa — esperava que as recomendações ativas acrescentassem algo. Mas a app por si só já é suficiente para resolver o congestionamento, pelo menos nos parâmetros que simulei. Do ponto de vista prático, a app simples seria preferível por ser menos invasiva para os utilizadores.

**O VIP Priority comporta-se como o Baseline em termos de espera média, mas com uma distribuição diferente.** Sem app nem gestão ativa, o tempo médio é semelhante ao Baseline. Mas as desistências são diferentes: 8.27 no VIP Priority vs 15.7 no Baseline. A maior parte das desistências VIP concentram-se no Yuma — o palco exclusivo tem capacidade 80, e os VIPs acumulam-se todos lá, criando um bottleneck que não existe nas outras políticas.

**O VIP Priority é a política mais desigual.** O Gini é 0.962, o mais alto. Isto é esperado — dar prioridade a um grupo redistribui o serviço e aumenta a desigualdade nos tempos de espera. É um trade-off claro: o sistema funciona melhor para VIPs à custa da equidade global.

**Os satisfaction scores são altos em todas as políticas**, entre 0.97 e 0.999. A diferença mais visível é nos VIPs no Baseline (0.971) — esperam proporcionalmente mais face à sua baixa tolerância. Curiosamente, no VIP Priority os VIPs têm o score mais alto de todos (0.999) porque a prioridade na fila resolve exatamente o seu problema.

**A fan satisfaction é praticamente igual em todas as políticas, ~19%.** Este resultado foi o mais interessante de analisar. Nenhuma política melhora a probabilidade de um fã ver o seu artista favorito. O bottleneck não é o acesso — é o tempo. O artista só toca uma vez, e quem não chega a tempo perde independentemente de haver ou não app. Gerir filas não resolve escassez de oferta.

**O throughput é estável em todas as políticas** (~676–680 ag/h). Melhorar a experiência das pessoas não penaliza a capacidade do sistema — o que é uma boa notícia do ponto de vista operacional.

### Conclusão

A Informative App é a política com melhor relação benefício/custo: reduz drasticamente espera e desistências, não introduz desigualdade relevante, e é mais simples de implementar do que o Active Management. O Active Management é equivalente mas mais complexo sem ganho mensurável. O VIP Priority resolve um problema diferente — não melhora a experiência global, mas serve quem pagou mais. O Baseline é claramente o pior em qualidade de serviço.

### Limitações

A compliance com recomendações foi definida por pressuposto — dados reais melhorariam a calibração do Active Management. O modelo também não captura o efeito de rede da app: se toda a gente a usar ao mesmo tempo pode criar novos pontos de congestionamento nos palcos alternativos. E a fan satisfaction provavelmente melhoraria com uma política que reservasse capacidade para fãs nos shows dos seus artistas favoritos — algo que não testei mas seria interessante explorar.