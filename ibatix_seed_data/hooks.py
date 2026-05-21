"""Post-install hooks : seed les fiches ADEME + guide ANAH en ir.attachment.

Idempotent : si l'attachment existe déjà pour le record cible, on met à
jour son contenu au lieu d'en créer un doublon.
"""
import base64
import logging
import os

_logger = logging.getLogger(__name__)

PDF_DIR = os.path.join(os.path.dirname(__file__), 'pdfs')

ANAH_GUIDE_NAME = 'Anah-FR-Guide_des_aides_Fev2026_WEB_20260224.pdf'
ANAH_GUIDE_FILE = 'anah_guide_2026.pdf'


def post_init_hook(env):
    _seed_cee_pdfs(env)
    _seed_anah_guide(env)


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
