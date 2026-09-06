"""Post-install hooks : seed les fiches ADEME + guide ANAH + analyses Claude.

Idempotent : si l'attachment ou l'analyse existe déjà pour le record cible,
on met à jour son contenu au lieu d'en créer un doublon.
"""
import base64
import json
import logging
import os

_logger = logging.getLogger(__name__)

PDF_DIR = os.path.join(os.path.dirname(__file__), 'pdfs')
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

ANAH_GUIDE_NAME = 'Anah-FR-Guide_des_aides_Fev2026_WEB_20260224.pdf'
ANAH_GUIDE_FILE = 'anah_guide_2026.pdf'
CEE_ANALYSES_FILE = 'cee_analyses.jsonl'

def post_init_hook(env):
    _seed_cee_pdfs(env)
    _seed_anah_guide(env)
    _seed_cee_analyses(env)
    _seed_delegataire_defaut(env)


def _read_b64(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read())


def _seed_cee_pdfs(env):
    Operation = env['ibatix.operation.cee']
    Attachment = env['ir.attachment']
    cee_dir = os.path.join(PDF_DIR, 'cee')
    if not os.path.isdir(cee_dir):
        _logger.warning("ibatix_seed_data: %s introuvable, skip CEE seed", cee_dir)
        return

    created = updated = skipped = 0
    for fname in sorted(os.listdir(cee_dir)):
        if not fname.endswith('.pdf'):
            continue
        code = fname[:-4]
        op = Operation.search([('code', '=', code)], limit=1)
        if not op:
            skipped += 1
            continue
        existing = Attachment.search([
            ('res_model', '=', 'ibatix.operation.cee'),
            ('res_id', '=', op.id),
            ('res_field', '=', 'fiche_pdf'),
        ], limit=1)
        data_b64 = _read_b64(os.path.join(cee_dir, fname))
        if existing:
            existing.write({'datas': data_b64})
            updated += 1
        else:
            Attachment.create({
                'name': 'fiche_pdf',
                'res_model': 'ibatix.operation.cee',
                'res_id': op.id,
                'res_field': 'fiche_pdf',
                'type': 'binary',
                'mimetype': 'application/pdf',
                'datas': data_b64,
            })
            created += 1
    _logger.info(
        "ibatix_seed_data: fiches CEE — %d créés, %d MAJ, %d sans opération en base",
        created, updated, skipped,
    )


def _seed_anah_guide(env):
    Attachment = env['ir.attachment'].sudo()
    anah_path = os.path.join(PDF_DIR, 'anah', ANAH_GUIDE_FILE)
    if not os.path.isfile(anah_path):
        _logger.warning("ibatix_seed_data: %s introuvable, skip ANAH", anah_path)
        return

    existing = Attachment.search([
        ('name', '=', ANAH_GUIDE_NAME),
        ('mimetype', '=', 'application/pdf'),
    ], limit=1)
    data_b64 = _read_b64(anah_path)
    if existing:
        existing.write({'datas': data_b64})
        _logger.info("ibatix_seed_data: guide ANAH MAJ (id=%s)", existing.id)
    else:
        Attachment.create({
            'name': ANAH_GUIDE_NAME,
            'type': 'binary',
            'mimetype': 'application/pdf',
            'datas': data_b64,
            'public': False,
        })
        _logger.info("ibatix_seed_data: guide ANAH créé")


# Champs de ibatix.operation.cee importés depuis l'instantané PROD.
# PROD est la source de vérité : analyses Claude (guide, formule, champs) et
# paramètres métier tenus en PROD (MPR, cible, bonification, types de bien,
# vérification de formule, état actif/abrogé).
SEED_FIELDS = (
    'active', 'abrogee',
    'guide_html', 'champs_eligibilite', 'champs_requis',
    'formule_analysee', 'formule_cumac_python', 'formule_description',
    'type_calcul_mpr', 'prime_mpr_bleu', 'prime_mpr_jaune', 'prime_mpr_violet',
    'plafond_depense_mpr', 'eligible_mpr', 'cible', 'bonification_type',
    'bien_type_maison', 'bien_type_appartement', 'bien_type_collectif',
    'bien_type_tertiaire', 'formule_verifiee', 'formule_verifiee_date',
    'fiche_date_validite',
)


def _seed_cee_analyses(env):
    """Aligne les opérations CEE sur l'instantané PROD (`cee_analyses.jsonl`).

    Rapprochement par identifiant de module (xmlid) puis par code de fiche ;
    création si l'opération n'existe pas (fiches créées à la main en PROD).
    Les champs de SEED_FIELDS sont écrasés : une analyse locale sur un client
    est un cas exceptionnel, à reporter en PROD puis à ré-exporter.
    """
    Operation = env['ibatix.operation.cee'].sudo().with_context(active_test=False)
    jsonl_path = os.path.join(DATA_DIR, CEE_ANALYSES_FILE)
    if not os.path.isfile(jsonl_path):
        _logger.warning("ibatix_seed_data: %s introuvable, skip analyses CEE", jsonl_path)
        return

    created = updated = invalid = 0
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                _logger.warning("ibatix_seed_data: JSON invalide → %s", e)
                invalid += 1
                continue
            code = rec.get('code')
            if not code:
                invalid += 1
                continue
            op = Operation.browse()
            for xmlid in rec.get('xmlids') or ():
                op = env.ref(xmlid, raise_if_not_found=False) or Operation.browse()
                if op:
                    break
            if not op:
                op = Operation.search([('code', '=', code)], limit=1)
            vals = {k: (rec.get(k) if rec.get(k) is not None else False) for k in SEED_FIELDS}
            if op:
                op.write(vals)
                updated += 1
            else:
                vals.update({
                    'code': code,
                    'name': rec.get('name') or code,
                    'secteur': rec.get('secteur') or False,
                })
                Operation.with_context(lang='fr_FR').create(vals)
                created += 1
    _logger.info(
        "ibatix_seed_data: opérations CEE — %d mises à jour, %d créées, %d lignes invalides",
        updated, created, invalid,
    )


DELEGATAIRE_DEMO = 'Délégataire CEE de démonstration'


def _seed_delegataire_defaut(env):
    """Sans délégataire ni contrat CEE, aucune prime ne se calcule sur un
    devis (la valorisation €/MWhc vient du contrat). Un client flotte naît
    sans aucun des deux : on pose un délégataire de démonstration par défaut,
    UNIQUEMENT si la base n'en a aucun, à remplacer par le vrai contrat."""
    from datetime import date
    Delegataire = env['ibatix.delegataire.cee'].sudo()
    if Delegataire.search_count([]):
        return
    d = Delegataire.create({
        'name': DELEGATAIRE_DEMO,
        'is_default': True,
        'actif_devis': True,
    })
    today = date.today()
    env['ibatix.delegataire.contrat'].sudo().create({
        'delegataire_id': d.id,
        'numero_contrat': 'DEMO — à remplacer',
        'date_debut': today.replace(month=1, day=1),
        'date_fin': today.replace(year=today.year + 1, month=12, day=31),
        'valo_classique_client': 6.5,
        'valo_precaire_client': 7.5,
        'valo_classique_reelle': 7.0,
        'valo_precaire_reelle': 8.0,
    })
    _logger.info("ibatix_seed_data: délégataire CEE de démonstration créé (aucun délégataire en base)")
