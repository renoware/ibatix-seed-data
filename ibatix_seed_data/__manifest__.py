{
    'name': 'IBATIX Seed Data — Fiches ADEME + Guide ANAH',
    'version': '19.0.2.1.0',
    'category': 'IBATIX',
    'summary': 'Données de référence (PDFs) pour les opérations CEE et la MaPrimeRénov\'',
    'description': """
Seed les 221 fiches PDF des opérations CEE (depuis l'ADEME) et le guide
des aides ANAH 2026 (utilisé par ibatix_intelligence pour les calculs
MaPrimeRénov').

Idempotent et rejoué à chaque `-u` (data/seed.xml → ibatix.seed.data.run) :
attachments mis à jour, opérations CEE alignées sur l'instantané PROD
(274 opérations, analyses Claude + paramètres MPR/bonification).
    """,
    'author': 'IBATIX',
    'depends': ['objets_ibatix'],
    'data': ['data/seed.xml'],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
