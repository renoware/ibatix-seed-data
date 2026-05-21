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

# Champs de ibatix.operation.cee importés depuis le snapshot PROD.
ANALYSIS_FIELDS = (
    'guide_html',
    'champs_eligibilite',
    'champs_requis',
    'formule_analysee',
    'formule_cumac_python',
    'formule_description',
)


def post_init_hook(env):
    _seed_cee_pdfs(env)
    _seed_anah_guide(env)
    _seed_cee_analyses(env)


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


def _seed_cee_analyses(env):
    """Seed les analyses Claude (guide_html + formules) depuis un snapshot
    JSONL exporté de PROD. Sauf si l'opération a DÉJÀ été (re)analysée par
    l'utilisateur du client (formule_cumac_python non vide), pour éviter
    d'écraser un fix manuel."""
    Operation = env['ibatix.operation.cee']
    jsonl_path = os.path.join(DATA_DIR, CEE_ANALYSES_FILE)
    if not os.path.isfile(jsonl_path):
        _logger.warning("ibatix_seed_data: %s introuvable, skip analyses CEE", jsonl_path)
        return

    created = preserved = skipped = 0
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                _logger.warning("ibatix_seed_data: JSON invalide → %s", e)
                continue
            code = rec.get('code')
            if not code:
                continue
            op = Operation.search([('code', '=', code)], limit=1)
            if not op:
                skipped += 1
                continue
            # Respect du travail local du client : si une analyse existe déjà
            # (cumac formule non vide), on ne touche pas.
            if op.formule_cumac_python:
                preserved += 1
                continue
            vals = {k: rec.get(k) for k in ANALYSIS_FIELDS if rec.get(k) is not None}
            if vals:
                op.write(vals)
                created += 1
    _logger.info(
        "ibatix_seed_data: analyses CEE — %d seedées, %d préservées (déjà analysées), %d sans op en base",
        created, preserved, skipped,
    )
