# SDD ledger — plan: docs/superpowers/plans/2026-08-08-mlip-vibrations-app.md
Task 1: complete (commits b8fd941..175215f, review clean)
Task 1: minor (deferred): test só checa truthiness de spec.name, não isinstance(expected_linear, bool)
Task 1: minor (deferred): não há checagem de unicidade de ase_name (só de id)
Task 2: complete (commits 175215f..827a7c4, review clean)
Task 2: minor (deferred): ramo is_linear=True e ramo imaginary=True sem teste dedicado (Task 3 exercita lineares via co2/c2h2)
Task 2: minor (deferred): subprocess.run sem timeout
Task 2: minor (deferred): ordenação dupla (por índice em classify, depois por freq em compute_molecule)
Task 3: parked — pareamento greedy com valores experimentais mispareia modos degenerados (C2H2: 612 e 730 casam ambos com 718.5; 774.7 nunca aparece) — ruling: plan-mandated, humano decidiu manter o codigo do plano; afeta so a tabela de diagnostico no terminal, nao o web/data.json
Task 3: fato registrado — MACE-OFF23-small subestima todas as frequencias do CO2 (545.4/1248.9/2170.4 vs 667/1333/2349 exp, ate -18%); potencial treinado em moleculas organicas, CO2 esta fora do dominio. Humano decidiu documentar no README (Task 5).
Task 3: minor (deferred): REFERENCIAS_EXPERIMENTAIS cobre so 5 das 10 moleculas (plan-mandated)
Task 3: complete (commits 827a7c4..47b0710, 1 parked)
Task 4: verificacao visual dos 4 pontos (abas, render 3D, animacao ao clicar, troca de molecula) CONFIRMADA pelo humano em http://localhost:8765/ — o controller nao tinha ferramentas de navegador nesta sessao
Task 4: fix round 1/5 (1 addressed, 0 open — stopAnimate() antes de clear() em desenhar(); commits 47f483b..1cd8834)
Task 4: parked — linhas <tr> da tabela de modos sem acesso por teclado (sem tabindex, sem handler Enter/Espaco) — ruling: plan-mandated, humano decidiu manter
Task 4: minor (deferred): n_imaginary nunca lido pelo script
Task 4: minor (deferred): zoomTo() a cada redraw descarta a rotacao manual do usuario
Task 4: minor (deferred): #legenda fica com "carregando..." no caminho de erro do fetch
Task 4: minor (deferred): innerHTML por interpolacao sem escaping (fonte e o proprio data.json)
Task 4: minor (deferred): faltam aria-controls/role=tabpanel no padrao de abas
Task 4: complete (commits 47b0710..1cd8834, 1 parked)
Task 5: README commitado (12d8acd) com a nota sobre a limitacao do CO2 aprovada pelo humano
Task 5: deploy via MCP ABORTADO — agente travou 10min transcrevendo 64kB de JSON inline (risco de corrupcao que eu havia sinalizado). Humano autenticou o Vercel CLI; refeito via CLI com upload byte-exato.
Task 5: deploy production https://cursocasakcm.vercel.app — index 200, data.json 200, sha256 de ambos IDENTICOS aos locais
Task 5: push para github.com/hugogontijomachado/curso_casa_kcm (main)
Task 5: complete (commits 1cd8834..beba7b1)

## Revisao final de branch inteiro (b8fd941..beba7b1, opus)
Veredito: "Fix before use: 5 items" — nenhum Critical; quimica verificada independentemente e correta.
DECISAO DO HUMANO: publicar como esta, NAO corrigir nada nesta sessao. Todos os achados parkeados e
documentados em docs/handoff.md para uma sessao futura.

Task FINAL: parked — I1 rodape da pagina afirma "frequencias ficam sistematicamente acima do experimental" em todas as 10 abas, mas CO2 fica 6-18% ABAIXO; a ressalva so existe no README, que nao esta publicado (404 no site) — ruling: humano optou por publicar como esta
Task FINAL: parked — I2 energy_eV exibido cru (ex: -2081.121 eV para H2O) inclui energias de referencia atomica do MACE; nao e comparavel entre moleculas, mas a pagina poe o mesmo campo nas 10 abas e convida a comparacao — ruling: parkeado
Task FINAL: parked — I3 zpe_eV vem de vib.get_zero_point_energy() da skill, que soma sobre TODOS os 3N modos sem classificacao; contamina com trans/rot residual. H2O: data.json 0.58786 eV vs 0.58432 eV somando os 3 modos listados. Contaminacao em cm-1: h2o 28.6, h2co 13.9, c2h4 13.1, c2h2 12.4, co2 6.9, c6h6 5.1, ch3oh 3.5, nh3 1.4, c2h6 0.2, ch4 0.0. tests/test_run_molecule.py fixa o valor contaminado 0.5875 — ruling: parkeado
Task FINAL: parked — I4 README manda exportar PYTHONPATH, mas run_molecule.py resolve a skill por ATOMISTIC_SKILLS (default hardcoded /Users/hugocemep/GitHub/AtomisticSkills) que alimenta VIB_SCRIPT e o cwd do subprocess. Seguir o README em outra maquina falha nas 10 moleculas. Tambem falta environment.yml para o env mace-agent — ruling: parkeado
Task FINAL: parked — I5 erros factuais no README: (a) "as demais nove moleculas, todas organicas" — H2O e NH3 nao sao organicas, e isso derruba o argumento causal do CO2; (b) afirma como fato que CO2 "nao estava no conjunto de treinamento" sem ter verificado o SPICE; (c) publica valores experimentais sem citacao, contrariando o padrao que o proprio spec definiu — ruling: parkeado
Task FINAL: parked — I6 validacao de contagem de modos e tautologica: esperado=3n-(5 ou 6) e len(modes) vem de ordem[n_trans_rot:], mesma formula e mesmo is_linear dos dois lados; nunca pode falhar. MoleculeSpec.expected_linear nunca e lido em lugar nenhum — ruling: parkeado
Task FINAL: parked — I7 run_all.py escreve web/data.json incondicionalmente, mesmo com registros==[]; um re-run que falhe destroi o dataset publicado — ruling: parkeado
Task FINAL: parked — revisora discordou de 2 rulings anteriores: zoomTo() a cada redraw (descarta rotacao manual; ela considera pior que minor) e acesso por teclado nas linhas da tabela — humano manteve ambos parkeados
Task FINAL: minor (deferred): amplitude de animacao nao normalizada por modo (norma cartesiana varia 0.25-1.0; modos de atomos pesados animam ~4x mais sutis); 3Dmol carregado sem versao fixa e sem guarda de falha; coluna "Modo" imprime sempre "vibracao"; timestamp sem fuso; acoplamento nao documentado ao nome do cache "vib" da skill; falta citar o MACE-OFF23
