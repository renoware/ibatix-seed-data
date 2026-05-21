# ibatix-seed-data — Données de référence métier IBATIX

Repo de données binaires (PDFs ADEME + guide ANAH) seedées dans la base
des clients IBATIX. Séparé du repo principal `renoware/ibatix` pour ne
pas alourdir le code source avec ~40 MB de binaires.

## Module

`ibatix_seed_data` — un `post_init_hook` parcourt `pdfs/cee/<CODE>.pdf`
et `pdfs/anah/anah_guide_2026.pdf` et crée/MAJ les `ir.attachment`
correspondants. Idempotent.

## Inclusion dans une instance client

Via `ibatix-stack/odoo/custom/src/repos.yaml` :

```yaml
./ibatix-seed-data:
  defaults:
    depth: $DEPTH_DEFAULT
  remotes:
    renoware: https://github.com/renoware/ibatix-seed-data.git
  target: renoware 19.0
  merges:
    - renoware 19.0
```

Et dans `addons.yaml` :

```yaml
ibatix-seed-data:
  - ibatix_seed_data
```

## Mise à jour des fiches ADEME

Quand l'ADEME publie de nouvelles fiches, drop les PDFs dans
`pdfs/cee/<CODE>.pdf` (overwrite), bump la version dans le manifest,
push. Tous les clients récupèrent via `Refresh available` puis
`Synchroniser sélection` sur `ibatix_seed_data` (passe `-u` qui
re-déclenche le hook).
