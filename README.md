# Frequências vibracionais de moléculas pequenas com MLIP

Otimização de geometria e análise vibracional harmônica de 10 moléculas
pequenas usando o potencial de machine learning MACE-OFF23-small, através
das skills do [AtomisticSkills](https://github.com/learningmatter-mit/AtomisticSkills).
Os resultados são publicados numa página estática com visualização 3D e
animação dos modos normais.

## Reproduzir os cálculos

Requer o repositório AtomisticSkills e o ambiente conda `mace-agent`.

    PYTHONPATH=/caminho/para/AtomisticSkills \
    ~/miniforge3/envs/mace-agent/bin/python scripts/run_all.py

Isso regenera `web/data.json` e imprime a validação: contagem de modos
(3N−6, ou 3N−5 para moléculas lineares), ausência de frequências
imaginárias, e a comparação com fundamentais experimentais.

## Testes

    PYTHONPATH=/caminho/para/AtomisticSkills \
    ~/miniforge3/envs/mace-agent/bin/python tests/test_molecules.py

    PYTHONPATH=/caminho/para/AtomisticSkills \
    ~/miniforge3/envs/mace-agent/bin/python tests/test_run_molecule.py

## Página

`web/` é servida como conteúdo estático. Para ver localmente:

    cd web && python -m http.server 8765

## Sobre os números

As frequências são **harmônicas**: a energia potencial é aproximada por uma
parábola em torno do mínimo. Elas ficam sistematicamente acima das
fundamentais medidas experimentalmente, que incluem efeitos anarmônicos.
Um desvio positivo da ordem de 5% é o esperado, não um erro do cálculo.

## Limitação conhecida: CO₂

O `MACE-OFF23-small` é treinado em moléculas orgânicas neutras, e o CO₂ fica
fora do domínio em que ele foi ajustado. O resultado aparece nos números:

| Modo | Calculado (cm⁻¹) | Experimental (cm⁻¹) | Desvio |
|------|------------------|---------------------|--------|
| Deformação angular (degenerada) | 545,4 | 667 | −18,2% |
| Estiramento simétrico | 1248,9 | 1333 | −6,3% |
| Estiramento assimétrico | 2170,4 | 2349 | −7,6% |

As três frequências ficam **abaixo** do experimental, o que contraria o desvio
positivo esperado da aproximação harmônica. Não é erro do cálculo nem da
implementação: é o potencial descrevendo mal uma molécula que não estava no seu
conjunto de treinamento. As demais nove moléculas, todas orgânicas, ficam dentro
do comportamento esperado.

Para um curso, esse caso é útil justamente por isso — mostra que um potencial de
machine learning só é confiável dentro do domínio químico em que foi treinado.
