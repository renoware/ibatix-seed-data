"""Chargeur des données de référence, rejouable à chaque `-u ibatix_seed_data`.

`post_init_hook` ne tourne qu'à l'installation : un client provisionné avant
un nouvel instantané ne le recevait jamais (fleet, 06/09/2026 : 0 guide
technique sur 255 opérations). Le `<function>` de `data/seed.xml` appelle
`run()` à chaque install ET upgrade.
"""
import logging

from odoo import api, models

from .. import hooks

_logger = logging.getLogger(__name__)


class IbatixSeedData(models.AbstractModel):
    _name = 'ibatix.seed.data'
    _description = 'Données de référence IBATIX (fiches ADEME, guide ANAH, analyses CEE)'

    @api.model
    def run(self):
        hooks.post_init_hook(self.env)
        return True
