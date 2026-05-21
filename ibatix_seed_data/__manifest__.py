{
    'name': 'IBATIX Seed Data — Fiches ADEME + Guide ANAH',
    'version': '19.0.1.0.0',
    'category': 'IBATIX',
    'summary': 'Données de référence (PDFs) pour les opérations CEE et la MaPrimeRénov\'',
    'description': """
Seed les 221 fiches PDF des opérations CEE (depuis l'ADEME) et le guide
des aides ANAH 2026 (utilisé par ibatix_intelligence pour les calculs
MaPrimeRénov').

Idempotent : peut être réinstallé / upgradé en toute sécurité, les
attachments existants sont mis à jour (pas dupliqués).
    """,
    'author': 'IBATIX',
    'depends': ['objets_ibatix'],
    'data': [],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
