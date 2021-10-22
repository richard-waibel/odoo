from odoo import fields, models


class EstatePropertyTag(models.Model):
    _name = "estate.property.tag"
    _description = "Property Tag"
    _order = "name"

    _sql_constraints = [
        ("name_unique", "UNIQUE (name)",
         "Property tag already exists !")
    ]

    name = fields.Char(required=True)
    color = fields.Integer()
