# Citation Consistency Report

Checks run on the final build (2026-10-03) with `scripts/build_bib.py` and an inline check script.

| Check | Result |
|---|---|
| Every `\cite{...}` key exists in `references_verified.bib` | PASS (90 cited, 90 present, 0 missing) |
| Every `.bib` entry is cited | PASS (0 uncited; uncited verified entries are kept out of the file and listed in `references_rejected.md`) |
| Undefined citations in `main.log` | PASS (none) |
| Duplicate arXiv IDs or DOIs | PASS (none) |
| arXiv IDs match titles for the 21 arXiv seed references | PASS (all 21 eprint fields equal the IDs resolved in `citation_search_log.md`) |
| Author order | Taken from the source of record for each entry (camera-ready PDF or proceedings page where they disagree with mirrors; for example AgentHazard and OS-Sentinel). One name-order question remains (Not an A11y, third author), see `citation_todo.md`. |
| Titles | Exact titles from the source of record; corrected titles for MELON, Progent (v3), Aura (paper title, not system name), NeuroTaint, FlowSeal, UI desync, and Caution for the Environment (ACL title). |
| DOI matches title | All DOIs came from Crossref/OpenAlex/publisher records fetched for that title. |
| Unsupported claims | Four idea-document claims were not carried over (see `references_rejected.md`). Every manuscript claim citing a paper is mapped in `citation_claim_map.csv`. |
| Topic dominance | Citations are dominated by mobile/GUI agent security, agent defenses, and Android platform mechanisms. No neighboring topic (federated learning, DP, wireless) appears. |
| Verification levels | full-text: 40; abstract-only: 33; documentation pages: 11; software pages: 2; metadata-level for background or terminology sentences only: 4 (Denning, Pearl, CamFlow, Hardy). Abstract-only references are cited only for abstract-level claims. |
| Em dashes | Removed from bibliography titles (user style preference). |
